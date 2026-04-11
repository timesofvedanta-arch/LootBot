import os
import telebot
import time
import re
import threading
from flask import Flask
from pymongo import MongoClient
from telebot import types
from playwright.sync_api import sync_playwright

# ================= कॉन्फ़िगरेशन =================
BOT_TOKEN = "8797754610:AAHM-KFFsdNoBJa2VIfrew5uFvgwGvyL-uI" 
MONGO_URI = "mongodb+srv://timesofvedanta:Mk626425@lootbot.ypsol8i.mongodb.net/?appName=Lootbot"
ADMIN_ID = 1216607288

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

# ================= डेटाबेस सेटअप =================
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client["loot_bot_db"]
users_col = db["users"]
offers_col = db["offers"]
stats_col = db["stats"]

# ================= रेंडर वेब सर्वर =================
@app.route('/')
def home(): return "Bot is Alive & Running!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# ================= हेल्पर फंक्शन्स =================
def validate_upi(upi):
    return re.match(r'^[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}$', upi)

def take_screenshot(url, path):
    try:
        # Sync Playwright इस्तेमाल किया है ताकि बोट क्रैश न हो
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            page.wait_for_timeout(3000) # पेज लोड होने का इंतज़ार
            page.screenshot(path=path, full_page=True)
            browser.close()
        return True
    except Exception as e:
        print(f"Screenshot Error: {e}")
        return False

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('📜 Offerlist', '🛠 My Task')
    markup.add('👥 My Referral', '📤 Submit Proof')
    markup.add('ℹ️ About')
    return markup

# ================= स्टार्ट कमांड =================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    
    if not users_col.find_one({"_id": user_id}):
        users_col.insert_one({
            "_id": user_id, "name": name, "balance": 0, "referrals": 0,
            "current_task": None, "upi": None
        })
    bot.send_message(user_id, f"नमस्ते {name}! Loot Bot में आपका स्वागत है। 🔥\nनीचे दिए गए बटनों से पैसे कमाना शुरू करें:", reply_markup=main_menu())

