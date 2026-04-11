import os
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from pymongo import MongoClient

# आपकी जानकारी
BOT_TOKEN = "8797754610:AAHwDu7n6d1U2Ma682BkIHD68k3vRlIwguQ"
MONGO_URI = "mongodb+srv://timesofvedanta:Mk626425@lootbot.ypsol8i.mongodb.net/?appName=Lootbot"
ADMIN_ID = 1216607288

# --- रेंडर के लिए हेल्थ चेक सर्वर ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running")

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# MongoDB कनेक्शन
try:
    client = MongoClient(MONGO_URI, tlsAllowInvalidCertificates=True)
    db = client["loot_bot_db"]
    users_col = db["users"]
    print("✅ MongoDB Connection Successful")
except Exception as e:
    print(f"❌ MongoDB Error: {e}")

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [['📜 Offerlist', '🛠 My Task'], ['👥 My Referral', '📤 Submit Proof'], ['ℹ️ About']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    if not users_col.find_one({"_id": user.id}):
        users_col.insert_one({"_id": user.id, "name": user.first_name, "balance": 0, "status": "active"})
    
    await update.message.reply_text(f"नमस्ते {user.first_name}! आपका बोट अब रेंडर पर लाइव है।", reply_markup=reply_markup)

def main():
    # हेल्थ चेक सर्वर को अलग धागे (Thread) में चलाएं
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # बोट सेटअप
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    
    print("🚀 बोट शुरू हो रहा है...")
    application.run_polling()

if __name__ == '__main__':
    main()
