from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is Link!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()


import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# अपनी फाइलों से इम्पोर्ट करें
from config import API_TOKEN, ADMIN_ID
import database as db
import keyboards as kb

# Logging (ताकि रेंडर के लॉग्स में एरर दिखे)
logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- STATES ---
class OfferStates(StatesGroup):
    name = State()
    days = State()
    icon = State()
    details = State()
    price = State()
    claim = State()
    track = State()

# --- START COMMAND ---
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear() # पुराना कचरा साफ़ करें
    if message.from_user.id == ADMIN_ID:
        await message.answer("नमस्ते एडमिन! आपका पैनल लोड हो गया है।", reply_markup=kb.admin_menu())
    else:
        await message.answer("X-Income बॉट में आपका स्वागत है!", reply_markup=kb.user_menu())

# --- ADD OFFER INITIATE ---
@dp.message(F.text == "add new offer")
async def start_add(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("1. ऑफर का **नाम** लिखें:", reply_markup=kb.get_skip_btn())
    await state.set_state(OfferStates.name)

# --- FSM HANDLERS (MESSAGE) ---
@dp.message(OfferStates.name)
async def st_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("2. कितने **दिन** चलेगा? (सिर्फ नंबर):", reply_markup=kb.get_skip_btn())
    await state.set_state(OfferStates.days)

@dp.message(OfferStates.days)
async def st_days(message: types.Message, state: FSMContext):
    val = message.text if message.text.isdigit() else "0"
    await state.update_data(days=val)
    await message.answer("3. **आइकॉन लिंक** (URL) दें:", reply_markup=kb.get_skip_btn())
    await state.set_state(OfferStates.icon)

@dp.message(OfferStates.icon)
async def st_icon(message: types.Message, state: FSMContext):
    url = message.text if message.text.startswith("http") else "N/A"
    await state.update_data(icon=url)
    await message.answer("4. ऑफर की **डिटेल्स** लिखें:", reply_markup=kb.get_skip_btn())
    await state.set_state(OfferStates.details)

@dp.message(OfferStates.details)
async def st_details(message: types.Message, state: FSMContext):
    await state.update_data(details=message.text)
    await message.answer("5. ऑफर का **प्राइज** (Amount) लिखें:", reply_markup=kb.get_skip_btn())
    await state.set_state(OfferStates.price)

@dp.message(OfferStates.price)
async def st_price(message: types.Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("6. **क्लेम लिंक** (URL) दें:", reply_markup=kb.get_skip_btn())
    await state.set_state(OfferStates.claim)

@dp.message(OfferStates.claim)
async def st_claim(message: types.Message, state: FSMContext):
    await state.update_data(claim=message.text)
    await message.answer("7. **ट्रैकिंग लिंक** (URL) दें:", reply_markup=kb.get_skip_btn())
    await state.set_state(OfferStates.track)

@dp.message(OfferStates.track)
async def st_final(message: types.Message, state: FSMContext):
    await state.update_data(track=message.text)
    data = await state.get_data()
    db.add_offer_db(data)
    await state.clear()
    await message.answer("✅ ऑफर सफलतापूर्वक जुड़ गया है!", reply_markup=kb.admin_menu())

# --- SKIP BUTTON LOGIC (ALL STATES) ---
@dp.callback_query(F.data == "skip_step")
async def skip_callback(call: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    
    if current_state == OfferStates.name:
        await state.update_data(name="No Name")
        await state.set_state(OfferStates.days)
        await call.message.answer("नाम स्किप हुआ। कितने **दिन**? (नंबर):", reply_markup=kb.get_skip_btn())
    
    elif current_state == OfferStates.days:
        await state.update_data(days="0")
        await state.set_state(OfferStates.icon)
        await call.message.answer("दिन स्किप हुए। **आइकॉन लिंक** दें:", reply_markup=kb.get_skip_btn())
    
    elif current_state == OfferStates.icon:
        await state.update_data(icon="N/A")
        await state.set_state(OfferStates.details)
        await call.message.answer("लिंक स्किप हुआ। **डिटेल्स** लिखें:", reply_markup=kb.get_skip_btn())
        
    elif current_state == OfferStates.details:
        await state.update_data(details="N/A")
        await state.set_state(OfferStates.price)
        await call.message.answer("डिटेल्स स्किप हुईं। **प्राइज** लिखें:", reply_markup=kb.get_skip_btn())

    elif current_state == OfferStates.price:
        await state.update_data(price="0")
        await state.set_state(OfferStates.claim)
        await call.message.answer("प्राइज स्किप हुआ। **क्लेम लिंक** दें:", reply_markup=kb.get_skip_btn())

    elif current_state == OfferStates.claim:
        await state.update_data(claim="#")
        await state.set_state(OfferStates.track)
        await call.message.answer("क्लेम लिंक स्किप हुआ। **ट्रैकिंग लिंक** दें:", reply_markup=kb.get_skip_btn())

    elif current_state == OfferStates.track:
        await state.update_data(track="#")
        data = await state.get_data()
        db.add_offer_db(data)
        await state.clear()
        await call.message.answer("✅ ऑफर सेव हो गया (डेटा स्किप किया गया)।", reply_markup=kb.admin_menu())

    await call.answer() # बटन का लोडिंग आइकॉन बंद करने के लिए

# --- BOT RUN ---
async def main():
    db.init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
