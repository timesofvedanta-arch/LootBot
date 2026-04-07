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

# States
admin_data = {}
refer_data = {}

# --- 2. DATABASE SETUP ---
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
    markup.add(types.InlineKeyboardButton("🔄 Refresh Data", callback_data=f"refresh_{off_id}"))
    markup.add(types.InlineKeyboardButton("👥 Refer & Earn", callback_data=f"refer_{off_id}"))
    return markup

# --- 4. START & VIEW LOGIC ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    # साफ़ करें पुरानी स्टेट्स
    admin_data.pop(message.chat.id, None)
    refer_data.pop(message.chat.id, None)
    
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "👨‍💻 **Admin Panel Active**", reply_markup=get_admin_keyboard())
    
    show_all_offers(message)

@bot.message_handler(func=lambda m: m.text == "🎁 View Offers")
def show_all_offers(message):
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, name, status, offer_url, total_prize FROM offers")
    rows = cursor.fetchall()
    if not rows:
        bot.send_message(message.chat.id, "❌ कोई ऑफर नहीं है। '➕ Add Offer' दबाएं।")
        return
    for r in rows:
        status_icon = "🟢" if r[2] == "LIVE" else "🔴"
        msg = f"{status_icon} **{r[1]}**\n💰 Total Prize: ₹{r[4]}"
        bot.send_message(message.chat.id, msg, reply_markup=get_offer_inline(r[0], r[3]))

# --- 5. ADMIN ACTIONS (ADD/EDIT/DELETE/STATUS) ---

