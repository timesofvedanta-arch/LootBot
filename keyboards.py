from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram import types

def admin_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="add new offer"), types.KeyboardButton(text="offer list"))
    builder.row(types.KeyboardButton(text="user data"), types.KeyboardButton(text="edit offer"))
    return builder.as_markup(resize_keyboard=True)

def user_menu():
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="view offers"))
    return builder.as_markup(resize_keyboard=True)

def get_skip_btn():
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="⏩ Skip Step", callback_data="skip_step"))
    return builder.as_markup()
