import os
import telebot
import time
import re
from flask import Flask
from threading import Thread
from pymongo import MongoClient
from telebot import types

# --- सेटअप (नया टोकन अपडेटेड) ---
BOT_TOKEN = "8797754610:AAHM-KFFsdNoBJa2VIfrew5uFvgwGvyL-uI" 
MONGO_URI = "mongodb+srv://timesofvedanta:Mk626425@lootbot.ypsol8i.mongodb.net/?appName=Lootbot"
ADMIN_ID = 1216607288

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

# MongoDB कनेक्शन
client = MongoClient(MONGO_URI)
db = client["loot_bot_db"]
users_col = db["users"]
offers_col = db["offers"]

@app.route('/')
def home(): return "Bot is Online"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# --- कीबोर्ड ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('📜 Offerlist', '🛠 My Task')
    markup.add('👥 My Referral', '📤 Submit Proof')
    markup.add('ℹ️ About')
    return markup

# --- कमांड्स ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if not users_col.find_one({"_id": user_id}):
        users_col.insert_one({"_id": user_id, "name": message.from_user.first_name, "balance": 0, "current_task": None})
    
    bot.send_message(user_id, f"नमस्ते {message.from_user.first_name}! आपका बोट अब तैयार है। लूट शुरू करें! 🔥", reply_markup=main_menu())

# --- एडमिन पैनल ---
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id == ADMIN_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add('➕ Add Offer', '❌ Delete Offer')
        markup.add('🔙 Exit Admin')
        bot.send_message(message.chat.id, "🛠 एडमिन कंट्रोल पैनल:", reply_markup=markup)
    else:
        bot.reply_to(message, "❌ केवल मालिक ही इसे देख सकता है।")

# --- एडमिन: ऑफर जोड़ना ---
@bot.message_handler(func=lambda m: m.text == '➕ Add Offer')
def add_offer(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(message.chat.id, "ऑफर का नाम लिखें:")
    bot.register_next_step_handler(msg, process_offer_name)

def process_offer_name(message):
    name = message.text
    msg = bot.send_message(message.chat.id, f"'{name}' के लिए कितने रुपये मिलेंगे? (जैसे: 10)")
    bot.register_next_step_handler(msg, process_offer_price, name)

def process_offer_price(message, name):
    price = message.text
    msg = bot.send_message(message.chat.id, "क्लेम लिंक (Link) भेजें:")
    bot.register_next_step_handler(msg, save_offer, name, price)

def save_offer(message, name, price):
    link = message.text
    offers_col.insert_one({
        "_id": str(time.time()), "name": name, "price": price, 
        "link": link, "status": "active"
    })
    bot.send_message(message.chat.id, "✅ ऑफर सफलतापूर्वक जुड़ गया!")

# --- यूजर बटन्स ---
@bot.message_handler(func=lambda m: True)
def handle_all(message):
    if message.text == '📜 Offerlist':
        offers = list(offers_col.find({"status": "active"}))
        if not offers:
            bot.reply_to(message, "अभी कोई ऑफर नहीं है।")
            return
        
        markup = types.InlineKeyboardMarkup()
        for off in offers:
            markup.add(types.InlineKeyboardButton(f"{off['name']} - ₹{off['price']}", callback_data=f"claim_{off['_id']}"))
        bot.send_message(message.chat.id, "🔥 लूट ऑफर्स:", reply_markup=markup)

    elif message.text == 'ℹ️ About':
        bot.reply_to(message, "📊 **Stats**\nकुल एक्टिव यूजर: " + str(users_col.count_documents({})) + "\nपेमेंट 100% गारंयटेड!")

    elif message.text == '🔙 Exit Admin':
        bot.send_message(message.chat.id, "एडमिन मोड बंद।", reply_markup=main_menu())

# --- क्लेम हैंडलिंग ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('claim_'))
def claim_offer(call):
    off_id = call.data.split('_')[1]
    offer = offers_col.find_one({"_id": off_id})
    users_col.update_one({"_id": call.from_user.id}, {"$set": {"current_task": off_id}})
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔗 Claim Now", url=offer['link']))
    bot.send_message(call.from_user.id, f"💎 **ऑफर:** {offer['name']}\n💰 **प्राइस:** ₹{offer['price']}\n\nटास्क पूरा करके 'Submit Proof' दबाएं।", reply_markup=markup)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling(drop_pending_updates=True)
