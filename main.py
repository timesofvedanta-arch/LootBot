from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
import psycopg2
import os
import telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ---------------------
# CONFIG
# ---------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
DATABASE_URL = os.getenv("DATABASE_URL")

# ---------------------
# DATABASE CONNECTION
# ---------------------
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# ---------------------
# FASTAPI
# ---------------------
app = FastAPI()

# ---------------------
# TELEGRAM BOT
# ---------------------
bot_app = Application.builder().token(BOT_TOKEN).build()

# ---------------------
# DATABASE TABLES
# ---------------------
cur.execute("""CREATE TABLE IF NOT EXISTS users (
id SERIAL PRIMARY KEY, telegram_id BIGINT UNIQUE, balance INT DEFAULT 0, referred_by BIGINT
)""")
cur.execute("""CREATE TABLE IF NOT EXISTS offers (
id SERIAL PRIMARY KEY, title TEXT, reward INT
)""")
cur.execute("""CREATE TABLE IF NOT EXISTS withdrawals (
id SERIAL PRIMARY KEY, user_id INT, amount INT, status TEXT DEFAULT 'pending'
)""")
conn.commit()

# ---------------------
# TELEGRAM HANDLERS
# ---------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    args = context.args
    ref = int(args[0]) if args else None

    cur.execute("SELECT * FROM users WHERE telegram_id=%s", (user_id,))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO users (telegram_id, referred_by) VALUES (%s, %s)", (user_id, ref))
        conn.commit()

    link = f"https://t.me/YOUR_BOT?start={user_id}"
    await update.message.reply_text(f"Welcome! Your referral link:\n{link}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    if "@upi" in text:
        await update.message.reply_text("✅ UPI received! (Demo)")

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT, handle_message))

# ---------------------
# WEBHOOK
# ---------------------
@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return {"ok": True}

# ---------------------
# ADMIN DASHBOARD
# ---------------------
@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    return """
    <h2>Login</h2>
    <form action='/login' method='post'>
    <input name='user' placeholder='Username'><br>
    <input name='pass' type='password' placeholder='Password'><br>
    <button>Login</button>
    </form>
    """

@app.post("/login")
def login(user: str = Form(...), password: str = Form(...)):
    if user == "admin" and password == "demo":
        return RedirectResponse("/dashboard", status_code=302)
    return {"error":"wrong"}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    cur.execute("SELECT * FROM offers")
    offers = cur.fetchall()
    cur.execute("SELECT * FROM withdrawals")
    withdrawals = cur.fetchall()

    html = "<h2>Dashboard</h2>"
    html += "<h3>Users</h3>"
    for u in users:
        html += f"User {u[1]} | Balance ₹{u[2]} | Referred by {u[3]}<br>"

    html += "<h3>Offers</h3>"
    for o in offers:
        html += f"{o[1]} | Reward ₹{o[2]} <a href='/delete_offer/{o[0]}'>Delete</a><br>"

    html += "<h3>Add Offer</h3>"
    html += """
    <form action='/add_offer' method='post'>
    <input name='title' placeholder='Title'><br>
    <input name='reward' placeholder='Reward'><br>
    <button>Add</button>
    </form>
    """

    html += "<h3>Withdrawals</h3>"
    for w in withdrawals:
        html += f"User {w[1]} | Amount ₹{w[2]} | Status {w[3]}<br>"

    return html

@app.post("/add_offer")
def add_offer(title: str = Form(...), reward: int = Form(...)):
    cur.execute("INSERT INTO offers (title, reward) VALUES (%s, %s)", (title, reward))
    conn.commit()
    return RedirectResponse("/dashboard", status_code=302)

@app.get("/delete_offer/{id}")
def delete_offer(id: int):
    cur.execute("DELETE FROM offers WHERE id=%s", (id,))
    conn.commit()
    return RedirectResponse("/dashboard", status_code=302)
