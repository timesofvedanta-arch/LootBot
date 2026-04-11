import os
import re
import logging
from datetime import datetime

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, Message
from telebot.formatting import escape_markdown

import pymongo
from pymongo import MongoClient

from flask import Flask
from threading import Thread
import time

# --- CONFIGURATION (पूरी तरह आपकी जानकारी के अनुसार) ---
BOT_TOKEN = "8797754610:AAHM-KFFsdNoBJa2VIfrew5uFvgwGvyL-uI"
MONGO_URI = "mongodb+srv://timesofvedanta:Mk626425@lootbot.ypsol8i.mongodb.net/?appName=Lootbot"
WEBAPP_URL = "https://lootbot-1.onrender.com" 
ADMIN_ID = 1216607288

PORT = int(os.environ.get("PORT", 10000))

# --- DB SETUP ---
client = MongoClient(MONGO_URI)
db = client["lootbot"]
users = db["users"]
offers = db["offers"]
proofs = db["proofs"]

# --- TELEBOT SETUP ---
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="MARKDOWN")

# --- FLASK (for Render port keep‑alive) ---
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ LootBot is running."

def keep_port_alive():
    from waitress import serve
    serve(app, host="0.0.0.0", port=PORT)

Thread(target=keep_port_alive, daemon=True).start()

# --- HELPERS ---
def get_user(user_id):
    usr = users.find_one({"user_id": user_id})
    if not usr:
        usr = {
            "user_id": user_id,
            "first_name": "Unknown",
            "username": None,
            "ref_by": None,
            "balance": 0,
            "tasks": [],
            "created_at": datetime.now()
        }
        users.insert_one(usr)
    return usr

def format_ref_link(user_id):
    return f"https://t.me/YourBotNameBot?start={user_id}"

def is_valid_upi(u):
    # simple UPI: user@upi or user@bank
    return re.match(r"^[a-zA-Z0-9.-_]{2,256}@[a-zA-Z]{2,}$", u)

def new_inline(*btns):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(*[InlineKeyboardButton(*b) for b in btns])
    return kb

# --- START / REFS ---
@bot.message_handler(commands=["start"])
def cmd_start(m: Message):
    user_id = m.from_user.id
    first_name = m.from_user.first_name
    username = m.from_user.username

    cmd = m.text.strip().split()
    referrer = None
    if len(cmd) > 1:
        referrer = int(cmd[1])

    usr = get_user(user_id)
    if usr.get("ref_by") is None and referrer and referrer != user_id:
        users.update_one(
            {"user_id": user_id},
            {"$set": {"ref_by": referrer}}
        )
        # credit referrer
        ref_user = users.find_one({"user_id": referrer})
        if ref_user:
            users.update_one(
                {"user_id": referrer},
                {"$inc": {"balance": 10}}
            )
            try:
                bot.send_message(
                    referrer,
                    "🎉 आपके फ्रेंड ने आपका रेफरल लिंक इस्तेमाल किया! आपका बैलेंस ₹10 बढ़ गया।"
                )
            except:
                pass

    text = (
        f"नमस्ते *{escape_markdown(first_name)}*! 🙏\n\n"
        "आपका अपना *Loot‑type Offers Bot* में स्वागत है!\n\n"
        "✅ आपका रेफरल लिंक:\n"
        f"`{format_ref_link(user_id)}`\n\n"
        "👉 /offerlist — सारे ऑफर देखें\n"
        "👉 /mytask — अपने चल रहे टास्क्स"
    )
    bot.reply_to(m, text, disable_web_page_preview=True)

# --- ADMIN PANEL ---
@bot.message_handler(commands=["admin"])
def cmd_admin(m: Message):
    if m.from_user.id != ADMIN_ID:
        bot.reply_to(m, "⚠ यह कमांड सिर्फ ADMIN के लिए है।")
        return

    text = "Admin Panel 🛠\n\n"
    text += "/addoffer — नया ऑफर जोड़ें\n"
    text += "/deloffer — ऑफर हटाएँ\n"
    text += "/approve — प्रूफ अप्रूव/रिजेक्ट करें\n"
    text += "/stats — स्टेट्स देखें"

    bot.reply_to(m, text, parse_mode="MARKDOWN")