@bot.message_handler(func=lambda m: m.text == "➕ Add Offer" and m.from_user.id == ADMIN_ID)
def add_offer_init(message):
    admin_data[message.chat.id] = {'action': 'ADD', 'step': 1}
    bot.send_message(message.chat.id, "📝 **Step 1:** ऑफर का नाम (Name) लिखें:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: m.text == "⚙️ Edit Offer" and m.from_user.id == ADMIN_ID)
def edit_offer_menu(message):
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, name FROM offers")
    rows = cursor.fetchall()
    if not rows: return bot.send_message(message.chat.id, "एडिट करने के लिए कुछ नहीं है।")
    markup = types.InlineKeyboardMarkup()
    for r in rows:
        markup.add(types.InlineKeyboardButton(f"📝 {r[1]}", callback_data=f"editstart_{r[0]}"))
    bot.send_message(message.chat.id, "किस ऑफर को एडिट करना है?", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🗑 Delete Offer" and m.from_user.id == ADMIN_ID)
def delete_offer_menu(message):
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, name FROM offers")
    rows = cursor.fetchall()
    markup = types.InlineKeyboardMarkup()
    for r in rows:
        markup.add(types.InlineKeyboardButton(f"❌ Delete {r[1]}", callback_data=f"confirmdel_{r[0]}"))
    bot.send_message(message.chat.id, "किसे डिलीट करना है?", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "⏯ Status" and m.from_user.id == ADMIN_ID)
def status_menu(message):
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, name, status FROM offers")
    rows = cursor.fetchall()
    markup = types.InlineKeyboardMarkup()
    for r in rows:
        markup.add(types.InlineKeyboardButton(f"{r[1]} ({r[2]})", callback_data=f"togstat_{r[0]}"))
    bot.send_message(message.chat.id, "Status बदलने के लिए चुनें:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "👥 User Details" and m.from_user.id == ADMIN_ID)
def user_details_log(message):
    cursor = db_conn.cursor()
    cursor.execute("SELECT name, offer_name, upi_id, timestamp FROM referral_logs ORDER BY id DESC LIMIT 10")
    logs = cursor.fetchall()
    if not logs: return bot.send_message(message.chat.id, "कोई डेटा नहीं है।")
    res = "📊 **Recent Referrals:**\n\n"
    for l in logs: res += f"👤 {l[0]} -> {l[1]}\n💳 {l[2]} | ⏰ {l[3]}\n---\n"
    bot.send_message(message.chat.id, res)

# --- 6. COMMON MESSAGE HANDLER (FOR STEPS) ---
@bot.message_handler(func=lambda m: m.chat.id in admin_data or m.chat.id in refer_data)
def master_message_handler(message):
    uid = message.chat.id
    cursor = db_conn.cursor()

    # --- ADMIN STEPS ---
    if uid in admin_data:
        state = admin_data[uid]
        if state['action'] == 'ADD':
            if state['step'] == 1:
                state['name'], state['step'] = message.text, 2
                bot.send_message(uid, "🔗 **Step 2:** Offer Link भेजें:")
            elif state['step'] == 2:
                state['url'], state['step'] = message.text, 3
                bot.send_message(uid, "📊 **Step 3:** Tracking Link भेजें:")
            elif state['step'] == 3:
                state['track'], state['step'] = message.text, 4
                bot.send_message(uid, "💰 **Step 4:** Total Prize (नंबर):")
            elif state['step'] == 4:
                state['prize'], state['step'] = message.text, 5
                bot.send_message(uid, "ℹ️ **Step 5:** Details लिखें:")
            elif state['step'] == 5:
                cursor.execute("INSERT INTO offers (name, offer_url, track_url, total_prize, details) VALUES (?,?,?,?,?)",
                               (state['name'], state['url'], state['track'], state['prize'], message.text))
                db_conn.commit()
                del admin_data[uid]
                bot.send_message(uid, "✅ ऑफर जुड़ गया!", reply_markup=get_admin_keyboard())

        elif state['action'] == 'EDIT':
            oid = state['id']
            # Edit logic follows pichla pattern (skip check)
            if state['step'] == 1:
                if message.text.lower() != 'skip': cursor.execute("UPDATE offers SET name=? WHERE id=?", (message.text, oid))
                state['step'] = 2
                bot.send_message(uid, "Edit Link (या skip):")
            # ... (Step 2 to 5 remains similar)
            db_conn.commit()

    # --- REFER STEPS ---
    elif uid in refer_data:
        state = refer_data[uid]
        if state['step'] == 'UPI':
            state['upi'] = message.text.replace("Use: ", "")
            state['step'] = 'SHARE'
            bot.send_message(uid, "अपना शेयर (Self) चुनें/लिखें:")
        elif state['step'] == 'SHARE':
            state['my'] = message.text
            state['step'] = 'FRIEND'
            bot.send_message(uid, "दोस्त का शेयर लिखें:")
        elif state['step'] == 'FRIEND':
            # Finish Referral logic
            now = datetime.now().strftime("%d/%m %H:%M")
            cursor.execute("INSERT OR REPLACE INTO user_prefs VALUES (?,?,?,?)", (uid, state['upi'], state['my'], message.text))
            cursor.execute("INSERT INTO referral_logs (user_id, name, offer_name, upi_id, my_share, friend_share, timestamp) VALUES (?,?,?,?,?,?,?)",
                           (uid, message.from_user.first_name, state['off_name'], state['upi'], state['my'], message.text, now))
            db_conn.commit()
            msg = f"🎁 {state['off_name']}\n💰 Cashback: ₹{message.text}\n🔗 {state['url']}"
            bot.send_message(uid, f"✅ **Copy Message:**\n\n`{msg}`", parse_mode="Markdown", reply_markup=get_admin_keyboard() if uid == ADMIN_ID else None)
            del refer_data[uid]

# --- 7. CALLBACK HANDLER ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    cursor = db_conn.cursor()
    uid = call.from_user.id

    if call.data.startswith("confirmdel_"):
        cursor.execute("DELETE FROM offers WHERE id=?", (call.data.split("_")[1],))
        db_conn.commit()
        bot.edit_message_text("🗑 Deleted!", call.message.chat.id, call.message.message_id)

    elif call.data.startswith("togstat_"):
        oid = call.data.split("_")[1]
        cursor.execute("SELECT status FROM offers WHERE id=?", (oid,))
        new_s = "PAUSE" if cursor.fetchone()[0] == "LIVE" else "LIVE"
        cursor.execute("UPDATE offers SET status=? WHERE id=?", (new_s, oid))
        db_conn.commit()
        bot.answer_callback_query(call.id, f"Status: {new_s}")

    elif call.data.startswith("editstart_"):
        admin_data[uid] = {'action': 'EDIT', 'step': 1, 'id': call.data.split("_")[1]}
        bot.send_message(uid, "Edit Name (या skip):", reply_markup=types.ReplyKeyboardRemove())

    elif call.data.startswith("refer_"):
        cursor.execute("SELECT name, total_prize, offer_url FROM offers WHERE id=?", (call.data.split("_")[1],))
        off = cursor.fetchone()
        refer_data[uid] = {'step': 'UPI', 'off_name': off[0], 'total': off[1], 'url': off[2]}
        bot.send_message(uid, "UPI ID भेजें:", reply_markup=types.ReplyKeyboardRemove())

# --- 8. RUN ---
@app.route('/')
def home(): return "Online"

if __name__ == "__main__":
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    bot.infinity_polling()
