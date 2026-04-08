import asyncio
import os
import logging
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, F, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# आपकी फाइलों से डेटा
from config import API_TOKEN, ADMIN_ID
import database as db
import keyboards as kb

# --- RENDER PORT FIX (Flask) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

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

# ================= CALLBACK HANDLERS (बटन के लिए) =================

@dp.callback_query(F.data == "skip_step")
async def skip_handler(call: types.CallbackQuery, state: FSMContext):
    current = await state.get_state()
    await call.answer() # बटन का घूमना तुरंत बंद करेगा

    if current == OfferStates.name:
        await state.update_data(name="N/A")
        await state.set_state(OfferStates.days)
        await call.message.answer("नाम स्किप हुआ।\n2. कितने **दिन**? (नंबर):", reply_markup=kb.get_skip_btn())
    
    elif current == OfferStates.days:
        await state.update_data(days="0")
        await state.set_state(OfferStates.icon)
        await call.message.answer("दिन स्किप हुए।\n3. **आइकॉन लिंक** दें:", reply_markup=kb.get_skip_btn())
    
    elif current == OfferStates.icon:
        await state.update_data(icon="N/A")
        await state.set_state(OfferStates.details)
        await call.message.answer("लिंक स्किप हुआ।\n4. **डिटेल्स** लिखें:", reply_markup=kb.get_skip_btn())
    
    elif current == OfferStates.details:
        await state.update_data(details="N/A")
        await state.set_state(OfferStates.price)
        await call.message.answer("डिटेल्स स्किप।\n5. **प्राइज** लिखें:", reply_markup=kb.get_skip_btn())

    elif current == OfferStates.price:
        await state.update_data(price="0")
        await state.set_state(OfferStates.claim)
        await call.message.answer("प्राइज स्किप।\n6. **क्लेम लिंक** दें:", reply_markup=kb.get_skip_btn())

    elif current == OfferStates.claim:
        await state.update_data(claim="#")
        await state.set_state(OfferStates.track)
        await call.message.answer("क्लेम लिंक स्किप।\n7. **ट्रैकिंग लिंक** दें:", reply_markup=kb.get_skip_btn())

    elif current == OfferStates.track:
        await state.update_data(track="#")
        data = await state.get_data()
        db.add_offer_db(data)
        await state.clear()
        await call.message.answer("✅ ऑफर सेव हो गया (डेटा स्किप किया गया)।", reply_markup=kb.admin_menu())

# ================= MESSAGE HANDLERS =================

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    if message.from_user.id == ADMIN_ID:
        await message.answer("✅ एडमिन पैनल सक्रिय है।", reply_markup=kb.admin_menu())
    else:
        await message.answer("X-Income बॉट में आपका स्वागत है!", reply_markup=kb.user_menu())

@dp.message(F.text == "add new offer")
async def start_add(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.clear() # पुराना कोई भी स्टेट साफ करें
    await state.set_state(OfferStates.name)
    await message.answer("1. ऑफर का **नाम** लिखें:", reply_markup=kb.get_skip_btn())

@dp.message(OfferStates.name)
async def st_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(OfferStates.days)
    await message.answer("2. कितने **दिन**? (नंबर):", reply_markup=kb.get_skip_btn())

@dp.message(OfferStates.days)
async def st_days(message: types.Message, state: FSMContext):
    await state.update_data(days=message.text if message.text.isdigit() else "0")
    await state.set_state(OfferStates.icon)
    await message.answer("3. **आइकॉन लिंक** दें:", reply_markup=kb.get_skip_btn())

# --- (बाकी के मैसेज हैंडलर icon, details, price इसी तरह चालू रहेंगे) ---

async def main():
    Thread(target=run_flask).start()
    db.init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
