import os, logging, sqlite3
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, 
    CallbackQueryHandler, MessageHandler, filters, ConversationHandler
)

# --- CONFIGURATION ---
ADMIN_ID = 1216607288  # अपना असली टेलीग्राम ID यहाँ डालें
DB_NAME = "income_bot.db"
ADD_NAME, ADD_REWARD, ADD_STEPS, ADD_LINK, ADD_EXPIRY = range(5)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- DATABASE ---
def db_query(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(query, params)
    data = cursor.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return data

def init_db():
    db_query('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, upi_id TEXT)''')
    db_query('''CREATE TABLE IF NOT EXISTS offers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, reward REAL, steps TEXT, link TEXT, expiry TEXT, status TEXT DEFAULT 'Active')''')

# --- UI ---
def main_menu_kb(user_id):
    kb = [[InlineKeyboardButton("🔥 Offer List", callback_data='view_offers')],
          [InlineKeyboardButton("💰 Wallet", callback_data='view_wallet')]]
    if user_id == ADMIN_ID:
        kb.append([InlineKeyboardButton("🛠 Admin Panel", callback_data='admin_main')])
    return InlineKeyboardMarkup(kb)

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db_query("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
    await update.message.reply_text("🚀 **TIMESOFVEDANTA INCOME** चालू है!", reply_markup=main_menu_kb(user_id), parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer(f"Action: {query.data}")

    if query.data == 'view_offers':
        offers = db_query("SELECT id, name, status, expiry FROM offers", fetch=True)
        if not offers:
            await query.edit_message_text("❌ अभी कोई ऑफर नहीं है।", reply_markup=main_menu_kb(user_id))
            return
        btns = [[InlineKeyboardButton(f"{o[1]} | {o[3]}", callback_data=f'off_{o[0]}')] for o in offers]
        btns.append([InlineKeyboardButton("🔙 Back", callback_data='main_menu')])
        await query.edit_message_text("🎁 **ऑफर लिस्ट:**", reply_markup=InlineKeyboardMarkup(btns))
    
    elif query.data == 'main_menu':
        await query.edit_message_text("मुख्य मेनू:", reply_markup=main_menu_kb(user_id))

# --- FLASK SERVER (RENDER FIX) ---
server = Flask(__name__)
@server.route('/')
def health(): return "I am Alive", 200

def run_flask():
    # Render इसी पोर्ट को चेक करता है
    port = int(os.environ.get("PORT", 8080))
    server.run(host='0.0.0.0', port=port)

# --- MAIN ---
if __name__ == '__main__':
    init_db()
    TOKEN = os.environ.get("BOT_TOKEN")
    
    # 1. Flask को पहले चालू करें ताकि रेंडर को सिग्नल मिल जाए
    Thread(target=run_flask, daemon=True).start()

    # 2. बोट को चालू करें
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("System is firing up...")
    # Polling शुरू करें
    app.run_polling(drop_pending_updates=True)
