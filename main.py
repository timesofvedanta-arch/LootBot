import asyncio
from aiogram import Bot, Dispatcher, F, types
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from config import API_TOKEN, ADMIN_ID
import database as db
import keyboards as kb
import admin_reports as reports

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class OfferStates(StatesGroup):
    name, days, icon, details, price, claim, track = State(), State(), State(), State(), State(), State(), State()

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("नमस्ते एडमिन!", reply_markup=kb.admin_menu())
    else:
        await message.answer("नमस्ते यूजर!", reply_markup=kb.user_menu())

# --- एडमिन: ऑफर जोड़ना ---
@dp.message(F.text == "add new offer")
async def add_offer(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await message.answer("ऑफर का नाम लिखें:", reply_markup=kb.get_skip_btn())
    await state.set_state(OfferStates.name)

@dp.message(OfferStates.name)
async def st_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("कितने दिन? (सिर्फ नंबर):", reply_markup=kb.get_skip_btn())
    await state.set_state(OfferStates.days)

@dp.message(OfferStates.days)
async def st_days(message: types.Message, state: FSMContext):
    await state.update_data(days=message.text if message.text.isdigit() else "0")
    await message.answer("आइकॉन लिंक (http...):", reply_markup=kb.get_skip_btn())
    await state.set_state(OfferStates.icon)

# --- एडमिन: यूजर डेटा देखना ---
@dp.message(F.text == "user data")
async def check_data(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await reports.show_reports(message)

# --- स्किप लॉजिक ---
@dp.callback_query(F.data == "skip_step")
async def skip(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("स्टेप स्किप हुआ। कृपया अगला विवरण लिखें।")
    await call.answer()

async def start_bot():
    db.init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(start_bot())
