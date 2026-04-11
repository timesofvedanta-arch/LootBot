import os
import telebot
import time
import re
import asyncio
from flask import Flask
from threading import Thread
from pymongo import MongoClient
from telebot import types
from playwright.async_api import async_playwright

# --- कॉन्फ़िगरेशन ---
BOT_TOKEN = "8797754610:AAHM-KFFsdNoBJa2VIfrew5uFvgwGvyL-uI"
MONGO_URI = "mongodb+srv://timesofvedanta:Mk626425@lootbot.ypsol8i.mongodb.net/?appName=Lootbot"
ADMIN_ID = 1216607288

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

# MongoDB Setup
client = MongoClient(MONGO_URI)
db = client["loot_bot_db"]
users_col = db["users"]
offers_col = db["offers"]
stats_col = db["stats"]

# रेंडर के लिए हेल्थ चेक
@app.route('/')
def home(): return "Bot is Running"

# --- हेल्पर फंक्शन्स ---
def is_admin(user_id):
    return user_id == ADMIN_ID

def validate_upi(upi):
    return re.match(r'^[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}$', upi)

# --- स्क्रीनशॉट ट्रैकिंग इंजन (Playwright) ---
async def take_screenshot(url, path):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=60000)
            await page.wait_for_timeout(2000) # थोड़ा इंतज़ार लोड होने के लिए
            await page.screenshot(path=path, full_page=True)
            await browser.close()
            return True
        except:
            await browser.close()
            return False

# --- मुख्य मेनू ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('📜 Offerlist', '🛠 My Task')
    markup.add('👥 My Referral', '📤 Submit Proof')
    markup.add('ℹ️ About')
    return markup

# --- स्टार्ट कमांड ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    
    # यूजर डेटा अगर नया है
    if not users_col.find_one({"_id": user_id}):
        users_col.insert_one({
            "_id": user_id, "name": name, "balance": 0, "referrals": 0,
            "current_task": None, "task_status": "none", "upi": None
        })
    
    bot.send_message(user_id, f"नमस्ते {name}! पैसे कमाने के लिए तैयार हैं?", reply_markup=main_menu())

# --- 📜 ऑफरलिस्ट ---
@bot.message_handler(func=lambda m: m.text == '📜 Offerlist')
def show_offers(message):
    offers = list(offers_col.find({"status": "active"}))
    if not offers:
        bot.reply_to(message, "अभी कोई ऑफर उपलब्ध नहीं है।")
        return
    
    markup = types.InlineKeyboardMarkup()
    for offer in offers:
        markup.add(types.InlineKeyboardButton(f"{offer['name']} - ₹{offer['price']}", callback_data=f"view_{offer['_id']}"))
    
    bot.send_message(message.chat.id, "🔥 ताज़ा ऑफर्स की लिस्ट:", reply_markup=markup)

