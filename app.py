import os, logging, sqlite3
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# --- CONFIGURATION ---
ADMIN_ID = 1216607288  # अपनी असली टेलीग्राम ID यहाँ डालें
DB_NAME = "income_bot.db"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- DATABASE ENGINE ---
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
    db_query('''CREATE TABLE IF NOT EXISTS offers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, link TEXT, reward REAL, steps TEXT, status TEXT, expiry TEXT)''')

# --- UI KEYBOARDS ---
def main_menu_kb(user_id):
    kb = [
        [InlineKeyboardButton("🔥 Offer List", callback_data='view_offers')],
        [InlineKeyboardButton("💰 Wallet", callback_data='view_wallet')],
    ]
    if user_id == ADMIN_ID:
        kb.append([InlineKeyboardButton("🛠 Admin Panel", callback_data='admin_main')])
    return InlineKeyboardMarkup(kb)

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db_query("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
    await update.message.reply_text("🚀 TIMESOFVEDANTA INCOME में आपका स्वागत है!", reply_markup=main_menu_kb(user_id))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    await query.answer(f"Processing: {data}") # हर बटन पर नोटिफिकेशन

    # --- USER SIDE ---
    if data == 'view_offers':
        offers = db_query("SELECT id, name, status, expiry FROM offers", fetch=True)
        if not offers:
            await query.edit_message_text("अभी कोई ऑफर उपलब्ध नहीं है।", reply_markup=main_menu_kb(user_id))
            return
        
        btns = []
        for o in offers:
            status_emoji = "✅" if o[2] == 'Active' else "❌"
            btns.append([InlineKeyboardButton(f"{status_emoji} {o[1]} | Exp: {o[3]}", callback_data=f'off_det_{o[0]}')])
        btns.append([InlineKeyboardButton("🔙 Back", callback_data='main_menu')])
        await query.edit_message_text("🎁 उपलब्ध ऑफर्स की सूची:", reply_markup=InlineKeyboardMarkup(btns))

    elif data.startswith('off_det_'):
        off_id = data.split('_')[2]
        off = db_query("SELECT name, reward, steps, link FROM offers WHERE id=?", (off_id,), fetch=True)[0]
        text = f"📌 **नाम:** {off[0]}\n💰 **रिवॉर्ड:** ₹{off[1]}\n📝 **स्टेप्स:** {off[2]}"
        btns = [
            [InlineKeyboardButton("🔗 Tracking Link", web_app=WebAppInfo(url=off[3]))],
            [InlineKeyboardButton("✅ Claim Reward", callback_data=f'claim_{off_id}')],
            [InlineKeyboardButton("🔙 Back to Offers", callback_data='view_offers')]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')

    elif data.startswith('claim_'):
        off_id = data.split('_')[1]
        user_data = db_query("SELECT upi_id FROM users WHERE id=?", (user_id,), fetch=True)[0]
        if not user_data[0]:
            context.user_data['pending_claim'] = off_id
            await query.message.reply_text("⚠️ क्लेम करने के लिए अपनी UPI ID भेजें:")
        else:
            await query.message.reply_text(f"UPI ID: {user_data[0]} सत्यापित है।", 
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Open Verification", web_app=WebAppInfo(url="https://google.com"))]]))

    # --- ADMIN SIDE ---
    elif data == 'admin_main':
        btns = [
            [InlineKeyboardButton("➕ Add Offer", callback_data='add_off')],
            [InlineKeyboardButton("📜 List/Edit Offers", callback_data='admin_off_list')],
            [InlineKeyboardButton("🔙 Main Menu", callback_data='main_menu')]
        ]
        await query.edit_message_text("🛠 एडमिन कंट्रोल पैनल", reply_markup=InlineKeyboardMarkup(btns))

    elif data == 'main_menu':
        await query.edit_message_text("मुख्य मेनू:", reply_markup=main_menu_kb(user_id))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if 'pending_claim' in context.user_data:
        db_query("UPDATE users SET upi_id=? WHERE id=?", (text, user_id))
        del context.user_data['pending_claim']
        await update.message.reply_text("✅ UPI ID सुरक्षित कर ली गई है। अब क्लेम बटन पर दोबारा क्लिक करें।")

# --- SERVER ---
server = Flask(__name__)
@server.route('/')
def h(): return "Bot Active", 200

if __name__ == '__main__':
    init_db()
    TOKEN = os.environ.get("BOT_TOKEN")
    Thread(target=lambda: server.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling(drop_pending_updates=True)
