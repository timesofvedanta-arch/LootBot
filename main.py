import os
import logging
import asyncio
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from pymongo import MongoClient

# --- 1. रेंडर के लिए 'वेबसाइट' हिस्सा ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- 2. आपकी जानकारी ---
BOT_TOKEN = "8797754610:AAHwDu7n6d1U2Ma682BkIHD68k3vRlIwguQ"
MONGO_URI = "mongodb+srv://timesofvedanta:Mk626425@lootbot.ypsol8i.mongodb.net/?appName=Lootbot"
ADMIN_ID = 1216607288

# --- 3. MongoDB सेटअप ---
# कनेक्शन को सुरक्षित बनाने के लिए timeout जोड़ दिया है
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client["loot_bot_db"]
users_col = db["users"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 4. स्टार्ट कमांड ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        logger.info(f"Start command received from: {user.id}")
        
        keyboard = [
            ['📜 Offerlist', '🛠 My Task'],
            ['👥 My Referral', '📤 Submit Proof'],
            ['ℹ️ About']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        # डेटाबेस में एंट्री (बिना अटके)
        users_col.update_one(
            {"_id": user.id},
            {"$set": {"name": user.first_name, "status": "active"}},
            upsert=True
        )
        
        await update.message.reply_text(
            f"नमस्ते {user.first_name}! आपका बोट अब पूरी तरह चालू है।\n\nनीचे दिए गए बटनों का उपयोग करें:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in start command: {e}")

# --- 5. मुख्य फंक्शन ---
def main():
    # वेब सर्वर को अलग धागे (Thread) में चलाएं
    server_thread = Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()
    
    # बोट सेटअप
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    
    print("🚀 बोट सफलतापूर्वक शुरू हो गया है...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
