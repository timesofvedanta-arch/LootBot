import sqlite3
import os
import telebot
from telebot import types
from flask import Flask
from threading import Thread

# --- 1. CONFIGURATION ---
API_TOKEN = "8774434240:AAGBJx186xIRpbNli0_SklGTLw46fCqKts4"  # अपना टोकन यहाँ डालें
ADMIN_ID = 1216607288          # अपनी आईडी यहाँ डालें
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- 2. DATABASE SETUP ---
def get_db_connection():
    # Render पर डेटाबेस सेव रखने के लिए /tmp/ का उपयोग करें
    conn = sqlite3.connect('/tmp/vedanta.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS offers 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, 
                       url TEXT, prize TEXT, status TEXT DEFAULT 'LIVE')''')
    conn.commit()
    conn.close()

init_db()

# --- 3. KEYBOARDS ---
def admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎁 View Offers", "➕ Add Offer")
    markup.add("🗑 Delete Offer")
    return markup

def offer_inline_btn(off_id, url):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎯 Claim Now", url=url))
    markup.add(types.InlineKeyboardButton("👥 Refer & Earn", callback_data=f"ref_{off_id}"))
    return markup

# --- 4. BUTTON HANDLERS (CRITICAL FIX) ---

@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "💰 **TimesOfVedanta Admin Panel**", reply_markup=admin_keyboard())
    else:
        bot.send_message(message.chat.id, "👋 Welcome to TimesOfVedanta Income!")
        send_offers(message.chat.id)

# VIEW OFFERS FIX: यह बटन अब डेटाबेस से लाइव डेटा उठाएगा
@bot.message_handler(func=lambda m: m.text == "🎁 View Offers")
def view_offers_cmd(message):
    send_offers(message.chat.id)

def send_offers(chat_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM offers")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        bot.send_message(chat_id, "❌ अभी कोई ऑफर उपलब्ध नहीं है।")
        return

    for r in rows:
        status = "🟢" if r['status'] == "LIVE" else "🔴"
        text = f"{status} **{r['name']}**\n💰 Prize: ₹{r['prize']}"
        bot.send_message(chat_id, text, reply_markup=offer_inline_btn(r['id'], r['url']), parse_mode="Markdown")

# ADD OFFER LOGIC
@bot.message_handler(func=lambda m: m.text == "➕ Add Offer" and m.from_user.id == ADMIN_ID)
def add_offer(message):
    msg = bot.send_message(message.chat.id, "ऑफर का नाम और लिंक भेजें इस तरह:\n`Name | Link | Prize`", parse_mode="Markdown")
    bot.register_next_step_handler(msg, save_offer)

def save_offer(message):
    try:
        parts = message.text.split("|")
        name, url, prize = parts[0].strip(), parts[1].strip(), parts[2].strip()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO offers (name, url, prize) VALUES (?, ?, ?)", (name, url, prize))
        conn.commit()
        conn.close()
        
        bot.send_message(message.chat.id, "✅ ऑफर जुड़ गया!", reply_markup=admin_keyboard())
    except Exception as e:
        bot.send_message(message.chat.id, "❌ फॉर्मेट गलत है! फिर से कोशिश करें।")

# DELETE OFFER
@bot.message_handler(func=lambda m: m.text == "🗑 Delete Offer" and m.from_user.id == ADMIN_ID)
def delete_menu(message):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM offers")
    rows = cursor.fetchall()
    conn.close()

    if not rows: return bot.send_message(message.chat.id, "खाली है।")
    
    markup = types.InlineKeyboardMarkup()
    for r in rows:
        markup.add(types.InlineKeyboardButton(f"❌ {r['name']}", callback_data=f"del_{r['id']}"))
    bot.send_message(message.chat.id, "किसे डिलीट करना है?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    if call.data.startswith("del_"):
        off_id = call.data.split("_")[1]
        conn = get_db_connection()
        conn.execute("DELETE FROM offers WHERE id=?", (off_id,))
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, "डिलीट हो गया!")
        bot.edit_message_text("🗑 ऑफर हटा दिया गया।", call.message.chat.id, call.message.message_id)

# --- 5. RENDER KEEP ALIVE & PORT FIX ---
@app.route('/')
def index(): return "TimesOfVedanta Bot is Running!"

def run_flask():
    # Render का पोर्ट पकड़ने के लिए
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    # थ्रेडिंग ताकि फ्लास्क और बोट साथ चलें
    t = Thread(target=run_flask)
    t.start()
    print("Bot is starting...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
