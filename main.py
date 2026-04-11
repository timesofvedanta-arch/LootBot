import os
import telebot
from flask import Flask
from threading import Thread
from pymongo import MongoClient

# --- जानकारी ---
BOT_TOKEN = "8797754610:AAHwDu7n6d1U2Ma682BkIHD68k3vRlIwguQ"
MONGO_URI = "mongodb+srv://timesofvedanta:Mk626425@lootbot.ypsol8i.mongodb.net/?appName=Lootbot"

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

@app.route('/')
def home(): return "Bot is Alive"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# MongoDB
client = MongoClient(MONGO_URI)
db = client["loot_bot_db"]

@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('📜 Offerlist', '🛠 My Task')
    markup.add('👥 My Referral', '📤 Submit Proof')
    markup.add('ℹ️ About')
    bot.reply_to(message, "✅ बोट लाइव है और Docker के साथ चल रहा है!", reply_markup=markup)

# टेस्टिंग के लिए ट्रैक बटन (सिर्फ मैसेज देने के लिए)
@bot.message_handler(func=lambda m: m.text == '🛠 My Task')
def my_task(message):
    bot.reply_to(message, "प्रोग्रेस: स्क्रीनशॉट ट्रैकिंग सिस्टम तैयार किया जा रहा है...")

if __name__ == "__main__":
    Thread(target=run_web).start()
    bot.infinity_polling()
