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

# --- 2. DATABASE (With Logging & Memory) ---
def init_db():
    conn = sqlite3.connect('offers.db', check_same_thread=False)
    cursor = conn.cursor()
    # Offers Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS offers 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, 
                       offer_url TEXT, track_url TEXT, details TEXT, 
                       status TEXT DEFAULT 'LIVE', total_prize TEXT DEFAULT '0')''')
    # User Preferences (To remember UPI and Amounts)
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_prefs 
                      (user_id INTEGER PRIMARY KEY, upi_id TEXT, my_share TEXT, friend_share TEXT)''')
    # Admin Logs (To track who referred what)
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

# --- 4. REFERRAL SYSTEM WITH MEMORY ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("refer_"))
def refer_step_start(call):
    off_id = call.data.split("_")[1]
    user_id = call.from_user.id
    
    cursor = db_conn.cursor()
    cursor.execute("SELECT name, total_prize, offer_url, details FROM offers WHERE id=?", (off_id,))
    off = cursor.fetchone()
    
    # Check if user has previous data
    cursor.execute("SELECT upi_id, my_share, friend_share FROM user_prefs WHERE user_id=?", (user_id,))
    prev = cursor.fetchone()
    
    refer_data[user_id] = {'step': 'UPI', 'off_id': off_id, 'off_name': off[0], 'total': off[1], 'url': off[2], 'details': off[3]}
    
    if prev:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(f"Use: {prev[0]}", "Badalna hai")
        bot.send_message(user_id, f"पसंद की UPI: `{prev[0]}`\nक्या आप यही रखना चाहते हैं या बदलना चाहते हैं?", reply_markup=markup, parse_mode="Markdown")
    else:
        bot.send_message(user_id, "अपनी **UPI ID** भेजें जहाँ आप पेमेंट लेना चाहते हैं:", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: m.chat.id in refer_data)
def handle_refer_logic(message):
    uid = message.chat.id
    state = refer_data[uid]
    text = message.text

    if state['step'] == 'UPI':
        if "Use: " in text:
            state['upi'] = text.replace("Use: ", "")
        else:
            state['upi'] = text
        
        # Next: Check Amount Preference
        cursor = db_conn.cursor()
        cursor.execute("SELECT my_share, friend_share FROM user_prefs WHERE user_id=?", (uid,))
        prev_amt = cursor.fetchone()
        
        state['step'] = 'AMOUNTS'
        if prev_amt:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.add(f"Same: Me {prev_amt[0]} / Friend {prev_amt[1]}", "Naya set karein")
            bot.send_message(uid, f"पिछला चुनाव: खुद ₹{prev_amt[0]} | दोस्त ₹{prev_amt[1]}\nक्या इसे बदलना है?", reply_markup=markup)
        else:
            bot.send_message(uid, f"ऑफर इनाम: ₹{state['total']}\nआपको कितना चाहिए? (नंबर लिखें):")

    elif state['step'] == 'AMOUNTS':
        if "Same: " in text:
            # Extract numbers from button text using Regex
            nums = re.findall(r'\d+', text)
            state['my_share'], state['friend_share'] = nums[0], nums[1]
            finish_referral(message, state)
        else:
            state['my_share'] = text
            state['step'] = 'FRIEND_AMT'
            bot.send_message(uid, "दोस्त को कितना मिलना चाहिए? (नंबर लिखें):")

    elif state['step'] == 'FRIEND_AMT':
        state['friend_share'] = text
        finish_referral(message, state)

def finish_referral(message, state):
    uid = message.chat.id
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Save/Update User Preference
    cursor = db_conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO user_prefs (user_id, upi_id, my_share, friend_share) VALUES (?,?,?,?)",
                   (uid, state['upi'], state['my_share'], state['friend_share']))
    
    # Log the action for Admin
    cursor.execute("INSERT INTO referral_logs (user_id, name, offer_name, upi_id, my_share, friend_share, timestamp) VALUES (?,?,?,?,?,?,?)",
                   (uid, message.from_user.first_name, state['off_name'], state['upi'], state['my_share'], state['friend_share'], now))
    db_conn.commit()

    # Generate Message
    ref_msg = (f"🎁 **Offer: {state['off_name']}**\n"
               f"💰 आपको मिलेगा: ₹{state['friend_share']} Cashback\n"
               f"🔗 Link: {state['url']}\n"
               f"📝 Details: {state['details']}")
    
    bot.send_message(uid, "✅ **मैसेज तैयार है!**\n\nनीचे वाले मैसेज को कॉपी करें:", reply_markup=get_admin_keyboard() if uid == ADMIN_ID else types.ReplyKeyboardRemove())
    bot.send_message(uid, f"```\n{ref_msg}\n```", parse_mode="MarkdownV2")
    
    del refer_data[uid]

# --- 5. ADMIN USER DETAILS BUTTON ---
@bot.message_handler(func=lambda m: m.text == "👥 User Details" and m.from_user.id == ADMIN_ID)
def show_admin_logs(message):
    cursor = db_conn.cursor()
    cursor.execute("SELECT name, offer_name, upi_id, timestamp FROM referral_logs ORDER BY id DESC LIMIT 10")
    logs = cursor.fetchall()
    
    if not logs:
        return bot.send_message(ADMIN_ID, "अभी तक कोई डेटा नहीं है।")
    
    report = "📊 **Recent Referral Activities:**\n\n"
    for l in logs:
        report += f"👤 {l[0]} -> {l[1]}\n💳 UPI: {l[2]}\n⏰ {l[3]}\n---\n"
    
    bot.send_message(ADMIN_ID, report)

# --- 6. ADD/EDIT WITH TOTAL PRIZE ---
@bot.message_handler(func=lambda m: m.text == "➕ Add Offer" and m.from_user.id == ADMIN_ID)
def admin_add_start(message):
    admin_data[message.chat.id] = {'action': 'ADD', 'step': 1}
    bot.send_message(message.chat.id, "1. Offer Name?")

@bot.message_handler(func=lambda m: m.chat.id in admin_data)
def handle_admin_steps(message):
    data = admin_data[message.chat.id]
    cursor = db_conn.cursor()
    # Step logic for Add/Edit (Name -> URL -> Track -> Prize -> Details)
    # [Total Prize step added in step 4]
    if data['step'] == 4: # Example step for Prize
        data['total_prize'] = message.text
        bot.send_message(message.chat.id, "5. Details?")
        data['step'] = 5
    # ... baki logic
