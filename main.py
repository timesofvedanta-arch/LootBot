import asyncio
import logging
import os
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, F, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# अपनी फाइलों से इम्पोर्ट
from config import API_TOKEN, ADMIN_ID
import database as db
import keyboards as kb

# --- KEEP ALIVE SERVER (For Render) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Running!"

def run_flask():
    # Render hamesha PORT variable deta hai
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- BOT SETUP ---
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class OfferStates(StatesGroup):
    name = State()
    days = State()
    icon = State()
    details = State()
    price = State()
    claim = State()
    track = State()

# --- HANDLERS ---
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    if message.from_user.id == ADMIN_ID:
        await message.answer("नमस्ते एडमिन!", reply_markup=kb.admin_menu())
    else:
        await message.answer("X-Income बॉट में स्वागत है!", reply_markup=kb.user_menu())

@dp.message(F.text == "add new offer")
async def start_add(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("1. ऑफर का नाम लिखें:", reply_markup=kb.get_skip_btn())
    await state.set_state(OfferStates.name)

# --- FSM (Shortened for brevity but keep your logic) ---
@dp.message(OfferStates.name)
async def st_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("2. कितने दिन? (नंबर):", reply_markup=kb.get_skip_btn())
    await state.set_state(OfferStates.days)

@dp.message(OfferStates.days)
async def st_days(message: types.Message, state: FSMContext):
    await state.update_data(days=message.text if message.text.isdigit() else "0")
    await message.answer("3. आइकॉन लिंक दें:", reply_markup=kb.get_skip_btn())
    await state.set_state(OfferStates.icon)

# --- SKIP HANDLER ---
@dp.callback_query(F.data == "skip_step")
async def skip_callback(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("स्टेप स्किप हुआ। कृपया अगला विवरण लिखें।")
    await call.answer()

# --- RUN BOT ---
async def start_bot():
    # Flask server shuru karein taaki Render Timeout na de
    keep_alive()
    db.init_db()
    print("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except (KeyboardInterrupt, SystemExit):
        print("Bot Stopped")
