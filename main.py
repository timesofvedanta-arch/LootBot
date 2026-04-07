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

# --- 1. कॉन्फ़िगरेशन (Configuration) ---
API_TOKEN = os.environ.get("API_TOKEN", "YOUR_BOT_TOKEN") 
ADMIN_ID = int(os.environ.get("ADMIN_ID", 123456789)) 
bot = TeleBot(API_TOKEN)
app = Flask('')

# डिक्शनरी फॉर स्टेट मैनेजमेंट
admin_data = {}
refer_data = {}

# --- 2. डेटाबेस सेटअप (Database Setup) ---
def init_db():
    conn = sqlite3.connect('offers.db', check_same_thread=False)
    cursor = conn.cursor()
    # ऑफर्स टेबल
    cursor.execute('''CREATE TABLE IF NOT EXISTS offers 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, 
                       offer_url TEXT, track_url TEXT, details TEXT, 
                       status TEXT DEFAULT 'LIVE', total_prize TEXT DEFAULT '0',
                       last_clicks TEXT DEFAULT '0', last_installs TEXT DEFAULT '0')''')
    # यूजर प्रेफरेंस (UPI और अमाउंट याद रखने के लिए)
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_prefs 
                      (user_id INTEGER PRIMARY KEY, upi_id TEXT, my_share TEXT, friend_share TEXT)''')
    # एडमिन लॉग्स
    cursor.execute('''CREATE TABLE IF NOT EXISTS referral_logs 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, 
                       offer_name TEXT, upi_id TEXT, my_share TEXT, friend_share TEXT, timestamp TEXT)''')
    conn.commit()
    return conn

db_conn = init_db()

# --- 3. लाइव ट्रैकिंग (Live Tracking) ---
def get_live_stats(off_id):
    cursor = db_conn.cursor()
    cursor.execute("SELECT track_url, last_clicks, last_installs FROM offers WHERE id=?", (off_id,))
    row = cursor.fetchone()
    try:
        res = requests.get(f"{row[0]}&v={int(time.time())}", timeout=10)
        stats = re.findall(r'<b>(.*?)</b>', res.text)
        if len(stats) >= 4:
            cursor.execute("UPDATE offers SET last_clicks=?, last_installs=? WHERE id=?", (stats[2], stats[3], off_id))
            db_conn.commit()
            return stats[2], stats[3]
    except: pass
    return row[1], row[2]

# --- 4. कीबोर्ड्स (Keyboards) ---
def get_admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎁 View Offers", "➕ Add Offer")
    markup.row("⚙️ Edit Offer", "🗑 Delete Offer")
    markup.row("⏯ Status", "👥 User Details")
    return markup

def get_offer_inline(off_id, off_url):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎯 Claim Now (Inline)", web_app=WebAppInfo(url=off_url)))
    markup.add(types.InlineKeyboardButton("🔄 Refresh Data", callback_data=f"refresh_{off_id}"))
    markup.add(types.InlineKeyboardButton("👥 Refer & Earn", callback_data=f"refer_{off_id}"))
    return markup

# --- 5. मुख्य हैंडलर (Main Handlers) ---
@bot.message_handler(commands=['start'])
def start(message):
    refer_data.pop(message.chat.id, None)
    admin_data.pop(message.chat.id, None)
    
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "👨‍💻 **Admin Panel Active**", reply_markup=get_admin_keyboard())
    
    show_offers(message)

def show_offers(message):
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, name, status, offer_url, total_prize FROM offers WHERE status='LIVE'")
    rows = cursor.fetchall()
    
    if not rows:
        bot.send_message(message.chat.id, "❌ फिलहाल कोई ऑफर उपलब्ध नहीं है।")
        return

    for r in rows:
        clicks, installs = get_live_stats(r[0])
        msg = (f"🚀 **{r[1]}**\n"
               f"💰 Total Prize: ₹{r[4]}\n"
               f"📊 Stats: {clicks} Clicks | {installs} Installs")
        bot.send_message(message.chat.id, msg, reply_markup=get_offer_inline(r[0], r[3]))

# --- 6. एडमिन पैनल लॉजिक (Add/Edit Offers) ---
@bot.message_handler(func=lambda m: m.text == "➕ Add Offer" and m.from_user.id == ADMIN_ID)
def add_init(message):
    admin_data[message.chat.id] = {'action': 'ADD', 'step': 1}
    bot.send_message(message.chat.id, "📝 **Step 1:** ऑफर का नाम लिखें:")

@bot.message_handler(func=lambda m: m.text == "⚙️ Edit Offer" and m.from_user.id == ADMIN_ID)
def edit_list(message):
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, name FROM offers")
    rows = cursor.fetchall()
    markup = types.InlineKeyboardMarkup()
    for r in rows:
        markup.add(types.InlineKeyboardButton(f"📝 Edit {r[1]}", callback_data=f"startedit_{r[0]}"))
    bot.send_message(message.chat.id, "किस ऑफर को एडिट करना है?", reply_markup=markup)

@bot.message_handler(func=lambda m: m.chat.id in admin_data)
def handle_admin_flow(message):
    uid = message.chat.id
    state = admin_data[uid]
    txt = message.text
    cursor = db_conn.cursor()

    if state['action'] == 'ADD':
        if state['step'] == 1:
            state['name'], state['step'] = txt, 2
            bot.send_message(uid, "🔗 **Step 2:** Offer Link (Claim) भेजें:")
        elif state['step'] == 2:
            state['off_url'], state['step'] = txt, 3
            bot.send_message(uid, "📊 **Step 3:** Tracking Link (Dashboard) भेजें:")
        elif state['step'] == 3:
            state['track_url'], state['step'] = txt, 4
            bot.send_message(uid, "💰 **Step 4:** Total Prize (पूरा इनाम):")
        elif state['step'] == 4:
            state['prize'], state['step'] = txt, 5
            bot.send_message(uid, "ℹ️ **Step 5:** ऑफर की डिटेल्स लिखें:")
        elif state['step'] == 5:
            cursor.execute("INSERT INTO offers (name, offer_url, track_url, total_prize, details) VALUES (?,?,?,?,?)",
                           (state['name'], state['off_url'], state['track_url'], state['prize'], txt))
            db_conn.commit()
            del admin_data[uid]
            bot.send_message(uid, "✅ ऑफर सफलतापूर्वक जुड़ गया!", reply_markup=get_admin_keyboard())

    elif state['action'] == 'EDIT':
        oid = state['id']
        if state['step'] == 1:
            if txt.lower() != 'skip': cursor.execute("UPDATE offers SET name=? WHERE id=?", (txt, oid))
            state['step'] = 2
            bot.send_message(uid, "Edit Offer Link (या 'skip'):")
        elif state['step'] == 2:
            if txt.lower() != 'skip': cursor.execute("UPDATE offers SET offer_url=? WHERE id=?", (txt, oid))
            state['step'] = 3
            bot.send_message(uid, "Edit Tracking Link (या 'skip'):")
        elif state['step'] == 3:
            if txt.lower() != 'skip': cursor.execute("UPDATE offers SET track_url=? WHERE id=?", (txt, oid))
            state['step'] = 4
            bot.send_message(uid, "Edit Total Prize (या 'skip'):")
        elif state['step'] == 4:
            if txt.lower() != 'skip': cursor.execute("UPDATE offers SET total_prize=? WHERE id=?", (txt, oid))
            state['step'] = 5
            bot.send_message(uid, "Edit Details (या 'skip'):")
        elif state['step'] == 5:
            if txt.lower() != 'skip': cursor.execute("UPDATE offers SET details=? WHERE id=?", (txt, oid))
            db_conn.commit()
            del admin_data[uid]
            bot.send_message(uid, "✅ अपडेट हो गया!", reply_markup=get_admin_keyboard())

# --- 7. रेफरल सिस्टम (Referral System with Memory) ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("refer_"))
def refer_init(call):
    off_id = call.data.split("_")[1]
    uid = call.from_user.id
    cursor = db_conn.cursor()
    cursor.execute("SELECT name, total_prize, offer_url, details FROM offers WHERE id=?", (off_id,))
    off = cursor.fetchone()
    
    cursor.execute("SELECT upi_id, my_share, friend_share FROM user_prefs WHERE user_id=?", (uid,))
    prev = cursor.fetchone()
    
    refer_data[uid] = {'step': 'UPI', 'off_name': off[0], 'total': off[1], 'url': off[2], 'details': off[3]}
    
    if prev:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(f"Use: {prev[0]}", "बदलना है")
        bot.send_message(uid, f"पुरानी UPI: `{prev[0]}`\nक्या यही इस्तेमाल करें?", reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(uid, "अपनी **UPI ID** भेजें:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: m.chat.id in refer_data)
def handle_refer_flow(message):
    uid = message.chat.id
    state = refer_data[uid]
    txt = message.text
    cursor = db_conn.cursor()

    if state['step'] == 'UPI':
        state['upi'] = txt.replace("Use: ", "")
        cursor.execute("SELECT my_share, friend_share FROM user_prefs WHERE user_id=?", (uid,))
        prev_amt = cursor.fetchone()
        state['step'] = 'MY_AMT'
        if prev_amt:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.add(f"Same: Me {prev_amt[0]} / Friend {prev_amt[1]}", "नया चुनें")
            bot.send_message(uid, f"पिछला शेयर: खुद ₹{prev_amt[0]} | दोस्त ₹{prev_amt[1]}\nक्या यही रखें?", reply_markup=markup)
        else:
            bot.send_message(uid, f"कुल इनाम ₹{state['total']} है। आपको कितना चाहिए?")

    elif state['step'] == 'MY_AMT':
        if "Same: " in txt:
            nums = re.findall(r'\d+', txt)
            state['my_share'], state['friend_share'] = nums[0], nums[1]
            complete_referral(message, state)
        else:
            state['my_share'] = txt
            state['step'] = 'FRIEND_AMT'
            bot.send_message(uid, "दोस्त को कितना मिलना चाहिए?")

    elif state['step'] == 'FRIEND_AMT':
        state['friend_share'] = txt
        complete_referral(message, state)

def complete_referral(message, state):
    uid = message.chat.id
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    cursor = db_conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO user_prefs VALUES (?,?,?,?)", (uid, state['upi'], state['my_share'], state['friend_share']))
    cursor.execute("INSERT INTO referral_logs (user_id, name, offer_name, upi_id, my_share, friend_share, timestamp) VALUES (?,?,?,?,?,?,?)",
                   (uid, message.from_user.first_name, state['off_name'], state['upi'], state['my_share'], state['friend_share'], now))
    db_conn.commit()

    ref_msg = (f"🎁 **Loot: {state['off_name']}**\n"
               f"💰 आपको मिलेगा: ₹{state['friend_share']} Cashback\n"
               f"💳 Payment: UPI ({state['upi']})\n\n"
               f"🔗 Link: {state['url']}\n"
               f"📝 Details: {state['details']}")
    
    bot.send_message(uid, "✅ कॉपी करने के लिए नीचे दबाएं:", reply_markup=get_admin_keyboard() if uid == ADMIN_ID else types.ReplyKeyboardRemove())
    bot.send_message(uid, f"```\n{ref_msg}\n```", parse_mode="MarkdownV2")
    del refer_data[uid]

# --- 8. एडमिन यूटिलिटीज (User Details & Status) ---
@bot.message_handler(func=lambda m: m.text == "👥 User Details" and m.from_user.id == ADMIN_ID)
def admin_logs(message):
    cursor = db_conn.cursor()
    cursor.execute("SELECT name, offer_name, upi_id, timestamp FROM referral_logs ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()
    res = "📊 **Recent Referrals:**\n\n"
    for r in rows: res += f"👤 {r[0]} | 🎯 {r[1]}\n💳 {r[2]} | ⏰ {r[3]}\n---\n"
    bot.send_message(ADMIN_ID, res)

@bot.message_handler(func=lambda m: m.text == "⏯ Status" and m.from_user.id == ADMIN_ID)
def admin_status_list(message):
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, name, status FROM offers")
    rows = cursor.fetchall()
    markup = types.InlineKeyboardMarkup()
    for r in rows:
        markup.add(types.InlineKeyboardButton(f"{r[1]} ({r[2]})", callback_data=f"togstat_{r[0]}"))
    bot.send_message(ADMIN_ID, "Status बदलें:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    cursor = db_conn.cursor()
    if call.data.startswith("refresh_"):
        off_id = call.data.split("_")[1]
        c, i = get_live_stats(off_id)
        bot.answer_callback_query(call.id, f"Live Stats: {c} Clicks")
    
    elif call.data.startswith("startedit_"):
        oid = call.data.split("_")[1]
        admin_data[call.message.chat.id] = {'action': 'EDIT', 'step': 1, 'id': oid}
        bot.send_message(call.message.chat.id, "Edit Name (या 'skip' लिखें):")

    elif call.data.startswith("togstat_"):
        oid = call.data.split("_")[1]
        cursor.execute("SELECT status FROM offers WHERE id=?", (oid,))
        curr = cursor.fetchone()[0]
        new_s = "PAUSE" if curr == "LIVE" else "LIVE"
        cursor.execute("UPDATE offers SET status=? WHERE id=?", (new_s, oid))
        db_conn.commit()
        bot.answer_callback_query(call.id, f"Status: {new_s}")
        admin_status_list(call.message)

    elif call.data.startswith("confirmdel_"):
        cursor.execute("DELETE FROM offers WHERE id=?", (call.data.split("_")[1],))
        db_conn.commit()
        bot.edit_message_text("🗑 Deleted!", call.message.chat.id, call.message.message_id)

# --- 9. रेंडर के लिए वेब सर्वर (Keep Alive) ---
@app.route('/')
def home(): return "Bot is Alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
