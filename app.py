import os, logging, sqlite3, http.server, socketserver, time
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, 
    CallbackQueryHandler, MessageHandler, filters, ConversationHandler
)

# MongoDB Functions
from database import get_all_offers, save_offer, get_offer_by_id, delete_offer_by_id, offers_col

# --- CONFIGURATION ---
ADMIN_ID = 1216607288  
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DB_NAME = "timesofvedanta.db"

# States (Exact 13 as per your Zip)
(A_NAME, A_STATUS, A_EXPIRY, A_PRIZE, A_STEPS, A_TERMS, A_CLINK, A_TLINK, 
 U_SEL_OFF, U_SCREEN, U_UPI, E_SEL, E_VAL) = range(13)

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# SQLite for submissions only
def db_query(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(query, params)
    data = cursor.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return data

def init_db():
    db_query('''CREATE TABLE IF NOT EXISTS submissions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, offer_name TEXT, upi TEXT, photo_id TEXT, status TEXT DEFAULT 'Pending')''')
    db_query('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, upi_id TEXT)''')

# --- KEYBOARDS ---
def user_kb(uid):
    btns = [[InlineKeyboardButton("🔥 Offer List", callback_data='u_offers')],
            [InlineKeyboardButton("📤 Submit Proof", callback_data='u_sub_start')],
            [InlineKeyboardButton("📱 Contact Us", url="https://wa.me/8955399449")]]
    if uid == ADMIN_ID: btns.append([InlineKeyboardButton("🛠 Admin Panel", callback_data='a_panel')])
    return InlineKeyboardMarkup(btns)

def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add", callback_data='a_add'), InlineKeyboardButton("🗑 Delete", callback_data='a_del')],
        [InlineKeyboardButton("🔄 Status", callback_data='a_status'), InlineKeyboardButton("👥 User Proofs", callback_data='a_proofs')],
        [InlineKeyboardButton("📜 Offer List", callback_data='u_offers'), InlineKeyboardButton("🔙 Back", callback_data='home')]
    ])

# --- LOGIC ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db_query("INSERT OR IGNORE INTO users (id) VALUES (?)", (uid,))
    await update.message.reply_text("🚀 **TIMESOFVEDANTA** सक्रिय है!", reply_markup=user_kb(uid), parse_mode='Markdown')

async def u_offers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    offers = get_all_offers()
    if not offers:
        await query.edit_message_text("❌ अभी कोई ऑफर नहीं है।", reply_markup=user_kb(query.from_user.id))
        return
    btns = [[InlineKeyboardButton(f"{o['name']} | {'🟢' if o['status']=='Active' else '🟡'} | ₹{o['prize']}", callback_data=f"u_det_{o['id']}")] for o in offers]
    btns.append([InlineKeyboardButton("🔙 Back", callback_data='home')])
    await query.edit_message_text("🎁 **ऑफर लिस्ट:**", reply_markup=InlineKeyboardMarkup(btns))