# --- ऑफर डिटेल्स (Callback) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('view_'))
def offer_details(call):
    off_id = call.data.split('_')[1]
    offer = offers_col.find_one({"_id": off_id})
    
    text = (f"💎 **ऑफर:** {offer['name']}\n"
            f"💰 **रिवॉर्ड:** ₹{offer['price']}\n"
            f"📝 **विवरण:** {offer['details']}\n\n"
            f"⚠️ **कंडीशन:** `{offer['condition']}`")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔗 Claim (In-App)", web_app=types.WebAppInfo(url=offer['claim_url'])))
    markup.add(types.InlineKeyboardButton("🔍 Track Status", callback_data=f"track_{off_id}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_to_list"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
    
    # Task Initiated State
    users_col.update_one({"_id": call.from_user.id}, {"$set": {"current_task": off_id, "task_status": "initiated"}})

# --- 🔍 लाइव ट्रैकिंग (Track Button) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('track_'))
def track_task(call):
    off_id = call.data.split('_')[1]
    offer = offers_col.find_one({"_id": off_id})
    user_id = call.from_user.id
    
    bot.answer_callback_query(call.id, "लाइव स्टेटस चेक किया जा रहा है... कृपया इंतज़ार करें।")
    
    # स्क्रीनशॉट लॉजिक
    photo_path = f"track_{user_id}.png"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    success = loop.run_until_loop_complete(take_screenshot(offer['track_url'], photo_path))
    
    if success:
        with open(photo_path, 'rb') as photo:
            bot.send_photo(user_id, photo, caption="📸 आपका लाइव ट्रैकिंग स्क्रीनशॉट।\nअगर सब सही है तो 'Submit Proof' करें।")
        os.remove(photo_path)
    else:
        bot.send_message(user_id, "🌐 वेबसाइट व्यस्त है, कृपया कुछ देर बाद ट्रैक करें।")

# --- 📤 सबमिट प्रूफ (Persistence Logic) ---
@bot.message_handler(func=lambda m: m.text == '📤 Submit Proof')
def submit_proof_start(message):
    user = users_col.find_one({"_id": message.from_user.id})
    if not user.get('current_task'):
        bot.reply_to(message, "⚠️ पहले ऑफरलिस्ट में जाकर किसी ऑफर को 'Claim' करें।")
        return
    
    msg = bot.send_message(message.chat.id, "📸 कृपया अपने पूरे हुए टास्क का स्क्रीनशॉट भेजें:")
    bot.register_next_step_handler(msg, process_proof_photo)

def process_proof_photo(message):
    if not message.photo:
        bot.reply_to(message, "❌ कृपया फोटो ही भेजें। फिर से 'Submit Proof' दबाएं।")
        return
    
    photo_id = message.photo[-1].file_id
    msg = bot.send_message(message.chat.id, "💰 अपनी UPI ID भेजें (जैसे: 12345@ybl):")
    bot.register_next_step_handler(msg, process_proof_upi, photo_id)

def process_proof_upi(message, photo_id):
    upi = message.text
    if not validate_upi(upi):
        bot.reply_to(message, "❌ गलत UPI फॉर्मेट! कृपया सही ID डालें, वरना पेमेंट फेल हो जाएगी।")
        return
    
    # एडमिन को भेजना
    bot.send_photo(ADMIN_ID, photo_id, caption=f"📩 **नया प्रूफ!**\nUser: {message.from_user.id}\nUPI: `{upi}`", 
                   reply_markup=admin_review_markup(message.from_user.id))
    bot.send_message(message.chat.id, "✅ आपका प्रूफ रिव्यू के लिए भेज दिया गया है।")

def admin_review_markup(user_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"app_{user_id}"),
               types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_{user_id}"))
    return markup

# --- ℹ️ About Section ---
@bot.message_handler(func=lambda m: m.text == 'ℹ️ About')
def about_sec(message):
    total_paid = stats_col.find_one({"_id": "global_stats"})
    amt = total_paid['total_distributed'] if total_paid else 0
    bot.reply_to(message, f"📊 **Loot Bot Stats**\n\n💰 कुल बांटा गया इनाम: ₹{amt}\n👥 एक्टिव यूजर्स: {users_col.count_documents({})}\n\nभरोसेमंद और तेज़ पेमेंट!")

# --- ⚙️ एडमिन पैनल (Secret Command: /admin) ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user.id): return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('➕ Add Offer', '📝 Edit Offer')
    markup.add('❌ Delete Offer', '📊 Change Status')
    markup.add('🔙 Exit Admin')
    bot.send_message(message.chat.id, "🛠 एडमिन कंट्रोल पैनल:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '➕ Add Offer')
def add_offer_step1(message):
    if not is_admin(message.from_user.id): return
    msg = bot.send_message(message.chat.id, "ऑफर का नाम लिखें:")
    bot.register_next_step_handler(msg, add_offer_step2)

def add_offer_step2(message):
    name = message.text
    msg = bot.send_message(message.chat.id, f"'{name}' की कीमत (₹) लिखें:")
    bot.register_next_step_handler(msg, add_offer_step3, name)

def add_offer_step3(message, name):
    price = message.text
    msg = bot.send_message(message.chat.id, "Claim URL भेजें:")
    bot.register_next_step_handler(msg, add_offer_step4, name, price)

def add_offer_step4(message, name, price):
    claim_url = message.text
    msg = bot.send_message(message.chat.id, "Tracking URL (Screenshot के लिए) भेजें:")
    bot.register_next_step_handler(msg, add_offer_final, name, price, claim_url)

def add_offer_final(message, name, price, claim_url):
    track_url = message.text
    offers_col.insert_one({
        "_id": str(time.time()), "name": name, "price": price, 
        "claim_url": claim_url, "track_url": track_url,
        "details": "Loot Now!", "condition": "Must complete all steps", "status": "active"
    })
    bot.send_message(message.chat.id, "✅ ऑफर सफलतापूर्वक जोड़ दिया गया!")

# --- Flask Thread ---
def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

if __name__ == "__main__":
    Thread(target=run_flask).start()
    print("🚀 All Systems Go!")
    bot.infinity_polling()
