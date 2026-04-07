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

# --- 1. CONFIGURATION ---
API_TOKEN = "8774434240:AAGBJx186xIRpbNli0_SklGTLw46fCqKts4"
ADMIN_ID =  1216607288
bot = telebot.TeleBot(API_TOKEN)
app = Flask('')

# States Storage
admin_data = {}
refer_data = {}

# --- 2. DATABASE ---
def init_db():
    conn = sqlite3.connect('offers.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS offers 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, 
                       offer_url TEXT, track_url TEXT, details TEXT, 
                       status TEXT DEFAULT 'LIVE', total_prize TEXT DEFAULT '0')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_prefs 
                      (user_id INTEGER PRIMARY KEY, upi_id TEXT, my_share TEXT, friend_share TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS referral_logs 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, 
                       offer_name TEXT, upi_id TEXT, my_share TEXT, friend_share TEXT, timestamp TEXT)''')
    conn.commit()
    return conn

db_conn = init_db()

# --- 3. KEYBOARDS ---
def get_admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎁 View Offers", "➕ Add Offer")
    markup.row("⚙️ Edit Offer", "🗑 Delete Offer")
    markup.row("⏯ Status", "👥 User Details")
    return markup

def get_offer_inline(off_id, off_url):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎯 Claim Now", web_app=WebAppInfo(url=off_url)))
    markup.add(types.InlineKeyboardButton("👥 Refer & Earn", callback_data=f"ref_{off_id}"))
    return markup

# --- 4. MAIN HANDLERS ---

@bot.message_handler(commands=['start'])
def start(message):
    admin_data.pop(message.chat.id, None)
    refer_data.pop(message.chat.id, None)
    
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "👋 **Welcome Admin!**\nनीचे दिए गए बटनों का उपयोग करें।", reply_markup=get_admin_keyboard())
    else:
        bot.send_message(message.chat.id, "🚀 **Welcome to Loot Tracker!**")
        show_offers(message)

@bot.message_handler(func=lambda m: m.text == "🎁 View Offers")
def show_offers(message):
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, name, status, offer_url, total_prize FROM offers")
    rows = cursor.fetchall()
    
    if not rows:
        bot.send_message(message.chat.id, "❌ कोई ऑफर नहीं मिला। पहले '➕ Add Offer' करें।")
        return

    for r in rows:
        status_icon = "🟢" if r[2] == "LIVE" else "🔴"
        text = f"{status_icon} **{r[1]}**\n💰 Total Prize: ₹{r[4]}"
        bot.send_message(message.chat.id, text, reply_markup=get_offer_inline(r[0], r[3]), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "➕ Add Offer" and m.from_user.id == ADMIN_ID)
def add_offer_start(message):
    admin_data[message.chat.id] = {'step': 1}
    bot.send_message(message.chat.id, "📝 **Step 1:** ऑफर का नाम लिखें:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: m.text == "🗑 Delete Offer" and m.from_user.id == ADMIN_ID)
def delete_menu(message):
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, name FROM offers")
    rows = cursor.fetchall()
    if not rows: return bot.send_message(message.chat.id, "डिलीट करने के लिए कुछ नहीं है।")
    
    markup = types.InlineKeyboardMarkup()
    for r in rows:
        markup.add(types.InlineKeyboardButton(f"❌ Delete {r[1]}", callback_data=f"del_{r[0]}"))
    bot.send_message(message.chat.id, "किसे डिलीट करना है?", reply_markup=markup)

# --- 5. STEP-BY-STEP MESSAGE HANDLER ---
@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    uid = message.chat.id
    txt = message.text
    cursor = db_conn.cursor()

    # Admin Adding Offer Logic
    if uid in admin_data:
        step = admin_data[uid]['step']
        if step == 1:
            admin_data[uid].update({'name': txt, 'step': 2})
            bot.send_message(uid, "🔗 **Step 2:** Offer Link (Claim) भेजें:")
        elif step == 2:
            admin_data[uid].update({'url': txt, 'step': 3})
            bot.send_message(uid, "📊 **Step 3:** Tracking Link भेजें:")
        elif step == 3:
            admin_data[uid].update({'track': txt, 'step': 4})
            bot.send_message(uid, "💰 **Step 4:** Total Prize (सिर्फ नंबर):")
        elif step == 4:
            admin_data[uid].update({'prize': txt, 'step': 5})
            bot.send_message(uid, "ℹ️ **Step 5:** ऑफर की डिटेल्स लिखें:")
        elif step == 5:
            d = admin_data[uid]
            cursor.execute("INSERT INTO offers (name, offer_url, track_url, total_prize, details) VALUES (?,?,?,?,?)",
                           (d['name'], d['url'], d['track'], d['prize'], txt))
            db_conn.commit()
            del admin_data[uid]
            bot.send_message(uid, "✅ **Success!** ऑफर जुड़ गया।", reply_markup=get_admin_keyboard())

    # User Referral Logic
    elif uid in refer_data:
        step = refer_data[uid]['step']
        if step == 'UPI':
            refer_data[uid].update({'upi': txt, 'step': 'MY_AMT'})
            bot.send_message(uid, "अपना शेयर (Self) लिखें:")
        elif step == 'MY_AMT':
            refer_data[uid].update({'my': txt, 'step': 'FRIEND_AMT'})
            bot.send_message(uid, "दोस्त का शेयर लिखें:")
        elif step == 'FRIEND_AMT':
            d = refer_data[uid]
            now = datetime.now().strftime("%d/%m %H:%M")
            cursor.execute("INSERT OR REPLACE INTO user_prefs VALUES (?,?,?,?)", (uid, d['upi'], d['my'], txt))
            cursor.execute("INSERT INTO referral_logs (user_id, name, offer_name, upi_id, my_share, friend_share, timestamp) VALUES (?,?,?,?,?,?,?)",
                           (uid, message.from_user.first_name, d['name'], d['upi'], d['my'], txt, now))
            db_conn.commit()
            msg = f"🎁 {d['name']}\n💰 Cashback: ₹{txt}\n🔗 {d['url']}"
            bot.send_message(uid, f"✅ **Copy Message:**\n\n`{msg}`", parse_mode="Markdown", reply_markup=get_admin_keyboard() if uid == ADMIN_ID else None)
            del refer_data[uid]

# --- 6. CALLBACKS ---
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    cursor = db_conn.cursor()
    if call.data.startswith("del_"):
        cursor.execute("DELETE FROM offers WHERE id=?", (call.data.split("_")[1],))
        db_conn.commit()
        bot.edit_message_text("🗑 **Deleted!**", call.message.chat.id, call.message.message_id)
    
    elif call.data.startswith("ref_"):
        cursor.execute("SELECT name, offer_url FROM offers WHERE id=?", (call.data.split("_")[1],))
        off = cursor.fetchone()
        refer_data[call.from_user.id] = {'step': 'UPI', 'name': off[0], 'url': off[1]}
        bot.send_message(call.message.chat.id, "अपनी **UPI ID** भेजें:", reply_markup=types.ReplyKeyboardRemove())

# --- 7. RUN ---
@app.route('/')
def home(): return "Online"

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    bot.infinity_polling()
