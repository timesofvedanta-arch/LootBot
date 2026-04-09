import os, logging, sqlite3, asyncio
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# --- CONFIG ---
ADMIN_ID = 1216607288  # अपनी ID डालें
DB_NAME = "income_bot.db"
TOKEN = os.environ.get("BOT_TOKEN")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, upi_id TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS offers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, reward REAL, steps TEXT, link TEXT, expiry TEXT, status TEXT DEFAULT 'Active')''')
    conn.commit()
    conn.close()

def db_query(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(query, params)
    data = cursor.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return data

# --- KEYBOARDS ---
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
    await update.message.reply_text("🚀 **TIMESOFVEDANTA INCOME** सक्रिय है!", reply_markup=main_menu_kb(user_id))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer(f"Process: {query.data}")
    # बाकी लॉजिक यहाँ रहेगा...

# --- FLASK (FOR RENDER) ---
server = Flask(__name__)
@server.route('/')
def health(): return "Bot is running", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    server.run(host='0.0.0.0', port=port)

# --- MAIN ---
if __name__ == '__main__':
    init_db()
    if not TOKEN:
        print("BOT_TOKEN is missing!")
        exit(1)

    # Start Flask in thread
    Thread(target=run_flask, daemon=True).start()

    # Create Application
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    print("Starting Polling...")
    application.run_polling(drop_pending_updates=True)
