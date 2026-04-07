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
API_TOKEN = os.environ.get("API_TOKEN", "YOUR_BOT_TOKEN") 
ADMIN_ID = int(os.environ.get("ADMIN_ID", 123456789)) 
bot = TeleBot(API_TOKEN)
app = Flask('')

# States Storage (States are now cleared on button clicks)
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

# --- 4. MAIN BUTTON HANDLERS (Priority) ---

@bot.message_handler(func=lambda m: m.text == "🎁 View Offers")
def view_offers_btn(message):
    admin_data.pop(message.chat.id, None) # Stop any ongoing add process
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, name, status, offer_url, total_prize FROM offers")
    rows = cursor.fetchall()
    if not rows:
        return bot.send_message(message.chat.id, "❌ कोई ऑफर नहीं मिला।")
    
    for r in rows:
        status_icon = "🟢" if r[2] == "LIVE" else "🔴"
        text = f"{status_icon} **{r[1]}**\n💰 Total Prize: ₹{r[4]}"
        bot.send_message(message.chat.id, text, reply_markup=get_offer_inline(r[0], r[3]), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "➕ Add Offer" and m.from_user.id == ADMIN_ID)
def add_offer_btn(message):
    admin_data[message.chat.id] = {'step': 1}
    bot.send_message(message.chat.id, "📝 **Add Offer Mode**\nStep 1: ऑफर का नाम भेजें:", reply_markup=get_admin_keyboard())

@bot.message_handler(func=lambda m: m.text == "🗑 Delete Offer" and m.from_user.id == ADMIN_ID)
def delete_offer_btn(message):
    admin_data.pop(message.chat.id, None)
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, name FROM offers")
    rows = cursor.fetchall()
    if not rows: return bot.send_message(message.chat.id, "डिलीट करने के लिए कुछ नहीं है।")
    
    markup = types.InlineKeyboardMarkup()
    for r in rows:
        markup.add(types.InlineKeyboardButton(f"❌ Delete {r[1]}", callback_data=f"del_{r[0]}"))
    bot.send_message(message.chat.id, "किसे डिलीट करना है?", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "👥 User Details" and m.from_user.id == ADMIN_ID)
def details_btn(message):
    cursor = db_conn.cursor()
    cursor.execute("SELECT name, offer_name, upi_id, timestamp FROM referral_logs ORDER BY id DESC LIMIT 10")
    logs = cursor.fetchall()
    if not logs: return bot.send_message(message.chat.id, "डेटा खाली है।")
    res = "📊 **Recent Referral Logs:**\n\n"
    for l in logs: res += f"👤 {l[0]} -> {l[1]}\n💳 {l[2]}\n⏰ {l[3]}\n---\n"
    bot.send_message(message.chat.id, res)

# --- 5. STEP-BY-STEP MESSAGE PROCESSING ---

@bot.message_handler(func=lambda m: True)
def master_handler(message):
    uid = message.chat.id
    txt = message.text
    cursor = db_conn.cursor()

    # If Admin is Adding an Offer
    if uid in admin_data:
        data = admin_data[uid]
        step = data['step']
        
        if step == 1:
            data.update({'name': txt, 'step': 2})
            bot.send_message(uid, "🔗 **Step 2:** Offer Link (Claim) भेजें:")
        elif step == 2:
            data.update({'url': txt, 'step': 3})
            bot.send_message(uid, "📊 **Step 3:** Tracking Link भेजें:")
        elif step == 3:
            data.update({'track': txt, 'step': 4})
            bot.send_message(uid, "💰 **Step 4:** Total Prize (नंबर):")
        elif step == 4:
            data.update({'prize': txt, 'step': 5})
            bot.send_message(uid, "ℹ️ **Step 5:** ऑफर की डिटेल्स लिखें:")
        elif step == 5:
            cursor.execute("INSERT INTO offers (name, offer_url, track_url, total_prize, details) VALUES (?,?,?,?,?)",
                           (data['name'], data['url'], data['track'], data['prize'], txt))
            db_conn.commit()
            del admin_data[uid]
            bot.send_message(uid, "✅ **Success!** ऑफर जुड़ गया।", reply_markup=get_admin_keyboard())

    # If User is in Referral Process
    elif uid in refer_data:
        data = refer_data[uid]
        if data['step'] == 'UPI':
            data.update({'upi': txt, 'step': 'MY_AMT'})
            bot.send_message(uid, "अपना शेयर (Self) लिखें:")
        elif data['step'] == 'MY_AMT':
            data.update({'my': txt, 'step': 'FRIEND_AMT'})
            bot.send_message(uid, "दोस्त का शेयर लिखें:")
        elif data['step'] == 'FRIEND_AMT':
            now = datetime.now().strftime("%d/%m %H:%M")
            cursor.execute("INSERT OR REPLACE INTO user_prefs VALUES (?,?,?,?)", (uid, data['upi'], data['my'], txt))
            cursor.execute("INSERT INTO referral_logs (user_id, name, offer_name, upi_id, my_share, friend_share, timestamp) VALUES (?,?,?,?,?,?,?)",
                           (uid, message.from_user.first_name, data['name'], data['upi'], data['my'], txt, now))
            db_conn.commit()
            msg = f"🎁 {data['name']}\n💰 Cashback: ₹{txt}\n🔗 {data['url']}"
            bot.send_message(uid, f"✅ **Copy Message:**\n\n`{msg}`", parse_mode="Markdown")
            del refer_data[uid]

# --- 6. CALLBACKS ---

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    cursor = db_conn.cursor()
    if call.data.startswith("del_"):
        cursor.execute("DELETE FROM offers WHERE id=?", (call.data.split("_")[1],))
        db_conn.commit()
        bot.edit_message_text("🗑 **ऑफर डिलीट कर दिया गया!**", call.message.chat.id, call.message.message_id)
    
    elif call.data.startswith("ref_"):
        cursor.execute("SELECT name, offer_url FROM offers WHERE id=?", (call.data.split("_")[1],))
        off = cursor.fetchone()
        refer_data[call.from_user.id] = {'step': 'UPI', 'name': off[0], 'url': off[1]}
        bot.send_message(call.message.chat.id, "अपनी **UPI ID** भेजें:")

# --- 7. RUN ---
@app.route('/')
def home(): return "Bot is Online"

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
    bot.infinity_polling()
