from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import os

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Application.builder().token(BOT_TOKEN).build()

users = {}

# /start command
async def start(update: Update, context):
    user_id = str(update.message.from_user.id)
    ref = context.args[0] if context.args else None

    if user_id not in users:
        users[user_id] = {
            "upi": None,
            "balance": 0,
            "ref": ref
        }

    link = f"https://t.me/YOUR_BOT?start={user_id}"

    await update.message.reply_text(
        f"👋 Welcome!\n\n🔗 Your Referral Link:\n{link}\n\nUPI ID भेजो:"
    )

# message handler
async def handle(update: Update, context):
    user_id = str(update.message.from_user.id)
    text = update.message.text

    if "@upi" in text:
        users[user_id]["upi"] = text
        await update.message.reply_text("✅ UPI Saved!")

# admin broadcast
async def broadcast(update: Update, context):
    if update.message.from_user.id != ADMIN_ID:
        return
    
    msg = " ".join(context.args)

    for u in users:
        try:
            await context.bot.send_message(u, msg)
        except:
            pass

bot.add_handler(CommandHandler("start", start))
bot.add_handler(CommandHandler("broadcast", broadcast))
bot.add_handler(MessageHandler(filters.TEXT, handle))


# webhook
@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, bot.bot)
    await bot.process_update(update)
    return {"ok": True}


# admin dashboard (simple)
@app.get("/admin")
def admin(user_id: int = 0):
    if user_id != ADMIN_ID:
        return {"error": "Unauthorized"}
    
    return users


@app.get("/")
def home():
    return {"status": "running"}
