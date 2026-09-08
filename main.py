import os
import re
import random
import asyncio
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, 
    LabeledPrice, PreCheckoutQuery
)
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from telethon import TelegramClient
from telethon.sessions import StringSession

# ================= الإعدادات الأساسية =================
BOT_TOKEN = "8896024185:AAFnycldDpL4OyQ4ebpgvjs1F1hJsrI-eJE"
ADMIN_USERNAME = "aaysam"

# قناة الاشتراك الإجباري
REQUIRED_CHANNEL = "VPP8P"

# 💵 أسعار الأرقام الجديدة
USA_NUMBER_PRICE = 3.00
COLOMBIA_NUMBER_PRICE = 1.00

# قيمة الهدية اليومية والإحالة (سنت واحد)
BONUS_AMOUNT = 0.01

# سعر النجمة الواحدة بالدولار (2 سنت)
STAR_PRICE_USD = 0.02

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class States(StatesGroup):
    waiting_for_stars_count = State()
    waiting_for_transfer_id = State()
    waiting_for_transfer_amount = State()

# ================= إعداد مسار القاعدة الدائم لتجنب فقدان السنتات =================
DB_DIR = "data"
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

DB_PATH = os.path.join(DB_DIR, "telegram_bot.db")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0.0,
    last_bonus TEXT,
    referred_by INTEGER,
    language TEXT DEFAULT 'ar'
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS user_purchases (
    user_id INTEGER,
    number_id TEXT,
    PRIMARY KEY (user_id, number_id)
)
""")
conn.commit()

# ================= مخزن الأرقام الأساسي =================
NUMBERS_STORE = {
    "1": {
        "country": "usa", 
        "name": "🇺🇸 أمريكا (احتيالي)", 
        "price": USA_NUMBER_PRICE, 
        "phone": "+13526419211",
        "session": "1AZWarzYBu5KAcXua9CNUuBPNtCE_7qKjZSrPCW8oTglmRjTeiqir6y6P253w6ckdo01lcaAnL1vNx0OMBxDWoCTGTG7xGWdWUor7J8Tde_bTf2Qqpcf5GFquiqcNFudvsbYm1UdvzIQwaUbByP7rFr3tnF6nlfh56QEr3Xqv9PyKBlXSDYK2hMLfSwy6Gh-F0J5CUerfi6qOArHG2XzPzx5rgN8DNC7yPDIgbQiCmU7XLAniXpYa4CPH0x89aLYRh395cRkm0mbwWyuJQo3wOnulNW-JvPB3ctEMGFkVk9LqIhv3rOKoy0k_qLJZHn6Sn5qgjadwGmicP1rVTMeW8TY5AkXnE_w=",
        "api_id": 34198296, 
        "api_hash": "8b007a14ebc08f01120d0ebs8ba4d595"
    },
    "2": {
        "country": "colombia", 
        "name": "🇨🇴 كولومبيا", 
        "price": COLOMBIA_NUMBER_PRICE, 
        "phone": "+57XXXXXXXXX", # استبدله برقمك الكولومبي الحقيقي لاحقاً
        "session": "ضع_جلسة_كولومبيا_هنا_عندما_تجهزها", # حط سيشن كولومبيا هنا
        "api_id": 1234567, # استبدلها بـ api_id الخاص بكولومبيا
        "api_hash": "your_colombia_api_hash" # استبدلها بـ api_hash الخاص بكولومبيا
    }
}

async def check_subscription(user_id: int) -> bool:
    if not REQUIRED_CHANNEL:
        return True
    try:
        member = await bot.get_chat_member(chat_id=f"@{REQUIRED_CHANNEL}", user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except Exception:
        pass
    return False

def get_user_language(user_id: int) -> str:
    cursor.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 'ar'

def get_main_keyboard(user_id):
    cursor.execute("SELECT balance, language FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    balance = row[0] if row and row[0] is not None else 0.0
    lang = row[1] if row and len(row) > 1 else 'ar'
    
    if lang == 'en':
        text_header = (
            "🤖 **Welcome to the Official Number Store** 🌐\n\n"
            "• Get numbers and receive OTP codes instantly.\n"
            "• Top up your balance via Telegram Stars.\n\n"
            f"🆔 ID: `{user_id}`\n"
            f"💵 Balance: `${balance:.2f}`\n\n"
            "Choose from the menu below 👇"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Buy Numbers Store", callback_data="buy_number_menu")],
            [InlineKeyboardButton(text="⚡ My Account", callback_data="my_account"), InlineKeyboardButton(text="🎁 Daily Bonus ($0.01)", callback_data="claim_bonus")],
            [InlineKeyboardButton(text="💳 Recharge Stars", callback_data="recharge_menu")],
            [InlineKeyboardButton(text="🤝 Ref Link ($0.01)", callback_data="ref_menu"), InlineKeyboardButton(text="💳 Transfer Balance", callback_data="transfer_menu")],
            [InlineKeyboardButton(text="🌐 Change Language (العربية)", callback_data="toggle_lang")],
            [InlineKeyboardButton(text="💬 Support", url=f"https://t.me/{ADMIN_USERNAME}")]
        ])
    else:
        text_header = (
            "🤖 **أهلاً بك في متجر الأرقام الرسمي** 🌐\n\n"
            "• يمكنك شراء الأرقام واستقبال الكود مباشرة.\n"
            "• اشحن رصيدك عبر نجوم تليجرام واستفد من العروض.\n\n"
            f"🆔 المعرف: `{user_id}`\n"
            f"💵 رصيدك: `${balance:.2f}`\n\n"
            "اختر من القائمة أدناه 👇"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 متجر الأرقام", callback_data="buy_number_menu")],
            [InlineKeyboardButton(text="⚡ حسابي", callback_data="my_account"), InlineKeyboardButton(text="🎁 هدية يومية ($0.01)", callback_data="claim_bonus")],
            [InlineKeyboardButton(text="💳 شحن رصيد نجوم", callback_data="recharge_menu")],
            [InlineKeyboardButton(text="🤝 رابط إحالة ($0.01)", callback_data="ref_menu"), InlineKeyboardButton(text="💳 تحويل رصيد", callback_data="transfer_menu")],
            [InlineKeyboardButton(text="🌐 Change Language (English)", callback_data="toggle_lang")],
            [InlineKeyboardButton(text="💬 الدعم الفني", url=f"https://t.me/{ADMIN_USERNAME}")]
        ])
    return text_header, keyboard

@dp.callback_query(F.data == "toggle_lang")
async def toggle_lang_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    current_lang = get_user_language(user_id)
    new_lang = 'en' if current_lang == 'ar' else 'ar'
    cursor.execute("UPDATE users SET language = ? WHERE user_id = ?", (new_lang, user_id))
    conn.commit()
    
    text, keyboard = get_main_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass
    await callback.answer()

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    args = message.text.split()
    referred_by = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referred_by = int(args[1].replace("ref_", ""))
            if referred_by == user_id:
                referred_by = None
        except ValueError:
            referred_by = None

    if not await check_subscription(user_id):
        sub_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 اشترك في القناة", url=f"https://t.me/{REQUIRED_CHANNEL}")],
            [InlineKeyboardButton(text="🔄 تحقق من الاشتراك", callback_data="check_sub")]
        ])
        await message.answer(
            "⚠️ **عذراً! يجب عليك الاشتراك في القناة أولاً لاستخدام البوت.**\n\n"
            f"اشترك هنا: @{REQUIRED_CHANNEL}\n"
            "ثم اضغط على زر التحقق 👇",
            reply_markup=sub_keyboard,
            parse_mode="Markdown"
        )
        return

    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, balance, referred_by, language) VALUES (?, 0.0, ?, 'ar')", (user_id, referred_by))
        if referred_by:
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (BONUS_AMOUNT, referred_by))
        conn.commit()

    text, keyboard = get_main_keyboard(user_id)
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if await check_subscription(user_id):
        try:
            await callback.message.delete()
        except Exception:
            pass
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users (user_id, balance, language) VALUES (?, 0.0, 'ar')", (user_id,))
            conn.commit()
        text, keyboard = get_main_keyboard(user_id)
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await callback.answer("❌ لم تقم بالاشتراك في القناة بعد!", show_alert=True)

@dp.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    text, keyboard = get_main_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(F.data == "buy_number_menu")
async def buy_number_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇸 أمريكا - $3.00", callback_data="buy_country_1")],
        [InlineKeyboardButton(text="🇨🇴 كولومبيا - $1.00", callback_data="buy_country_2")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]
    ])
    title = "🌍 **اختر الدولة لشراء الرقم:**" if lang == 'ar' else "🌍 **Choose country to buy number:**"
    await callback.message.edit_text(title, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_country_"))
async def buy_country_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    num_id = callback.data.replace("buy_country_", "")
    
    cursor.execute("SELECT 1 FROM user_purchases WHERE user_id = ? AND number_id = ?", (user_id, num_id))
    if cursor.fetchone():
        await callback.answer("❌ لقد قمت بشراء هذا الرقم مسبقاً!", show_alert=True)
        return

    data = NUMBERS_STORE.get(num_id)
    if not data:
        await callback.answer("❌ الرقم غير متوفر حالياً.", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"تأكيد الشراء مقابل ${data['price']:.2f}", callback_data=f"buy_balance_{num_id}")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="buy_number_menu")]
    ])
    
    text = (
        f"الدولة: {data['name']}\n"
        f"السعر: **${data['price']:.2f}**\n\n"
        f"هل تريد تأكيد عملية الشراء؟" if lang == 'ar' else
        f"Country: {data['name']}\nPrice: **${data['price']:.2f}**\n\nConfirm purchase?"
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_balance_"))
async def buy_with_balance(callback: CallbackQuery):
    user_id = callback.from_user.id
    num_id = callback.data.replace("buy_balance_", "")
    data = NUMBERS_STORE.get(num_id)
    lang = get_user_language(user_id)
    
    cursor.execute("SELECT 1 FROM user_purchases WHERE user_id = ? AND number_id = ?", (user_id, num_id))
    if cursor.fetchone():
        await callback.answer("لقد اشتريت هذا الرقم من قبل!", show_alert=True)
        return

    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    balance = row[0] if row else 0.0

    price = data['price']
    if balance < price:
        err = "❌ رصيدك غير كافي لشراء هذا الرقم. يرجى شحن رصيدك." if lang == 'ar' else "❌ Insufficient balance to buy this number. Please top up."
        await callback.answer(err, show_alert=True)
        return

    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, user_id))
    cursor.execute("INSERT INTO user_purchases (user_id, number_id) VALUES (?, ?)", (user_id, num_id))
    conn.commit()
    
    await callback.answer("⏳ جاري جلب كود التفعيل...", show_alert=False)
    otp_text = await fetch_otp_async(data["session"], data["api_id"], data["api_hash"])
    
    success_msg = (
        f"🎉 **تم شراء الرقم بنجاح!**\n\n"
        f"📱 **الرقم المخصص لك:** `{data['phone']}`\n"
        f"💵 **تم خصم:** `${price:.2f}`\n\n"
        f"📥 **حالة الكود (OTP):**\n{otp_text}\n\n"
        f"💡 **تنبيه هام جداً:**\n"
        f"1. اكتب الرقم في تطبيق تيليجرام واطلب الكود.\n"
        f"2. اضغط على زر **(🔄 تحديث الكود)** بالأسفل فوراً لجلب الرسالة الجديدة."
    ) if lang == 'ar' else (
        f"🎉 **Number purchased successfully!**\n\n"
        f"📱 **Your Phone:** `{data['phone']}`\n"
        f"💵 **Deducted:** `${price:.2f}`\n\n"
        f"📥 **OTP Status:**\n{otp_text}\n\n"
        f"💡 **Important Note:**\n"
        f"1. Enter the number in the Telegram app and request the code.\n"
        f"2. Click the **(🔄 Refresh OTP)** button below immediately to get the new message."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 تحديث الكود / Refresh OTP", callback_data=f"get_otp_{num_id}")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية / Main Menu", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(success_msg, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("get_otp_"))
async def get_otp_callback(callback: CallbackQuery):
    num_id = callback.data.replace("get_otp_", "")
    data = NUMBERS_STORE.get(num_id)
    lang = get_user_language(callback.from_user.id)
    if not data:
        await callback.answer("الرقم غير موجود!" if lang == 'ar' else "Number not found!", show_alert=True)
        return
    await callback.answer("⏳ جاري الاتصال وتحديث الكود..." if lang == 'ar' else "⏳ Connecting and refreshing OTP...", show_alert=False)
    otp_text = await fetch_otp_async(data["session"], data["api_id"], data["api_hash"])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 تحديث الكود / Refresh", callback_data=f"get_otp_{num_id}")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية / Main Menu", callback_data="main_menu")]
    ])
    
    msg = (
        f"📱 **الرقم:** `{data['phone']}`\n\n"
        f"📥 **حالة الكود (OTP):**\n{otp_text}\n\n"
        f"💡 اطلب الكود من التطبيق ثم اضغط تحديث."
    ) if lang == 'ar' else (
        f"📱 **Phone:** `{data['phone']}`\n\n"
        f"📥 **OTP Status:**\n{otp_text}\n\n"
        f"💡 Request code from app then click Refresh."
    )
    try:
        await callback.message.edit_text(msg, reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data == "recharge_menu")
async def recharge_menu(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    await state.set_state(States.waiting_for_stars_count)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع / Back", callback_data="main_menu")]])
    
    text = (
        "💳 **شحن الرصيد عبر نجوم تليجرام:**\n\n"
        "🌟 **سعر الشحن:** كل 1 نجمة = 0.02$ (2 سنت)\n\n"
        "أرسل عدد النجوم التي تريد شراءها (مثال: `10` أو `50`):"
    ) if lang == 'ar' else (
        "💳 **Recharge via Telegram Stars:**\n\n"
        "🌟 **Rate:** 1 Star = $0.02\n\n"
        "Send the number of stars you want (e.g. `10` or `50`):"
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.message(States.waiting_for_stars_count)
async def process_custom_stars_input(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ يرجى إدخال أرقام فقط / Enter numbers only:")
        return
    stars_count = int(message.text.strip())
    added_balance = stars_count * STAR_PRICE_USD
    
    prices = [LabeledPrice(label=f"شحن {stars_count} نجمة (${added_balance:.2f})", amount=stars_count)]
    await state.clear()
    await bot.send_invoice(
        chat_id=message.chat.id,
        title=f"شحن رصيد ({stars_count} نجمة)",
        description=f"ستحصل على ${added_balance:.2f} رصيد داخل البوت مقابل {stars_count} نجمة.",
        payload=f"recharge_stars_{stars_count}",
        provider_token="",
        currency="XTR",
        prices=prices,
        start_parameter="stars-recharge"
    )

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    if payload.startswith("recharge_stars_"):
        stars_count = int(payload.replace("recharge_stars_", ""))
        added_balance = stars_count * STAR_PRICE_USD
        user_id = message.from_user.id
        
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (added_balance, user_id))
        conn.commit()
        
        await message.answer(f"🎉 **تم الشحن بنجاح!**\nتم إضافة `${added_balance:.2f}` إلى رصيدك بكل أمان في مجلد البيانات.", parse_mode="Markdown")

@dp.callback_query(F.data == "my_account")
async def my_account(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    balance = row[0] if row else 0.0
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع / Back", callback_data="main_menu")]])
    text = (
        f"⚡ **تفاصيل حسابك (محفوظة بالكامل):**\n\n"
        f"🆔 المعرف: `{user_id}`\n"
        f"💵 الرصيد المتاح: `${balance:.2f}`\n"
        f"*(سنتاتك محفوظة بأمان في مجلد Volume ولن تختفي أبداً)*"
    ) if lang == 'ar' else (
        f"⚡ **Your Account Details (Fully Saved):**\n\n"
        f"🆔 ID: `{user_id}`\n"
        f"💵 Available Balance: `${balance:.2f}`\n"
        f"*(Your balance is securely saved in the Volume folder and will never disappear)*"
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "claim_bonus")
async def claim_bonus(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    cursor.execute("SELECT last_bonus, balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    last_bonus_str = row[0] if row else None
    
    now = datetime.now()
    if last_bonus_str:
        last_bonus = datetime.fromisoformat(last_bonus_str)
        if now - last_bonus < timedelta(hours=24):
            msg = "❌ لقد حصلت على هديتك اليومية بالفعل، عد غداً!" if lang == 'ar' else "❌ You have already claimed your daily bonus, come back tomorrow!"
            await callback.answer(msg, show_alert=True)
            return

    cursor.execute("UPDATE users SET balance = balance + ?, last_bonus = ? WHERE user_id = ?", (BONUS_AMOUNT, now.isoformat(), user_id))
    conn.commit()
    
    success_msg = f"🎉 تم إضافة ${BONUS_AMOUNT:.2f} إلى رصيدك بنجاح!" if lang == 'ar' else f"🎉 Added ${BONUS_AMOUNT:.2f} to your balance!"
    await callback.answer(success_msg, show_alert=True)
    text, keyboard = get_main_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data == "ref_menu")
async def ref_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع / Back", callback_data="main_menu")]])
    
    text = (
        f"🤝 **رابط الإحالة الخاص بك:**\n`{ref_link}`\n\n"
        f"احصل على **${BONUS_AMOUNT:.2f}** فوراً عن كل شخص يسجل من رابطك وتضاف مباشرة لمجلد البيانات الدائم!"
    ) if lang == 'ar' else (
        f"🤝 **Your Referral Link:**\n`{ref_link}`\n\n"
        f"Get **${BONUS_AMOUNT:.2f}** for each referral added securely to the permanent data folder!"
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "transfer_menu")
async def transfer_menu_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    await state.set_state(States.waiting_for_transfer_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع / Back", callback_data="main_menu")]])
    prompt = "💳 أرسل آيدي (User ID) الشخص المراد تحويل الرصيد له:" if lang == 'ar' else "💳 Send recipient User ID:"
    await callback.message.edit_text(prompt, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.message(States.waiting_for_transfer_id)
async def process_transfer_id(message: Message, state: FSMContext):
    lang = get_user_language(message.from_user.id)
    if not message.text.strip().isdigit():
        err = "❌ يرجى إدخال ID صحيح / Enter valid ID:" if lang == 'ar' else "❌ Enter valid ID:"
        await message.answer(err)
        return
    await state.update_data(recipient_id=int(message.text.strip()))
    await state.set_state(States.waiting_for_transfer_amount)
    prompt = "✍️ أرسل المبلغ المراد تحويله (مثال: `0.02`):" if lang == 'ar' else "✍️ Send the amount to transfer (e.g. `0.02`):"
    await message.answer(prompt)

@dp.message(States.waiting_for_transfer_amount)
async def process_transfer_amount(message: Message, state: FSMContext):
    lang = get_user_language(message.from_user.id)
    try:
        amount = float(message.text.strip().replace("$", ""))
    except ValueError:
        err = "❌ أدخل مبلغاً صحيحاً / Enter valid amount:" if lang == 'ar' else "❌ Enter valid amount:"
        await message.answer(err)
        return
    
    sender_id = message.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (sender_id,))
    row = cursor.fetchone()
    sender_balance = row[0] if row else 0.0
    
    if sender_balance < amount:
        err = "❌ رصيدك الحالي لا يكفي لإتمام عملية التحويل!" if lang == 'ar' else "❌ Insufficient current balance!"
        await message.answer(err)
        await state.clear()
        return

    data = await state.get_data()
    recipient_id = data.get("recipient_id")
    
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (recipient_id,))
    rec_row = cursor.fetchone()
    if not rec_row:
        err = "❌ المستخدم المراد التحويل له غير مسجل في البوت." if lang == 'ar' else "❌ Recipient is not registered in the bot."
        await message.answer(err)
        await state.clear()
        return

    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, sender_id))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, recipient_id))
    conn.commit()
    await state.clear()
    
    success_msg = f"✅ تم تحويل `${amount:.2f}` بنجاح للمستخدم `{recipient_id}`!" if lang == 'ar' else f"✅ Successfully transferred `${amount:.2f}` to user `{recipient_id}`!"
    await message.answer(success_msg, parse_mode="Markdown")

# 🛠️ دالة جلب واستخراج كود OTP
async def fetch_otp_async(session_str, api_id, api_hash):
    if not session_str or "ضع_جلسة" in session_str:
        return "❌ لم يتم ضبط جلسة هذا الرقم بعد من قبل الإدارة! / Session not configured!"
    try:
        client = TelegramClient(StringSession(session_str), api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return "❌ الجلسة منتهية أو محظورة من تيليجرام. / Session expired or banned."
        
        messages = await client.get_messages(777000, limit=5)
        await client.disconnect()
        
        if not messages:
            return "⏳ لم يصل الكود بعد.. أطلب الكود من تطبيق تيليجرام أولاً ثم اضغط تحديث. / OTP not arrived yet."
        
        for msg in messages:
            if msg.text:
                otp_match = re.search(r'\b\d{5}\b', msg.text)
                if otp_match:
                    code = otp_match.group(0)
                    msg_time = msg.date.strftime("%Y-%m-%d %H:%M:%S")
                    return f"🔑 **الكود / Code:** `{code}`\n⏰ **الوقت / Time:** {msg_time}"
        
        latest_text = messages[0].text
        return f"📩 **وصلت رسالة جديدة / New message:**\n\n`{latest_text}`"
        
    except Exception as e:
        return f"❌ خطأ أثناء الاتصال بالجلسة / Connection error: {str(e)}"

async def main():
    print("جاري تشغيل البوت مع الأسعار الجديدة وتحديثات مجلد البيانات...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
    await asyncio.sleep(1)
    await dp.start_polling(bot, close_bot_session=True)

if __name__ == "__main__":
    asyncio.run(main())