# ================= एडमिन पैनल =================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ आप एडमिन नहीं हैं।")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('➕ Add Offer', '❌ Delete Offer', '🔙 Exit Admin')
    bot.send_message(message.chat.id, "🛠 **एडमिन पैनल**\nयहाँ से आप पूरे बोट को कंट्रोल कर सकते हैं:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == '➕ Add Offer')
def add_offer_start(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(message.chat.id, "1️⃣ ऑफर का नाम लिखें:")
    bot.register_next_step_handler(msg, add_offer_price)

def add_offer_price(message):
    name = message.text
    msg = bot.send_message(message.chat.id, f"2️⃣ '{name}' की कीमत (₹) लिखें:")
    bot.register_next_step_handler(msg, add_offer_link, name)

def add_offer_link(message, name):
    price = message.text
    msg = bot.send_message(message.chat.id, "3️⃣ ऑफर का क्लेम लिंक (URL) भेजें:")
    bot.register_next_step_handler(msg, add_offer_track, name, price)

def add_offer_track(message, name, price):
    claim_link = message.text
    msg = bot.send_message(message.chat.id, "4️⃣ ट्रैकिंग URL (Screenshot के लिए) भेजें:")
    bot.register_next_step_handler(msg, save_offer, name, price, claim_link)

def save_offer(message, name, price, claim_link):
    track_link = message.text
    offers_col.insert_one({
        "_id": str(int(time.time())), "name": name, "price": price, 
        "claim_link": claim_link, "track_link": track_link, "status": "active"
    })
    bot.send_message(message.chat.id, "✅ शानदार! ऑफर बोट में जुड़ गया है।")

@bot.message_handler(func=lambda m: m.text == '🔙 Exit Admin')
def exit_admin(message):
    if message.from_user.id != ADMIN_ID: return
    bot.send_message(message.chat.id, "✅ एडमिन पैनल बंद किया गया।", reply_markup=main_menu())

# ================= मुख्य बटन्स (User Panel) =================
@bot.message_handler(func=lambda m: m.text in ['📜 Offerlist', '🛠 My Task', '👥 My Referral', '📤 Submit Proof', 'ℹ️ About'])
def handle_main_buttons(message):
    user_id = message.from_user.id
    user = users_col.find_one({"_id": user_id})

    # --- Offerlist ---
    if message.text == '📜 Offerlist':
        offers = list(offers_col.find({"status": "active"}))
        if not offers:
            bot.reply_to(message, "अभी कोई ऑफर उपलब्ध नहीं है। कृपया बाद में चेक करें!")
            return
        markup = types.InlineKeyboardMarkup()
        for off in offers:
            markup.add(types.InlineKeyboardButton(f"🎁 {off['name']} - ₹{off['price']}", callback_data=f"view_{off['_id']}"))
        bot.send_message(message.chat.id, "🔥 **धमाकेदार ऑफर्स:**\nकिसी भी ऑफर पर क्लिक करें:", reply_markup=markup)

    # --- My Task ---
    elif message.text == '🛠 My Task':
        if not user or not user.get("current_task"):
            bot.reply_to(message, "आपने अभी तक कोई टास्क क्लेम नहीं किया है। पहले '📜 Offerlist' में जाएं।")
            return
        
        offer = offers_col.find_one({"_id": user["current_task"]})
        if not offer:
            bot.reply_to(message, "यह टास्क अब उपलब्ध नहीं है।")
            return

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔗 Continue Task", web_app=types.WebAppInfo(url=offer['claim_link'])))
        markup.add(types.InlineKeyboardButton("🔍 Live Track", callback_data=f"track_{offer['_id']}"))
        
        bot.send_message(message.chat.id, f"🛠 **आपका वर्तमान टास्क:**\n\n📌 नाम: {offer['name']}\n💰 रिवॉर्ड: ₹{offer['price']}\n\nनीचे से ट्रैक करें या टास्क जारी रखें:", reply_markup=markup)

    # --- Submit Proof ---
    elif message.text == '📤 Submit Proof':
        if not user or not user.get("current_task"):
            bot.reply_to(message, "⚠️ पहले किसी ऑफर को क्लेम करें और पूरा करें।")
            return
        msg = bot.send_message(message.chat.id, "📸 कृपया अपने पूरे हुए टास्क का **स्क्रीनशॉट** भेजें:")
        bot.register_next_step_handler(msg, process_proof_photo)

    # --- My Referral ---
    elif message.text == '👥 My Referral':
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        bot.reply_to(message, f"🎁 **रेफर एंड अर्न**\n\nअपने दोस्तों को इनवाइट करें और कमाएं!\n\nआपका रेफरल लिंक:\n`{ref_link}`", parse_mode="Markdown")

    # --- About ---
    elif message.text == 'ℹ️ About':
        total_users = users_col.count_documents({})
        bot.reply_to(message, f"📊 **Loot Bot Stats**\n\n👥 कुल एक्टिव यूजर्स: {total_users}\n⚡ तेज़ पेमेंट और 100% ट्रस्टेड!\n\nहेल्प के लिए एडमिन से संपर्क करें।")

# ================= कॉलबैक हैंडलर्स (Inline Buttons) =================
@bot.callback_query_handler(func=lambda call: call.data.startswith('view_'))
def view_offer(call):
    off_id = call.data.split('_')[1]
    offer = offers_col.find_one({"_id": off_id})
    if not offer: return bot.answer_callback_query(call.id, "ऑफर एक्सपायर हो गया है।")
    
    # टास्क यूजर के डेटाबेस में सेव करें (Persist My Task)
    users_col.update_one({"_id": call.from_user.id}, {"$set": {"current_task": off_id}})
    
    markup = types.InlineKeyboardMarkup()
    # In-App Browser (WebApp)
    markup.add(types.InlineKeyboardButton("🔗 Claim Now (In-App)", web_app=types.WebAppInfo(url=offer['claim_link'])))
    markup.add(types.InlineKeyboardButton("🔍 Track Status", callback_data=f"track_{off_id}"))
    
    text = f"💎 **ऑफर का नाम:** {offer['name']}\n💰 **रिवॉर्ड:** ₹{offer['price']}\n\n1️⃣ 'Claim Now' पर क्लिक करें।\n2️⃣ टास्क पूरा करें।\n3️⃣ 'Track Status' से चेक करें।"
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('track_'))
def track_task(call):
    off_id = call.data.split('_')[1]
    offer = offers_col.find_one({"_id": off_id})
    user_id = call.from_user.id
    
    bot.answer_callback_query(call.id, "लाइव ट्रैकिंग चालू है... इसमें 15-30 सेकंड लग सकते हैं।")
    bot.send_message(user_id, "⏳ सिस्टम पेज का स्क्रीनशॉट ले रहा है, कृपया इंतज़ार करें...")
    
    photo_path = f"screenshot_{user_id}.png"
    success = take_screenshot(offer['track_link'], photo_path)
    
    if success and os.path.exists(photo_path):
        with open(photo_path, 'rb') as photo:
            bot.send_photo(user_id, photo, caption="📸 आपका लाइव ट्रैकिंग स्क्रीनशॉट।\nअगर काम पूरा हो गया है, तो 'Submit Proof' पर क्लिक करें।")
        os.remove(photo_path)
    else:
        bot.send_message(user_id, "❌ वेबसाइट अभी रिस्पॉन्स नहीं दे रही है। कृपया टास्क पूरा करें और सीधा 'Submit Proof' करें।")

# ================= प्रूफ सबमिशन और UPI वैलिडेशन =================
def process_proof_photo(message):
    if not message.photo:
        msg = bot.reply_to(message, "❌ यह फोटो नहीं है। कृपया सिर्फ स्क्रीनशॉट (Photo) भेजें:")
        bot.register_next_step_handler(msg, process_proof_photo)
        return
    
    photo_id = message.photo[-1].file_id
    msg = bot.send_message(message.chat.id, "💰 बहुत बढ़िया! अब अपनी **UPI ID** भेजें (जैसे: mobile@paytm):")
    bot.register_next_step_handler(msg, process_proof_upi, photo_id)

def process_proof_upi(message, photo_id):
    upi = message.text
    if not validate_upi(upi):
        msg = bot.reply_to(message, "❌ गलत UPI फॉर्मेट! कृपया सही ID डालें (जैसे 123@ybl):")
        bot.register_next_step_handler(msg, process_proof_upi, photo_id)
        return
    
    user_id = message.from_user.id
    user = users_col.find_one({"_id": user_id})
    offer = offers_col.find_one({"_id": user.get("current_task")})
    
    # एडमिन को अप्रूवल के लिए भेजना
    caption = f"📩 **नया टास्क प्रूफ!**\n\n👤 यूजर ID: `{user_id}`\n🎁 ऑफर: {offer['name']} (₹{offer['price']})\n💳 UPI: `{upi}`"
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}_{offer['price']}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
    )
    
    bot.send_photo(ADMIN_ID, photo_id, caption=caption, parse_mode="Markdown", reply_markup=markup)
    
    # यूजर का टास्क रिसेट करें
    users_col.update_one({"_id": user_id}, {"$set": {"current_task": None, "upi": upi}})
    bot.send_message(message.chat.id, "✅ आपका प्रूफ एडमिन को भेज दिया गया है। 24 घंटे के अंदर पेमेंट मिल जाएगी!")

