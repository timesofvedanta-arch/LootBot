import os, logging, sqlite3, http.server, socketserver
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, 
    CallbackQueryHandler, MessageHandler, filters, ConversationHandler
)

# --- CONFIGURATION ---
ADMIN_ID = 1216607288  # <--- अपनी असली ID यहाँ डालें
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DB_NAME = "timesofvedanta.db"

# States for Admin Add/Edit
A_NAME, A_STATUS, A_EXPIRY, A_PRIZE, A_STEPS, A_TERMS, A_CLINK, A_TLINK = range(8)
# States for User Submit Proof
U_SELECT_OFFER, U_SCREENSHOT, U_UPI = range(8, 11)

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
    db_query('''CREATE TABLE IF NOT EXISTS offers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, status TEXT, expiry TEXT, prize TEXT, steps TEXT, terms TEXT, claim_link TEXT, track_link TEXT)''')
    db_query('''CREATE TABLE IF NOT EXISTS submissions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, offer_name TEXT, upi TEXT, photo_id TEXT, status TEXT DEFAULT 'Pending')''')
    db_query('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, upi_id TEXT)''')

# --- KEYBOARDS ---
def user_main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Offer List", callback_data='u_offers')],
        [InlineKeyboardButton("📱 Contact Us", url="https://wa.me/yournumber")],
        [InlineKeyboardButton("📤 Submit Proof", callback_data='u_submit_start')]
    ])

def admin_main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Users/Proofs", callback_data='a_view_proofs')],
        [InlineKeyboardButton("➕ Add Offer", callback_data='a_add_start'), InlineKeyboardButton("📜 Offer List", callback_data='a_off_list')],
        [InlineKeyboardButton("🔄 Change Status", callback_data='a_ch_status'), InlineKeyboardButton("🗑 Delete Offer", callback_data='a_del_off')],
        [InlineKeyboardButton("🔙 Main Menu", callback_data='main_home')]
    ])

# --- START COMMAND ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db_query("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
    
    text = "🚀 **TIMESOFVEDANTA INCOME** में आपका स्वागत है!"
    await update.message.reply_text(text, reply_markup=user_main_kb(), parse_mode='Markdown')

# --- USER SIDE LOGIC ---
async def show_offers(update: Update, context: ContextTypes.DEFAULT_TYPE, is_edit=True):
    offers = db_query("SELECT id, name, status, expiry, prize FROM offers", fetch=True)
    query = update.callback_query
    
    if not offers:
        btn = [[InlineKeyboardButton("📱 Contact Admin", url="https://wa.me/yournumber")]]
        txt = "❌ अभी कोई एक्टिव ऑफर नहीं है।"
        if is_edit: await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(btn))
        else: await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(btn))
        return

    btns = []
    for o in offers:
        color = "🟢" if o[2] == 'Active' else "🟡"
        btns.append([InlineKeyboardButton(f"{color} {o[1]} | ₹{o[4]} | Exp: {o[3]}", callback_data=f'u_det_{o[0]}')])
    btns.append([InlineKeyboardButton("🔙 Back", callback_data='main_home')])
    
    txt = "🎁 **उपलब्ध ऑफर्स की सूची:**"
    if is_edit: await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')
    else: await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')

async def offer_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    off_id = query.data.split('_')[2]
    o = db_query("SELECT name, status, prize, steps, terms, claim_link, track_link FROM offers WHERE id=?", (off_id,), fetch=True)[0]
    
    text = (f"📌 **Offer:** {o[0]}\n"
            f"💠 **Status:** {o[1]}\n"
            f"💰 **Prize:** ₹{o[2]}\n\n"
            f"📝 **Steps:**\n{o[3]}\n\n"
            f"⚠️ **Condition:**\n{o[4]}")
    
    btns = [
        [InlineKeyboardButton("🚀 Claim", web_app=WebAppInfo(url=o[5])), 
         InlineKeyboardButton("📍 Track", web_app=WebAppInfo(url=o[6]))],
        [InlineKeyboardButton("🔙 Back to List", callback_data='u_offers')]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')

# --- ADMIN: ADD OFFER CONVERSATION ---
async def a_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("1️⃣ ऑफर का नाम भेजें:")
    return A_NAME

async def a_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['n_name'] = update.message.text
    await update.message.reply_text("2️⃣ स्टेटस चुनें (Active/Pause):")
    return A_STATUS

async def a_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['n_status'] = update.message.text
    await update.message.reply_text("3️⃣ एक्सपायरी के दिन भेजें:")
    return A_EXPIRY

async def a_expiry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['n_exp'] = update.message.text
    await update.message.reply_text("4️⃣ इनाम की राशि (₹) भेजें:")
    return A_PRIZE

async def a_prize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['n_prize'] = update.message.text
    await update.message.reply_text("5️⃣ डिटेल और स्टेप्स भेजें:")
    return A_STEPS

async def a_steps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['n_steps'] = update.message.text
    await update.message.reply_text("6️⃣ टर्म एंड कंडीशन भेजें:")
    return A_TERMS

async def a_terms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['n_terms'] = update.message.text
    await update.message.reply_text("7️⃣ क्लेम लिंक (URL) भेजें:")
    return A_CLINK

async def a_clink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['n_clink'] = update.message.text
    await update.message.reply_text("8️⃣ ट्रैकिंग लिंक (URL) भेजें:")
    return A_TLINK

async def a_tlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = context.user_data
    db_query("INSERT INTO offers (name, status, expiry, prize, steps, terms, claim_link, track_link) VALUES (?,?,?,?,?,?,?,?)",
             (d['n_name'], d['n_status'], d['n_exp'], d['n_prize'], d['n_steps'], d['n_terms'], d['n_clink'], update.message.text))
    await update.message.reply_text("✅ ऑफर सफलतापूर्वक जुड़ गया!", reply_markup=admin_main_kb())
    return ConversationHandler.END

# --- WEB SERVER FOR RENDER ---
def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
        httpd.serve_forever()

# --- MAIN EXECUTION ---
if __name__ == '__main__':
    init_db()
    Thread(target=run_health_server, daemon=True).start()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Admin Add Offer Conv
    add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(a_add_start, pattern='^a_add_start$')],
        states={
            A_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, a_name)],
            A_STATUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, a_status)],
            A_EXPIRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, a_expiry)],
            A_PRIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, a_prize)],
            A_STEPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, a_steps)],
            A_TERMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, a_terms)],
            A_CLINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, a_clink)],
            A_TLINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, a_tlink)],
        },
        fallbacks=[CommandHandler("cancel", start)]
    )

    app.add_handler(add_conv)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons)) # Define this to route all callback_data
    
    app.run_polling(drop_pending_updates=True)
