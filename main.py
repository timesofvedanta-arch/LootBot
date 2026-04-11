import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from pymongo import MongoClient

# --- आपकी जानकारी यहाँ जोड़ दी गई है ---
BOT_TOKEN = "8797754610:AAHwDu7n6d1U2Ma682BkIHD68k3vRlIwguQ"
MONGO_URI = "mongodb+srv://timesofvedanta:Mk626425@@lootbot.ypsol8i.mongodb.net/?appName=Lootbot"
ADMIN_ID = 1216607288  # आपकी Chat ID, ताकि आप एडमिन रहें

# MongoDB कनेक्शन सेट करें
try:
    # सुरक्षित कनेक्शन के लिए tlsAllowInvalidCertificates का उपयोग (Render के लिए जरूरी हो सकता है)
    client = MongoClient(MONGO_URI)
    db = client["loot_bot_db"]
    users_col = db["users"]
    print("✅ MongoDB से सफलतापूर्वक जुड़ गए!")
except Exception as e:
    print(f"❌ MongoDB कनेक्शन एरर: {e}")

# लॉगिंग (बोट की हलचल पर नज़र रखने के लिए)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

# --- मुख्य बटन (Keyboard) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # टाइपिंग बॉक्स के नीचे दिखने वाले स्थायी बटन
    keyboard = [
        ['📜 Offerlist', '🛠 My Task'],
        ['👥 My Referral', '📤 Submit Proof'],
        ['ℹ️ About']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # डेटाबेस में यूजर को सेव करना (अगर नया है)
    existing_user = users_col.find_one({"_id": user.id})
    if not existing_user:
        users_col.insert_one({
            "_id": user.id,
            "username": user.username,
            "name": user.first_name,
            "balance": 0,
            "referrals": 0,
            "tasks": [],
            "status": "active"
        })
        welcome_text = f"नमस्ते {user.first_name}! आपका स्वागत है। आपका अकाउंट बना दिया गया है।"
    else:
        welcome_text = f"वापसी पर स्वागत है {user.first_name}!"

    await update.message.reply_text(
        f"{welcome_text}\n\nकमाने के लिए नीचे दिए गए बटनों का उपयोग करें:",
        reply_markup=reply_markup
    )

def main():
    # बोट की एप्लीकेशन बनाना
    application = Application.builder().token(BOT_TOKEN).build()
    
    # /start कमांड को जोड़ना
    application.add_handler(CommandHandler("start", start))
    
    print("🚀 बोट शुरू हो रहा है...")
    application.run_polling()

if __name__ == '__main__':
    main()