# ================= एडमिन अप्रूवल एक्शन =================
@bot.callback_query_handler(func=lambda call: call.data.startswith('approve_') or call.data.startswith('reject_'))
def admin_action(call):
    action, user_id = call.data.split('_')[0], int(call.data.split('_')[1])
    
    if action == "approve":
        price = int(call.data.split('_')[2])
        users_col.update_one({"_id": user_id}, {"$inc": {"balance": price}})
        bot.send_message(user_id, f"🎉 बधाई हो! आपका प्रूफ पास हो गया है। ₹{price} आपके खाते में भेज दिए गए हैं।")
        bot.edit_message_caption("✅ **Approved & Paid**", call.message.chat.id, call.message.message_id)
    else:
        bot.send_message(user_id, "❌ आपका प्रूफ रिजेक्ट कर दिया गया है। कृपया टास्क सही से पूरा करें।")
        bot.edit_message_caption("❌ **Rejected**", call.message.chat.id, call.message.message_id)

# ================= मेन रनर =================
if __name__ == "__main__":
    # Flask को बैकग्राउंड में चलाएं ताकि रेंडर पोर्ट न रोके
    threading.Thread(target=run_flask, daemon=True).start()
    print("🚀 All Systems Go! Bot is Running...")
    
    # Polling चालू करें (Try-Except के साथ ताकि क्रैश न हो)
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5, drop_pending_updates=True)
        except Exception as e:
            print(f"Polling Error: {e}")
            time.sleep(5)
