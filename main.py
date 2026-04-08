import asyncio
import os
import logging
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, F, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from config import API_TOKEN, ADMIN_ID
import database as db
import keyboards as kb

# Keep Alive for Render
app = Flask('')
@app.route('/')
def home(): return "Bot is Online"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class OfferStates(StatesGroup):
    name, days, icon, details, price, claim, track = State(), State(), State(), State(), State(), State(), State()

# --- ADMIN PANEL BUTTONS ---

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    if message.from_user.id == ADMIN_ID:
        await message.answer("✅ एडमिन पैनल लोड हो गया।", reply_markup=kb.admin_menu())
    else:
        await message.answer("नमस्ते! X-Income में आपका स्वागत है।", reply_markup=kb.user_menu())

@dp.message(F.text == "add new offer")
async def start_add(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.set_state(OfferStates.name)
    await message.answer("1. ऑफर का नाम लिखें:", reply_markup=kb.get_skip_btn())

@dp.message(F.text == "offer list")
async def list_offers(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    offers = db.get_all_offers()
    if not offers:
        await message.answer("📭 कोई ऑफर नहीं मिला।")
        return
    res = "📋 **Active Offers:**\n\n"
    for o in offers:
        res += f"🔹 ID: {o[0]} | {o[1]} | ₹{o[8]}\n"
    await message.answer(res)

@dp.message(F.text == "user data")
async def user_reports(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("📊 यूजर रिपोर्ट्स सेक्शन (यहाँ पेंडिंग टास्क दिखेंगे)")

@dp.message(F.text == "edit offer")
async def edit_of(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("✍️ एडिट करने के लिए ऑफर की ID भेजें।")

# --- FSM HANDLERS ---
@dp.message(OfferStates.name)
async def st_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(OfferStates.days)
    await message.answer("2. कितने दिन? (नंबर):", reply_markup=kb.get_skip_btn())

# (इसी तरह बाकी स्टेप्स st_days, st_icon... को main.py में पूरा भरें)

# --- SKIP LOGIC ---
@dp.callback_query(F.data == "skip_step")
async def skip_handler(call: types.CallbackQuery, state: FSMContext):
    await call.answer("स्किप किया गया")
    # अगली स्टेट पर जाने का कोड यहाँ आता है...

async def main():
    Thread(target=run_flask).start()
    db.init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
