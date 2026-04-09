import os
import sqlite3
import random
import telebot
from flask import Flask, render_template_string
from threading import Thread

# --- 1. कॉन्फ़िगरेशन ---
# Render की Settings -> Environment Variables में API_TOKEN नाम से टोकन डालें
API_TOKEN = os.getenv('API_TOKEN')
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- 2. डेटाबेस मैनेजमेंट ---
def get_db():
    conn = sqlite3.connect('database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                upi_id TEXT,
                balance INTEGER DEFAULT 0
            )
        ''')
    print("Database Initialized.")

# --- 3. टेलीग्राम बोट लॉजिक ---
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    with get_db() as conn:
        conn.execute('INSERT OR IGNORE INTO users (chat_id) VALUES (?)', (chat_id,))
        conn.commit()
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('🎁 टास्क पूरा करें', '💰 बैलेंस', '📝 UPI अपडेट')
    
    msg = (
        "✨ **TIMESOFVEDANTA INCOME** ✨\n\n"
        "आपका स्वागत है! यहाँ आप टास्क पूरे करके **₹100 से ₹1500** तक कमा सकते हैं।\n\n"
        "नीचे दिए गए बटन का उपयोग करें।"
    )
    bot.send_message(chat_id, msg, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '🎁 टास्क पूरा करें')
def task(message):
    reward = random.randint(100, 1500)
    with get_db() as conn:
        conn.execute('UPDATE users SET balance = balance + ? WHERE chat_id = ?', (reward, message.chat.id))
        conn.commit()
    bot.reply_to(message, f"🎊 **बधाई हो!**\nआपने टास्क पूरा किया और **₹{reward}** प्राप्त किए।", parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '💰 बैलेंस')
def balance(message):
    with get_db() as conn:
        user = conn.execute('SELECT balance, upi_id FROM users WHERE chat_id = ?', (message.chat.id,)).fetchone()
    
    upi = user['upi_id'] if user['upi_id'] else "सेट नहीं है"
    bot.send_message(message.chat.id, f"💵 **आपका बैलेंस:** ₹{user['balance']}\n🔗 **UPI ID:** `{upi}`", parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '📝 UPI अपडेट')
def upi_ask(message):
    sent_msg = bot.reply_to(message, "कृपया अपनी **UPI ID** भेजें (जैसे: user@upi):", parse_mode='Markdown')
    bot.register_next_step_handler(sent_msg, upi_save)

def upi_save(message):
    with get_db() as conn:
        conn.execute('UPDATE users SET upi_id = ? WHERE chat_id = ?', (message.text, message.chat.id))
        conn.commit()
    bot.send_message(message.chat.id, f"✅ आपकी UPI ID **{message.text}** सुरक्षित सेव कर ली गई है।", parse_mode='Markdown')

# --- 4. वेब डैशबोर्ड (गोल्डन प्रीमियम लुक) ---
HTML = """
<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TIMESOFVEDANTA INCOME</title>
    <style>
        body {
            background: #0a0a0a;
            color: #d4af37;
            font-family: 'Segoe UI', sans-serif;
            display: flex; justify-content: center; align-items: center;
            height: 100vh; margin: 0;
        }
        .card {
            background: linear-gradient(145deg, #1a1a1a, #000);
            border: 2px solid #d4af37;
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            box-shadow: 0 0 25px rgba(212, 175, 55, 0.4);
            max-width: 400px;
        }
        h1 {
            background: linear-gradient(to right, #cf9e2e, #f9f295, #b38728);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.5em; margin: 0 0 10px 0;
        }
        .rupee-box { font-size: 1.8em; font-weight: bold; margin: 20px 0; }
        .footer { font-size: 0.8em; opacity: 0.6; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>TIMESOFVEDANTA INCOME</h1>
        <p>असली कमाई, सीधा आपके बैंक में।</p>
        <div class="rupee-box">₹100 - ₹1500</div>
        <p>काम शुरू करने के लिए बोट पर वापस जाएँ।</p>
        <div class="footer">© 2026 TIMESOFVEDANTA | All Rights Reserved</div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML)

# --- 5.Execution ---
def start_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    init_db()
    # बोट को अलग थ्रेड में चलाएं ताकि वेब सर्वर भी चलता रहे
    Thread(target=start_bot, daemon=True).start()
    # Render का पोर्ट गेट करें
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
