import sqlite3
import requests
import re
import time
from telebot import TeleBot, types
from telebot.types import WebAppInfo
from flask import Flask
from threading import Thread
from datetime import datetime

# --- 1. CONFIGURATION ---
API_TOKEN = 'YOUR_BOT_TOKEN' 
ADMIN_ID = 123456789  # <--- APNI ID YAHA DAALEIN
bot = TeleBot(API_TOKEN)
app = Flask('')

# Admin Steps Storage
admin_data = {}

# --- 2. DATABASE ---
def init_db():
    conn = sqlite3.connect('offers.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS offers 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, 
                       offer_url TEXT, track_url TEXT, details TEXT, 
                       status TEXT DEFAULT 'LIVE',
                       last_clicks TEXT DEFAULT '0', last_installs TEXT DEFAULT '0')''')
    conn.commit()
    return conn

db_conn = init_db()

# --- 3. SCRAPER ---
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

# --- 4. KEYBOARDS ---
def get_admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎁 View Offers", "➕ Add Offer")
    markup.row("⚙️ Edit Offer", "🗑 Delete Offer")
    markup.row("⏯ Change Status")
    return markup

def offer_details_markup(off_id, track_url):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎯 Claim Now", callback_data=f"claim_{off_id}"),
        types.InlineKeyboardButton("🔄 Refresh", callback_data=f"view_{off_id}")
    )
    markup.add(types.InlineKeyboardButton("🌐 Live Tracking (In-App)", web_app=WebAppInfo(url=track_url)))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="back_home"))
    return markup

# --- 5. START & NAVIGATION ---
@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "👨‍💻 **Admin Control Panel Active**", reply_markup=get_admin_keyboard(), parse_mode="Markdown")
    else:
        show_user_offers(message)

def show_user_offers(message):
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, name, status FROM offers")
    rows = cursor.fetchall()
    markup = types.InlineKeyboardMarkup()
    for r in rows:
        icon = "🟢" if r[2] == "LIVE" else "🔴"
        markup.add(types.InlineKeyboardButton(f"{icon} {r[1]}", callback_data=f"view_{r[0]}"))
    bot.send_message(message.chat.id, "🚀 **All Live Loot Offers:**", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🎁 View Offers")
def view_offers_admin(message):
    show_user_offers(message)

# --- 6. ADD OFFER (STEP-BY-STEP) ---
@bot.message_handler(func=lambda m: m.text == "➕ Add Offer" and m.from_user.id == ADMIN_ID)
def add_step_1(message):
    admin_data[message.chat.id] = {'action': 'ADD', 'step': 1}
    bot.send_message(message.chat.id, "📝 **Step 1:** Offer ka **Naam** likhein:")

# --- 7. EDIT OFFER (STEP-BY-STEP) ---
@bot.message_handler(func=lambda m: m.text == "⚙️ Edit Offer" and m.from_user.id == ADMIN_ID)
def edit_list(message):
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, name FROM offers")
    rows = cursor.fetchall()
    if not rows: return bot.send_message(message.chat.id, "Koi offer nahi hai.")
    markup = types.InlineKeyboardMarkup()
    for r in rows:
        markup.add(types.InlineKeyboardButton(f"Edit {r[1]}", callback_data=f"startedit_{r[0]}"))
    bot.send_message(message.chat.id, "Kise edit karna chahte hain?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("startedit_"))
def edit_step_1(call):
    off_id = call.data.split("_")[1]
    admin_data[call.message.chat.id] = {'action': 'EDIT', 'step': 1, 'id': off_id}
    bot.send_message(call.message.chat.id, "📝 **Edit Name:** Naya naam likhein ya type karein 'skip':")

# --- 8. DELETE OFFER ---
@bot.message_handler(func=lambda m: m.text == "🗑 Delete Offer" and m.from_user.id == ADMIN_ID)
def delete_list(message):
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, name FROM offers")
    rows = cursor.fetchall()
    markup = types.InlineKeyboardMarkup()
    for r in rows:
        markup.add(types.InlineKeyboardButton(f"❌ Delete {r[1]}", callback_data=f"confirmdel_{r[0]}"))
    bot.send_message(message.chat.id, "Kise delete karna hai?", reply_markup=markup)

# --- 9. CHANGE STATUS ---
@bot.message_handler(func=lambda m: m.text == "⏯ Change Status" and m.from_user.id == ADMIN_ID)
def status_list(message):
    cursor = db_conn.cursor()
    cursor.execute("SELECT id, name, status FROM offers")
    rows = cursor.fetchall()
    markup = types.InlineKeyboardMarkup()
    for r in rows:
        markup.add(types.InlineKeyboardButton(f"{r[1]} ({r[2]})", callback_data=f"setstat_{r[0]}"))
    bot.send_message(message.chat.id, "Status badalne ke liye offer chunein:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("setstat_"))
def status_toggle(call):
    off_id = call.data.split("_")[1]
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🟢 LIVE", callback_data=f"upstat_{off_id}_LIVE"),
               types.InlineKeyboardButton("🔴 PAUSE", callback_data=f"upstat_{off_id}_PAUSE"))
    bot.edit_message_text("Naya status chunein:", call.message.chat.id, call.message.message_id, reply_markup=markup)

# --- 10. GLOBAL MESSAGE HANDLER (FOR STEPS) ---
@bot.message_handler(func=lambda m: m.chat.id in admin_data)
def handle_admin_steps(message):
    data = admin_data[message.chat.id]
    text = message.text
    cursor = db_conn.cursor()

    # --- ADD LOGIC ---
    if data['action'] == 'ADD':
        if data['step'] == 1:
            data['name'] = text
            data['step'] = 2
            bot.send_message(message.chat.id, "🔗 **Step 2:** Offer Link (Claim Link) bhejein:")
        elif data['step'] == 2:
            data['off_url'] = text
            data['step'] = 3
            bot.send_message(message.chat.id, "📊 **Step 3:** Tracking Link (Dashboard Link) bhejein:")
        elif data['step'] == 3:
            data['track_url'] = text
            data['step'] = 4
            bot.send_message(message.chat.id, "ℹ️ **Step 4:** Offer ki Details likhein:")
        elif data['step'] == 4:
            cursor.execute("INSERT INTO offers (name, offer_url, track_url, details) VALUES (?,?,?,?)",
                           (data['name'], data['off_url'], data['track_url'], text))
            db_conn.commit()
            del admin_data[message.chat.id]
            bot.send_message(message.chat.id, "✅ **Success!** Naya offer add ho gaya.", reply_markup=get_admin_keyboard())

    # --- EDIT LOGIC ---
    elif data['action'] == 'EDIT':
        off_id = data['id']
        if data['step'] == 1:
            if text.lower() != 'skip': cursor.execute("UPDATE offers SET name=? WHERE id=?", (text, off_id))
            data['step'] = 2
            bot.send_message(message.chat.id, "🔗 **Edit Offer Link:** Naya link dein ya 'skip' likhein:")
        elif data['step'] == 2:
            if text.lower() != 'skip': cursor.execute("UPDATE offers SET offer_url=? WHERE id=?", (text, off_id))
            data['step'] = 3
            bot.send_message(message.chat.id, "📊 **Edit Tracking Link:** Naya link dein ya 'skip' likhein:")
        elif data['step'] == 3:
            if text.lower() != 'skip': cursor.execute("UPDATE offers SET track_url=? WHERE id=?", (text, off_id))
            data['step'] = 4
            bot.send_message(message.chat.id, "ℹ️ **Edit Details:** Nayi details likhein ya 'skip' likhein:")
        elif data['step'] == 4:
            if text.lower() != 'skip': cursor.execute("UPDATE offers SET details=? WHERE id=?", (text, off_id))
            db_conn.commit()
            del admin_data[message.chat.id]
            bot.send_message(message.chat.id, "✨ **Done!** Offer successfully update ho gaya.", reply_markup=get_admin_keyboard())

# --- 11. CALLBACK HANDLERS (VIEW/DELETE/STATUS) ---
@bot.callback_query_handler(func=lambda call: True)
def global_callback(call):
    cursor = db_conn.cursor()
    
    if call.data.startswith("view_"):
        off_id = call.data.split("_")[1]
        clicks, installs = get_live_stats(off_id)
        cursor.execute("SELECT name, details, track_url, status FROM offers WHERE id=?", (off_id,))
        off = cursor.fetchone()
        msg = f"🎯 **{off[0]}** ({off[3]})\n---\n🖱 Clicks: `{clicks}` | 📥 Installs: `{installs}`\n\n📝 {off[1]}"
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, 
                              reply_markup=offer_details_markup(off_id, off[2]), parse_mode="Markdown")

    elif call.data.startswith("confirmdel_"):
        off_id = call.data.split("_")[1]
        cursor.execute("DELETE FROM offers WHERE id=?", (off_id,))
        db_conn.commit()
        bot.answer_callback_query(call.id, "Deleted!")
        bot.edit_message_text("🗑 Offer delete kar diya gaya.", call.message.chat.id, call.message.message_id)

    elif call.data.startswith("upstat_"):
        _, off_id, new_stat = call.data.split("_")
        cursor.execute("UPDATE offers SET status=? WHERE id=?", (new_stat, off_id))
        db_conn.commit()
        bot.answer_callback_query(call.id, f"Status: {new_stat}")
        bot.edit_message_text(f"✅ Status badalkar **{new_stat}** kar diya gaya.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

    elif call.data == "back_home":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_user_offers(call.message)

# --- 12. RUN ---
@app.route('/')
def home(): return "Online"
Thread(target=lambda: app.run(host='0.0.0.0', port=8080)).start()
bot.infinity_polling()