@bot.message_handler(commands=["addoffer"])
def cmd_addoffer(m: Message):
    if m.from_user.id != ADMIN_ID:
        bot.reply_to(m, "⚠ यह कमांड सिर्फ ADMIN के लिए है।")
        return

    def ask_name_step(msg: Message):
        name = msg.text.strip()
        if not name:
            bot.reply_to(msg, "⚠ नाम खाली नहीं हो सकता। दोबारा भेजें।")
            return bot.register_next_step_handler(msg, ask_name_step)

        def ask_reward(msg: Message):
            try:
                reward = float(msg.text.strip())
            except:
                bot.reply_to(msg, "⚠ पुरस्कार संख्या में दें, जैसे 10.0")
                return bot.register_next_step_handler(msg, ask_reward)

            def ask_url(msg: Message):
                url = msg.text.strip()
                if not url.startswith("http"):
                    bot.reply_to(msg, "⚠ वैलिड URL दें (https://...)")
                    return bot.register_next_step_handler(msg, ask_url)

                oid = str(offers.count_documents({}) + 1)
                offer = {
                    "oid": oid,
                    "name": name,
                    "reward": reward,
                    "url": url,
                    "created_at": datetime.now()
                }
                offers.insert_one(offer)

                bot.reply_to(msg, f"✅ ऑफर {oid} बनाया गया:\n"
                                  f"नाम: *{escape_markdown(name)}*\n"
                                  f"पुरस्कार: ₹{reward}")
            bot.send_message(msg.chat.id, "अब ऑफर URL दें (WebApp/Ticket URL):")
            bot.register_next_step_handler(msg, ask_url)
        bot.send_message(msg.chat.id, "ऑफर का पुरस्कार (₹) दें:")
        bot.register_next_step_handler(msg, ask_reward)
    bot.send_message(m.chat.id, "ऑफर का नाम दें:")
    bot.register_next_step_handler(m, ask_name_step)

@bot.message_handler(commands=["deloffer"])
def cmd_deloffer(m: Message):
    if m.from_user.id != ADMIN_ID:
        bot.reply_to(m, "⚠ यह कमांड सिर्फ ADMIN के लिए है।")
        return

    all_offers = list(offers.find({}, {"_id": 0, "oid": 1, "name": 1, "reward": 1}))
    if not all_offers:
        bot.reply_to(m, "⚠ कोई ऑफर नहीं मिला।")
        return

    btns = [
        (f"{o['oid']}: ₹{o['reward']}", f"deloffer_{o['oid']}")
        for o in all_offers
    ]
    kb = new_inline(*btns)
    bot.reply_to(m, "हटाने के लिए ऑफर चुनें:", reply_markup=kb)

@bot.callback_query_handler(func=lambda q: q.data.startswith("deloffer_"))
def cb_deloffer(q):
    if q.from_user.id != ADMIN_ID:
        bot.answer_callback_query(q.id, "केवल ADMIN!")
        return

    oid = q.data.split("_")[1]
    offers.delete_one({"oid": oid})
    bot.edit_message_text(
        f"🗑 ऑफर {oid} हटा दिया गया।",
        chat_id=q.message.chat.id,
        message_id=q.message.id
    )

# --- OFFER LIST / MY TASK ---
@bot.message_handler(commands=["offerlist"])
def cmd_offerlist(m: Message):
    user_id = m.from_user.id
    user = get_user(user_id)

    all_offers = list(offers.find({}, {"_id": 0, "oid": 1, "name": 1, "reward": 1}))
    if not all_offers:
        bot.reply_to(m, "⚠ फिलहाल कोई ऑफर नहीं है।")
        return

    lines = []
    for of in all_offers:
        in_task = bool(next((t for t in user["tasks"] if t["offer_oid"] == of["oid"]), None))
        status = "✅" if in_task else "➕"
        lines.append(
            f"{status} `{of['oid']}` *{escape_markdown(of['name'])}* — ₹{of['reward']}"
        )

    text = (
        "*📋 ऑफरलिस्ट*\n\n"
        + "\n".join(lines)
        + "\n\n👉 ऑफर पर क्लिक करके अपने 'My Task' में जोड़ें"
    )

    rows = [
        InlineKeyboardButton(
            f"{of['oid']} | ₹{of['reward']}",
            callback_data=f"offer_{of['oid']}"
        )
        for of in all_offers
    ]
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(*rows)

    bot.reply_to(m, text, reply_markup=kb)

