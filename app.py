import os, logging, sqlite3, http.server, socketserver
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, 
    CallbackQueryHandler, MessageHandler, filters, ConversationHandler
)

# --- CONFIGURATION ---
ADMIN_ID = 1216607288  # <--- अपनी ID यहाँ डालें
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DB_NAME = "timesofvedanta.db"

# States
(A_NAME, A_STATUS, A_EXPIRY, A_PRIZE, A_STEPS, A_TERMS, A_CLINK, A_TLINK, 
 U_SEL_OFF, U_SCREEN, U_UPI, E_SEL, E_VAL) = range(13)

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

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
    db_query('''CREATE TABLE IF NOT EXISTS offers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, status TEXT, expiry TEXT, prize TEXT, steps TEXT, terms TEXT, claim_link TEXT, track_link TEXT)''')
    db_query('''CREATE TABLE IF NOT EXISTS submissions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, offer_name TEXT, upi TEXT, photo_id TEXT, status TEXT DEFAULT 'Pending')''')
    db_query('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, upi_id TEXT)''')

# --- KEYBOARDS ---
def user_kb(uid):
    btns = [[InlineKeyboardButton("🔥 Offer List", callback_data='u_offers')],
            [InlineKeyboardButton("📤 Submit Proof", callback_data='u_sub_start'),
             InlineKeyboardButton("📱 Contact Us", url="https://wa.me/YOUR_NUMBER")]]
    if uid == ADMIN_ID: btns.append([InlineKeyboardButton("🛠 Admin Panel", callback_data='a_panel')])
    return InlineKeyboardMarkup(btns)

def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add", callback_data='a_add'), InlineKeyboardButton("🗑 Delete", callback_data='a_del')],
        [InlineKeyboardButton("🔄 Status", callback_data='a_status'), InlineKeyboardButton("👥 User Proofs", callback_data='a_proofs')],
        [InlineKeyboardButton("📜 Offer List", callback_data='u_offers'), InlineKeyboardButton("🔙 Back", callback_data='home')]
    ])

# --- START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    db_query("INSERT OR IGNORE INTO users (id) VALUES (?)", (uid,))
    await update.message.reply_text("🚀 **TIMESOFVEDANTA** सक्रिय है!", reply_markup=user_kb(uid), parse_mode='Markdown')

# --- USER: OFFERS & PROOF ---
async def u_offers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    offers = db_query("SELECT id, name, status, expiry, prize FROM offers", fetch=True)
    if not offers:
        await query.edit_message_text("❌ अभी कोई एक्टिव ऑफर नहीं है।", reply_markup=user_kb(query.from_user.id))
        return
    btns = []
    for o in offers:
        tag = "🟢 Active" if o[2] == 'Active' else "🟡 Pause"
        btns.append([InlineKeyboardButton(f"{o[1]} | {tag} | ₹{o[4]}", callback_data=f'u_det_{o[0]}')])
    btns.append([InlineKeyboardButton("🔙 Back", callback_data='home')])
    await query.edit_message_text("🎁 **ऑफर लिस्ट:**", reply_markup=InlineKeyboardMarkup(btns))

