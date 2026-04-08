from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram import types

def get_skip_btn():
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="⏩ Skip Step", callback_data="skip_step"))
    return builder.as_markup()

def admin_menu():
    builder = ReplyKeyboardBuilder()
    btns = ['add new offer', 'offer list', 'user data', 'edit offer']
    for b in btns: builder.add(types.KeyboardButton(text=b))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def user_menu():
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="view offers"), types.KeyboardButton(text="My Referrals"))
    return builder.as_markup(resize_keyboard=True)

def report_action_btns(sub_id):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ Approve", callback_data=f"app_{sub_id}"),
                types.InlineKeyboardButton(text="❌ Reject", callback_data=f"rej_{sub_id}"))
    builder.row(types.InlineKeyboardButton(text="🏠 Back to List", callback_data="user_data_back"))
    return builder.as_markup()