@bot.callback_query_handler(func=lambda q: q.data.startswith("offer_"))
def cb_offer_add(q):
    user_id = q.from_user.id
    user = get_user(user_id)

    oid = q.data.split("_")[1]
    offer = offers.find_one({"oid": oid})
    if not offer:
        bot.answer_callback_query(q.id, "ऑफर नहीं मिला।")
        return

    if any(t["offer_oid"] == oid for t in user["tasks"]):
        bot.answer_callback_query(q.id, "अलरेडी 'My Task' में है।")
        return

    users.update_one(
        {"user_id": user_id},
        {"$push": {"tasks": {
            "offer_oid": oid,
            "status": "pending",
            "updated_at": datetime.now()
        }}}
    )

    # WebApp Claim Button
    wb = InlineKeyboardButton(
        "✅ प्रॉमिस करें और दावा करें",
        web_app=WebAppInfo(url=f"{WEBAPP_URL}/claim?offer={oid}&user={user_id}")
    )
    track = InlineKeyboardButton(
        "📸 Track/Track URL",
        callback_data=f"track_{oid}"
    )
    kb = InlineKeyboardMarkup()
    kb.row(wb)
    kb.row(track)

    bot.edit_message_text(
        f"✅ ऑफर `{oid}` आपके *My Task* में जोड़ दिया गया है!\n"
        "अब आप इस ऑफर के लिए टास्क पूरा कर सकते हैं।",
        chat_id=q.message.chat.id,
        message_id=q.message.id,
        reply_markup=kb
    )

@bot.message_handler(commands=["mytask"])
def cmd_mytask(m: Message):
    user_id = m.from_user.id
    user = get_user(user_id)

    if not user["tasks"]:
        bot.reply_to(m, "⚠ आपके 'My Task' में कोई ऑफर नहीं है।")
        return

    text = "*📋 My Task*\n\n"
    inline = InlineKeyboardMarkup(row_width=1)
    for task in user["tasks"]:
        offer = offers.find_one({"oid": task["offer_oid"]})
        if not offer:
            continue
        status = "🟢 पेंडिंग" if task["status"] == "pending" else "✅ CLAIMED"
        text += f"*{offer['name']}* — ₹{offer['reward']} — {status}\n"

        btn_text = f"📷 {offer['name']}"
        inline.row(
            InlineKeyboardButton(
                btn_text,
                callback_data=f"proof_{offer['oid']}"
            )
        )

    bot.reply_to(m, text, reply_markup=inline)

# --- TRACK / SCREENSHOT (Playwright Placeholder) ---
@bot.callback_query_handler(func=lambda q: q.data.startswith("track_"))
def cb_track(q):
    bot.send_message(
        q.message.chat.id,
        "🖼 ट्रैकिंग URL का स्क्रीनशॉट लिया जा रहा है...\n"
        "Playwright sync mode से full‑page स्क्रीनशॉट लेकर यहाँ भेजा जाएगा।"
    )

# --- PROOF SUBMISSION ---
@bot.callback_query_handler(func=lambda q: q.data.startswith("proof_"))
def cb_proof_ask(q):
    oid = q.data.split("_")[1]
    offer = offers.find_one({"oid": oid})
    if not offer:
        bot.answer_callback_query(q.id, "ऑफर नहीं मिला।")
        return

    text = (
        f"📸 *{offer['name']}* के लिए प्रूफ भेजें।\n\n"
        "✅ शर्तें:\n"
        "1. अच्छी क्वालिटी की फोटो/स्क्रीनशॉट\n"
        "2. साफ़ दिखने वाला ट्रैफ़िक/टास्क आइडी\n"
        "3. अब आप अपना UPI ID भेजें (उदाहरण: user@upi)"
    )

    bot.edit_message_text(text, chat_id=q.message.chat.id, message_id=q.message.id)

# पोलिंग शुरू
bot.infinity_polling()
