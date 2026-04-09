import os, logging, sqlite3
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, 
    CallbackQueryHandler, MessageHandler, filters, ConversationHandler
)

# --- CONFIGURATION ---
ADMIN_ID = 1216607288  # अपना असली टेलीग्राम ID यहाँ डालें (जैसे: 54637281)
DB_NAME = "income_bot.db"
ADD_NAME, ADD_REWARD, ADD_STEPS, ADD_LINK, ADD_EXPIRY = range(5)

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
    db_query('''CREATE TABLE IF NOT EXISTS offers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, reward REAL, steps TEXT, link TEXT, expiry TEXT, status TEXT DEFAULT 'Active')''')

# --- KEYBOARDS ---
def main_menu_kb(user_id):
    kb = [
        [InlineKeyboardButton("🔥 Offer List", callback_data='view_offers')],
        [InlineKeyboardButton("💰 Wallet", callback_data='view_wallet')],
    ]
    if user_id == ADMIN_ID:
        kb.append([InlineKeyboardButton("🛠 Admin Panel", callback_data='admin_main')])
    return InlineKeyboardMarkup(kb)

# --- USER HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db_query("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
    await update.message.reply_text("🚀 **TIMESOFVEDANTA INCOME** सक्रिय है!", reply_markup=main_menu_kb(user_id), parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    await query.answer(f"Action: {data}")

    if data == 'main_menu':
        await query.edit_message_text("मुख्य मेनू:", reply_markup=main_menu_kb(user_id))

    elif data == 'view_offers':
        offers = db_query("SELECT id, name, status, expiry FROM offers", fetch=True)
        if not offers:
            await query.edit_message_text("❌ कोई ऑफर उपलब्ध नहीं है।", reply_markup=main_menu_kb(user_id))
            return
        btns = [[InlineKeyboardButton(f"{'✅' if o[2]=='Active' else '❌'} {o[1]} | {o[3]}", callback_data=f'off_{o[0]}')] for o in offers]
        btns.append([InlineKeyboardButton("🔙 Back", callback_data='main_menu')])
        await query.edit_message_text("🎁 **उपलब्ध ऑफर्स:**", reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')

    elif data.startswith('off_'):
        off_id = data.split('_')[1]
        off = db_query("SELECT name, reward, steps, link, expiry FROM offers WHERE id=?", (off_id,), fetch=True)[0]
        text = f"📌 **ऑफर:** {off[0]}\n💰 **रिवॉर्ड:** ₹{off[1]}\n⏳ **एक्सपायरी:** {off[4]}\n\n📝 **स्टेप्स:**\n{off[2]}"
        btns = [
            [InlineKeyboardButton("🔗 Tracking Link", web_app=WebAppInfo(url=off[3]))],
            [InlineKeyboardButton("✅ Claim Reward", callback_data=f'claim_{off_id}')],
            [InlineKeyboardButton("🔙 Back to Offers", callback_data='view_offers')]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')

    elif data.startswith('claim_'):
        user_data = db_query("SELECT upi_id FROM users WHERE id=?", (user_id,), fetch=True)[0]
        if not user_data[0]:
            context.user_data['waiting_upi'] = True
            await query.message.reply_text("⚠️ क्लेम के लिए अपनी UPI ID भेजें:")
        else:
            await query.message.reply_text(f"✅ UPI: {user_data[0]} सत्यापित है। अब वेरिफिकेशन विंडो खोलें।", 
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Open Verification", web_app=WebAppInfo(url="https://google.com"))]]))

    elif data == 'admin_main' and user_id == ADMIN_ID:
        btns = [[InlineKeyboardButton("➕ Add New Offer", callback_data='add_start')],
                [InlineKeyboardButton("🗑 Delete Offer", callback_data='del_start')],
                [InlineKeyboardButton("🔙 Main Menu", callback_data='main_menu')]]
        await query.edit_message_text("🛠 **एडमिन पैनल**", reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')

# --- ADMIN CONVERSATION (ADD OFFER) ---
async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("1️⃣ ऑफर का नाम भेजें:")
    return ADD_NAME

async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_off_name'] = update.message.text
    await update.message.reply_text("2️⃣ रिवॉर्ड अमाउंट भेजें (जैसे: 50):")
    return ADD_REWARD

async def add_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_off_price'] = update.message.text
    await update.message.reply_text("3️⃣ स्टेप्स और टर्म्स भेजें:")
    return ADD_STEPS

async def add_steps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_off_steps'] = update.message.text
    await update.message.reply_text("4️⃣ ट्रैकिंग लिंक (URL) भेजें:")
    return ADD_LINK

async def add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_off_link'] = update.message.text
    await update.message.reply_text("5️⃣ एक्सपायरी टाइम भेजें (जैसे: 24h या 2 Days):")
    return ADD_EXPIRY

async def add_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = context.user_data
    db_query("INSERT INTO offers (name, reward, steps, link, expiry) VALUES (?,?,?,?,?)", 
             (d['new_off_name'], d['new_off_price'], d['new_off_steps'], d['new_off_link'], update.message.text))
    await update.message.reply_text("✅ ऑफर सफलतापूर्वक ऐड हो गया!", reply_markup=main_menu_kb(ADMIN_ID))
    return ConversationHandler.END

# --- MESSAGE HANDLER ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_upi'):
        db_query("UPDATE users SET upi_id=? WHERE id=?", (update.message.text, update.effective_user.id))
        context.user_data['waiting_upi'] = False
        await update.message.reply_text("✅ UPI ID सेव हो गई! अब क्लेम बटन दबाएं।")

# --- SERVER ---
server = Flask(__name__)
@server.route('/')
def h(): return "Active", 200

if __name__ == '__main__':
    init_db()
    TOKEN = os.environ.get("BOT_TOKEN")
    Thread(target=lambda: server.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))).start()
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_start, pattern='^add_start$')],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            ADD_REWARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reward)],
            ADD_STEPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_steps)],
            ADD_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_link)],
            ADD_EXPIRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_finish)],
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling(drop_pending_updates=True)
