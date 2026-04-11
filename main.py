import os
import logging
import http.server
import socketserver
import threading
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from pymongo import MongoClient

# --- जानकारी ---
BOT_TOKEN = "8797754610:AAHwDu7n6d1U2Ma682BkIHD68k3vRlIwguQ"
MONGO_URI = "mongodb+srv://timesofvedanta:Mk626425@lootbot.ypsol8i.mongodb.net/?appName=Lootbot"
ADMIN_ID = 1216607288

# --- रेंडर के लिए फेक पोर्ट (Health Check के लिए) ---
def start_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

# MongoDB कनेक्शन
try:
    client = MongoClient(MONGO_URI)
    db = client["loot_bot_db"]
    users_col = db["users"]
    print("✅ MongoDB Connected!")
except Exception as e:
    print(f"❌ MongoDB Error: {e}")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [['📜 Offerlist', '🛠 My Task'], ['👥 My Referral', '📤 Submit Proof'], ['ℹ️ About']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    if not users_col.find_one({"_id": user.id}):
        users_col.insert_one({"_id": user.id, "name": user.first_name, "balance": 0, "status": "active"})
    
    await update.message.reply_text(f"नमस्ते {user.first_name}! बोट चालू है।", reply_markup=reply_markup)

def main():
    # रेंडर को शांत रखने के लिए बैकग्राउंड में सर्वर चलाना
    threading.Thread(target=start_server, daemon=True).start()
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    print("🚀 बोट शुरू हो रहा है...")
    application.run_polling()

if __name__ == '__main__':
    main()
