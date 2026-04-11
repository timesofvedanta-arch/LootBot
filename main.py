import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from pymongo import MongoClient

# --- रेंडर को धोखा देने के लिए छोटी सी वेबसाइट (Flask) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_web_server():
    # रेंडर पोर्ट 10000 या 8080 मांगता है
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- आपकी जानकारी ---
BOT_TOKEN = "8797754610:AAHwDu7n6d1U2Ma682BkIHD68k3vRlIwguQ"
MONGO_URI = "mongodb+srv://timesofvedanta:Mk626425@lootbot.ypsol8i.mongodb.net/?appName=Lootbot"
ADMIN_ID = 1216607288

# MongoDB कनेक्शन
try:
    client = MongoClient(MONGO_URI, tlsAllowInvalidCertificates=True)
    db = client["loot_bot_db"]
    users_col = db["users"]
    print("✅ MongoDB Connected")
except Exception as e:
    print(f"❌ MongoDB Error: {e}")

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [['📜 Offerlist', '🛠 My Task'], ['👥 My Referral', '📤 Submit Proof'], ['ℹ️ About']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    if not users_col.find_one({"_id": user.id}):
        users_col.insert_one({"_id": user.id, "name": user.first_name, "balance": 0, "status": "active"})
    
    await update.message.reply_text(f"नमस्ते {user.first_name}! आपका फ्री बोट अब लाइव है।", reply_markup=reply_markup)

def main():
    # 1. पहले वेब सर्वर को अलग धागे में शुरू करें
    t = Thread(target=run_web_server)
    t.start()
    
    # 2. बोट शुरू करें
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    
    print("🚀 बोट शुरू हो रहा है...")
    application.run_polling()

if __name__ == '__main__':
    main()
