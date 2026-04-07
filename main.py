import sqlite3
import requests
import re
import time
import os
from telebot import TeleBot, types
from telebot.types import WebAppInfo
from flask import Flask
from threading import Thread
from datetime import datetime

# --- 1. कॉन्फ़िगरेशन ---
API_TOKEN = os.environ.get("API_TOKEN", "YOUR_BOT_TOKEN") 
ADMIN_ID = int(os.environ.get("ADMIN_ID", 123456789)) 
bot = TeleBot(API_TOKEN)
app = Flask('')

admin_data = {}
refer_data = {}

# --- 2. डेटाबेस ---
def init_db():
    conn = sqlite3.connect('offers.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS offers 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, 
                       offer_url TEXT, track_url TEXT, details TEXT, 
                       status TEXT DEFAULT 'LIVE', total_prize TEXT DEFAULT '0',
                       last_clicks TEXT DEFAULT '0', last_installs TEXT DEFAULT '0')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_prefs 
                      (user_id INTEGER PRIMARY KEY, upi_id TEXT, my_share TEXT, friend_share TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS referral_logs 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, 
                       offer_name TEXT, upi_id TEXT, my_share TEXT, friend_share TEXT, timestamp TEXT)''')
    conn.commit()
    return conn

db_conn = init_db()

# --- 3. कीबोर्ड्स ---
def get_admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎁 View Offers", "➕ Add Offer")
    markup.row("⚙️ Edit Offer", "🗑 Delete Offer")
    markup.row("⏯ Status", "👥 User Details")
    return markup

def get_offer_inline(off_id, off_url):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎯 Claim Now", web_app=WebAppInfo(url=off_url)))
    markup.add(types.InlineKeyboardButton("🔄 Refresh Data", callback_data=f"refresh_{off_id}"))
    markup.add(types.InlineKeyboardButton("👥 Refer & Earn", callback_data=f"refer_{off_id}"))
    return markup

# --- 4. START & VIEW OFFERS ---
@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "👨‍💻 **Admin Control Panel**", reply_markup=get_admin_keyboard())
    show_offers_list(message)

@bot.message_handler(func=lambda m: m.text == "🎁 View Offers")
def show_offers_list(message):
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, name, status, offer_url, total_prize FROM offers")
    rows = cursor.fetchall()
    
    if not rows:
        bot.send_message(message.chat.id, "❌ कोई ऑफर नहीं मिला। '➕ Add Offer' पर क्लिक करें।")
        return

    for r in rows:
        msg = f"🚀 **{r[1]}** (Status: {r[2]})\n💰 Prize: ₹{r[4]}"
        bot.send_message(message.chat.id, msg, reply_markup=get_offer_inline(r[0], r[3]))

# --- 5. DELETE OFFER LOGIC (FIXED) ---
@bot.message_handler(func=lambda m: m.text == "🗑 Delete Offer" and m.from_user.id == ADMIN_ID)
def delete_menu(message):
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, name FROM offers")
    rows = cursor.fetchall()
    
    if not rows:
        bot.send_message(message.chat.id, "डिलीट करने के लिए कोई ऑफर नहीं है।")
        return

    markup = types.InlineKeyboardMarkup()
    for r in rows:
        markup.add(types.InlineKeyboardButton(f"❌ Delete {r[1]}", callback_data=f"confirmdel_{r[0]}"))
    
    bot.send_message(message.chat.id, "किस ऑफर को डिलीट करना चाहते हैं?", reply_markup=markup)

# --- 6. CALLBACK HANDLERS (FIXED) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    cursor = db_conn.cursor()
    
    # Delete Confirmation
    if call.data.startswith("confirmdel_"):
        off_id = call.data.split("_")[1]
        cursor.execute("DELETE FROM offers WHERE id=?", (off_id,))
        db_conn.commit()
        bot.answer_callback_query(call.id, "🗑 ऑफर डिलीट हो गया!")
        bot.edit_message_text("✅ ऑफर को सफलतापूर्वक डेटाबेस से हटा दिया गया है।", call.message.chat.id, call.message.message_id)

    # Refresh Stats
    elif call.data.startswith("refresh_"):
        bot.answer_callback_query(call.id, "🔄 डेटा सिंक हो रहा है...")
        # (Scraping logic can be added here)

    # Refer Logic
    elif call.data.startswith("refer_"):
        # (Referral logic from previous message stays same)
        pass

# --- 7. ADD/EDIT/STATUS (STAYS SAME) ---
# [Pichle code ka Add/Edit logic yahan add karein]

# --- 8. RUN ---
@app.route('/')
def home(): return "Bot Online"

if __name__ == "__main__":
    # Render support
    port = int(os.environ.get("PORT", 8080))
    Thread(target=lambda: app.run(host='0.0.0.0', port=port)).start()
    bot.infinity_polling()