async def u_det(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    oid = query.data.split('_')[2]
    o = get_offer_by_id(oid)
    if not o:
        await query.answer("Offer error!")
        return
    txt = f"📌 **{o['name']}**\n💰 Prize: ₹{o['prize']}\nExp: {o['expiry']}\n\n📝 **Steps:**\n{o['steps']}\n\n⚠️ **Terms:**\n{o['terms']}"
    # Claim and Track Buttons
    btns = [[InlineKeyboardButton("🚀 Claim", web_app=WebAppInfo(url=o['claim_link'])), 
             InlineKeyboardButton("📍 Track", web_app=WebAppInfo(url=o['track_link']))],
            [InlineKeyboardButton("🔙 Back", callback_data='u_offers')]]
    await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')

# --- ADMIN FLOW (Exact match with Zip) ---
async def a_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("1️⃣ नाम:")
    return A_NAME

async def a_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['n_name'] = update.message.text
    await update.message.reply_text("2️⃣ स्टेटस (Active/Pause):")
    return A_STATUS

async def a_status_in(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['n_st'] = update.message.text
    await update.message.reply_text("3️⃣ एक्सपायरी:")
    return A_EXPIRY

async def a_exp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['n_ex'] = update.message.text
    await update.message.reply_text("4️⃣ प्राइज:")
    return A_PRIZE

async def a_prz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['n_pr'] = update.message.text
    await update.message.reply_text("5️⃣ स्टेप्स:")
    return A_STEPS

async def a_stp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['n_step'] = update.message.text
    await update.message.reply_text("6️⃣ शर्ते:")
    return A_TERMS

async def a_trm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['n_term'] = update.message.text
    await update.message.reply_text("7️⃣ क्लेम लिंक:")
    return A_CLINK

async def a_cli(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['n_cl'] = update.message.text
    await update.message.reply_text("8️⃣ ट्रैक लिंक:")
    return A_TLINK

async def a_fin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = context.user_data
    save_offer(d['n_name'], d['n_st'], d['n_ex'], d['n_pr'], d['n_step'], d['n_term'], d['n_cl'], update.message.text)
    await update.message.reply_text("✅ MongoDB में सेव हो गया!", reply_markup=admin_kb())
    return ConversationHandler.END

# --- CALLBACKS ---
async def global_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    d = q.data
    if d == 'home': await q.edit_message_text("मुख्य मेनू:", reply_markup=user_kb(q.from_user.id))
    elif d == 'u_offers': await u_offers(update, context)
    elif d.startswith('u_det_'): await u_det(update, context)
    elif d == 'a_panel': await q.edit_message_text("🛠 एडमिन पैनल:", reply_markup=admin_kb())
    elif d == 'a_del':
        offers = get_all_offers()
        btns = [[InlineKeyboardButton(o['name'], callback_data=f"del_{o['id']}")] for o in offers]
        btns.append([InlineKeyboardButton("🔙 Back", callback_data='a_panel')])
        await q.edit_message_text("🗑 डिलीट करें:", reply_markup=InlineKeyboardMarkup(btns))
    elif d.startswith('del_'):
        delete_offer_by_id(d.split('_')[1])
        await q.answer("✅ डिलीटेड!")
        await q.edit_message_text("🛠 एडमिन पैनल:", reply_markup=admin_kb())
    elif d == 'a_status':
        offers = get_all_offers()
        btns = [[InlineKeyboardButton(f"{o['name']} ({o['status']})", callback_data=f"stch_{o['id']}")] for o in offers]
        btns.append([InlineKeyboardButton("🔙 Back", callback_data='a_panel')])
        await q.edit_message_text("🔄 स्टेटस बदलें:", reply_markup=InlineKeyboardMarkup(btns))
    elif d.startswith('stch_'):
        oid = d.split('_')[1]
        o = get_offer_by_id(oid)
        new_st = "Pause" if o['status'] == "Active" else "Active"
        offers_col.update_one({"id": oid}, {"$set": {"status": new_st}})
        await q.answer(f"Status: {new_st}")
        await q.edit_message_text("🛠 एडमिन पैनल:", reply_markup=admin_kb())

def run_srv():
    p = int(os.environ.get("PORT", 8080))
    with socketserver.TCPServer(("", p), http.server.SimpleHTTPRequestHandler) as h: h.serve_forever()

if __name__ == '__main__':
    init_db()
    Thread(target=run_srv, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(a_add_start, pattern='^a_add$')],
        states={A_NAME:[MessageHandler(filters.TEXT, a_name)], A_STATUS:[MessageHandler(filters.TEXT, a_status_in)], A_EXPIRY:[MessageHandler(filters.TEXT, a_exp)], A_PRIZE:[MessageHandler(filters.TEXT, a_prz)], A_STEPS:[MessageHandler(filters.TEXT, a_stp)], A_TERMS:[MessageHandler(filters.TEXT, a_trm)], A_CLINK:[MessageHandler(filters.TEXT, a_cli)], A_TLINK:[MessageHandler(filters.TEXT, a_fin)]},
        fallbacks=[CommandHandler("start", start)]
    ))
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(global_cb))
    app.run_polling()
