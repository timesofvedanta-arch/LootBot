import sqlite3
from aiogram import types
import keyboards as kb

def get_pending_reports():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_name, offer_name, amount FROM submissions WHERE status = 'pending'")
    data = cursor.fetchall()
    conn.close()
    return data

async def show_reports(message: types.Message):
    reports = get_pending_reports()
    if not reports:
        await message.answer("📭 कोई पेंडिंग रिपोर्ट नहीं है।")
        return
    builder = InlineKeyboardBuilder()
    for r in reports:
        builder.row(types.InlineKeyboardButton(text=f"👤 {r[1]} | {r[2]} | ₹{r[3]}", callback_data=f"view_sub_{r[0]}"))
    await message.answer("📋 पेंडिंग यूजर डेटा:", reply_markup=builder.as_markup())