async def u_det(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    oid = query.data.split('_')[2]
    o = db_query("SELECT name, status, prize, steps, terms, claim_link, track_link FROM offers WHERE id=?", (oid,), fetch=True)[0]
    txt = f"📌 **{o[0]}**\n💰 Prize: ₹{o[2]}\nStatus: {o[1]}\n\n📝 **Steps:**\n{o[3]}\n\n⚠️ **Terms:**\n{o[4]}"
    btns = [[InlineKeyboardButton("🚀 Claim", web_app=WebAppInfo(url=o[5])), InlineKeyboardButton("📍 Track", web_app=WebAppInfo(url=o[6]))],
            [InlineKeyboardButton("🔙 Back", callback_data='u_offers')]]
    await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')

# --- SUBMIT PROOF FLOW ---
async def u_sub_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    offers = db_query("SELECT name FROM offers WHERE status='Active'", fetch=True)
    if not offers:
        await update.callback_query.answer("कोई एक्टिव ऑफर नहीं है!", show_alert=True)
        return ConversationHandler.END
    btns = [[InlineKeyboardButton(o[0], callback_data=f'sub_{o[0]}')] for o in offers]
    await update.callback_query.edit_message_text("✅ ऑफर चुनें जिसका प्रूफ देना है:", reply_markup=InlineKeyboardMarkup(btns))
    return U_SEL_OFF

async def u_sub_sel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['sub_off'] = update.callback_query.data.split('_')[1]
    await update.callback_query.edit_message_text("📸 अब स्क्रीनशॉट अपलोड करें:")
    return U_SCREEN

async def u_sub_screen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['sub_img'] = update.message.photo[-1].file_id
    await update.message.reply_text("💳 अपनी UPI ID भेजें:")
    return U_UPI

async def u_sub_upi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upi = update.message.text
    uid = update.effective_user.id
    db_query("INSERT INTO submissions (user_id, offer_name, upi, photo_id) VALUES (?,?,?,?)", 
             (uid, context.user_data['sub_off'], upi, context.user_data['sub_img']))
    await update.message.reply_text("✅ सबमिट हो गया! टीम रिव्यु करेगी।", reply_markup=user_kb(uid))
    return ConversationHandler.END

# --- ADMIN: ADD OFFER FLOW ---
async def a_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("1️⃣ नाम:")
    return A_NAME

async def a_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['n_name'] = update.message.text
    await update.message.reply_text("2️⃣ स्टेटस (Active/Pause):")
    return A_STATUS

async def a_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['n_st'] = update.message.text
    await update.message.reply_text("3️⃣ एक्सपायरी:")
    return A_EXPIRY

async def a_exp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['n_ex'] = update.message.text
    await update.message.reply_text("4️⃣ प्राइज (₹):")
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
    db_query("INSERT INTO offers (name,status,expiry,prize,steps,terms,claim_link,track_link) VALUES (?,?,?,?,?,?,?,?)",
             (d['n_name'],d['n_st'],d['n_ex'],d['n_pr'],d['n_step'],d['n_term'],d['n_cl'],update.message.text))
    await update.message.reply_text("✅ ऑफर जुड़ गया!", reply_markup=admin_kb())
    return ConversationHandler.END

# --- ADMIN: PROOF REVIEW ---
async def a_proofs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subs = db_query("SELECT id, user_id, offer_name, upi, photo_id FROM submissions WHERE status='Pending'", fetch=True)
    if not subs:
        await update.callback_query.edit_message_text("कोई पेंडिंग प्रूफ नहीं है।", reply_markup=admin_kb())
        return
    for s in subs:
        btns = [[InlineKeyboardButton("✅ Approve", callback_data=f'apr_{s[0]}_{s[1]}'),
                 InlineKeyboardButton("❌ Reject", callback_data=f'rej_{s[0]}_{s[1]}')]]
        await update.callback_query.message.reply_photo(s[4], caption=f"User: {s[1]}\nOffer: {s[2]}\nUPI: {s[3]}", reply_markup=InlineKeyboardMarkup(btns))

# --- HANDLER ROUTER ---
async def global_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    d = q.data
    uid = q.from_user.id
    if d == 'home': await q.edit_message_text("मुख्य मेनू:", reply_markup=user_kb(uid))
    elif d == 'u_offers': await u_offers(update, context)
    elif d.startswith('u_det_'): await u_det(update, context)
    elif d == 'a_panel': await q.edit_message_text("🛠 एडमिन पैनल:", reply_markup=admin_kb())
    elif d == 'a_proofs': await a_proofs(update, context)
    elif d.startswith('apr_'):
        sid, usr = d.split('_')[1], d.split('_')[2]
        db_query("UPDATE submissions SET status='Approved' WHERE id=?", (sid,))
        await context.bot.send_message(usr, "✅ आपका पेमेंट भेज दिया गया है!")
        await q.delete_message()
    elif d.startswith('rej_'):
        sid, usr = d.split('_')[1], d.split('_')[2]
        db_query("UPDATE submissions SET status='Rejected' WHERE id=?", (sid,))
        await context.bot.send_message(usr, "❌ आपने स्टेप्स फॉलो नहीं किए, इसलिए रिजेक्ट हो गया।")
        await q.delete_message()

# --- SERVER ---
def run_srv():
    p = int(os.environ.get("PORT", 8080))
    with socketserver.TCPServer(("", p), http.server.SimpleHTTPRequestHandler) as h: h.serve_forever()

if __name__ == '__main__':
    init_db()
    Thread(target=run_srv, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Conversations
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(a_add_start, pattern='^a_add$')],
        states={A_NAME:[MessageHandler(filters.TEXT, a_name)], A_STATUS:[MessageHandler(filters.TEXT, a_status)], A_EXPIRY:[MessageHandler(filters.TEXT, a_exp)], A_PRIZE:[MessageHandler(filters.TEXT, a_prz)], A_STEPS:[MessageHandler(filters.TEXT, a_stp)], A_TERMS:[MessageHandler(filters.TEXT, a_trm)], A_CLINK:[MessageHandler(filters.TEXT, a_cli)], A_TLINK:[MessageHandler(filters.TEXT, a_fin)]},
        fallbacks=[CommandHandler("start", start)]
    ))
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(u_sub_start, pattern='^u_sub_start$')],
        states={U_SEL_OFF:[CallbackQueryHandler(u_sub_sel, pattern='^sub_')], U_SCREEN:[MessageHandler(filters.PHOTO, u_sub_screen)], U_UPI:[MessageHandler(filters.TEXT, u_sub_upi)]},
        fallbacks=[CommandHandler("start", start)]
    ))
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(global_cb))
    app.run_polling(drop_pending_updates=True)
