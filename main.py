import telebot
import os
import sqlite3
from flask import Flask
from threading import Thread

# --- 1. CONFIGURATION ---
API_TOKEN = "8774434240:AAGBJx186xIRpbNli0_SklGTLw46fCqKts4" 
ADMIN_ID = 1216607288  # <--- YAHAN APNI ASLI ID DAALEIN

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- 2. DATABASE ---
def get_db():
    conn = sqlite3.connect('/tmp/vedanta.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS offers 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, 
                       url TEXT, prize TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 3. KEYBOARDS (ADMIN VS USER) ---

def get_keyboard(user_id):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    if user_id == ADMIN_ID:
        # Admin ko ye 3 buttons dikhenge
        markup.row("🎁 View Offers", "➕ Add Offer")
        markup.row("🗑 Delete Offer")
    else:
        # Normal User ko sirf ye 1 button dikhega
        markup.row("🎁 View Offers")
    return markup

# --- 4. HANDLERS ---

@bot.message_handler(commands=['start', 'menu'])
def start(message):
    user_id = message.from_user.id
    welcome_text = "💰 **TimesOfVedanta Income**\n\nWelcome! Use the buttons below:"
    if user_id == ADMIN_ID:
        welcome_text = "⚡ **Admin Mode Active**\nManage your offers below:"
    
    bot.send_message(message.chat.id, welcome_text, 
                     reply_markup=get_keyboard(user_id), 
                     parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🎁 View Offers")
def view_offers(message):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM offers")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "❌ No offers available right now.")
        return

    for r in rows:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🎯 Claim Now", url=r[2]))
        bot.send_message(message.chat.id, f"🟢 **{r[1]}**\n💰 Prize: ₹{r[3]}", 
                         reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "➕ Add Offer")
def add_offer(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(message.chat.id, "Format: `Name | Link | Prize`", parse_mode="Markdown")
    bot.register_next_step_handler(msg, save_offer)

def save_offer(message):
    try:
        name, url, prize = [i.strip() for i in message.text.split("|")]
        conn = get_db()
        conn.execute("INSERT INTO offers (name, url, prize) VALUES (?, ?, ?)", (name, url, prize))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, "✅ Added!", reply_markup=get_keyboard(ADMIN_ID))
    except:
        bot.send_message(message.chat.id, "❌ Error! Try again.")

@bot.message_handler(func=lambda m: m.text == "🗑 Delete Offer")
def delete_menu(message):
    if message.from_user.id != ADMIN_ID: return
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM offers")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        bot.send_message(message.chat.id, "Nothing to delete.")
        return

    markup = telebot.types.InlineKeyboardMarkup()
    for r in rows:
        markup.add(telebot.types.InlineKeyboardButton(f"❌ {r[1]}", callback_data=f"del_{r[0]}"))
    bot.send_message(message.chat.id, "Select to delete:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
def callback_del(call):
    off_id = call.data.split("_")[1]
    conn = get_db()
    conn.execute("DELETE FROM offers WHERE id=?", (off_id,))
    conn.commit()
    conn.close()
    bot.answer_callback_query(call.id, "Deleted!")
    bot.edit_message_text("🗑 Removed.", call.message.chat.id, call.message.message_id)

# --- 5. RUN SERVER ---
@app.route('/')
def home(): return "Running..."

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
