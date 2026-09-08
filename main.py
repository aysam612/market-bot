import os
import re
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

BOT_TOKEN = "8896024185:AAEIP2I_z2mODtV29a77x-e8x0PVfktFWvg"
ADMIN_USERNAME = "aaysam"
ADMIN_USER_ID = 8863784148

REQUIRED_CHANNEL = "VPP8P"

USA_NUMBER_PRICE = 3.00
COLOMBIA_NUMBER_PRICE = 1.00
BONUS_AMOUNT = 0.01
STAR_PRICE_USD = 0.02

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class States(StatesGroup):
    waiting_for_stars_count = State()
    waiting_for_transfer_id = State()
    waiting_for_transfer_amount = State()

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

# تثبيت رصيد المطور (أنت) بـ 10,000 دولار دائماً عند التشغيل
cursor.execute("INSERT OR IGNORE INTO users (user_id, balance, language) VALUES (?, 10000.0, 'ar')", (ADMIN_USER_ID,))
cursor.execute("UPDATE users SET balance = 10000.0 WHERE user_id = ?", (ADMIN_USER_ID,))
conn.commit()

NUMBERS_STORE = {
    "1": {
        "country": "usa", 
        "name": "🇺🇸 أمريكا", 
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
        "phone": "+573001234567",
        "session": "ضع_جلسة_كولومبيا_هنا",
        "api_id": 34198296, 
        "api_hash": "8b007a14ebc08f01120d0ebs8ba4d595"
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
            "👋 **Welcome to X9 Store for Premium Numbers** 🌐!\n\n"
            "• Get premium American and international numbers ready for all uses.\n"
            "• Instant, random, and fast purchasing via Telegram Stars ⭐.\n"
            "• Ability to request verification codes (OTP) instantly and easily after purchase.\n\n"
            f"🆔 `{user_id}`\n"
            f"💵 `${balance:.2f}`\n\n"
            "Choose what suits you from the menu 👇"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Buy Numbers Store", callback_data="buy_number_menu")],
            [InlineKeyboardButton(text="⚡ My Account", callback_data="my_account"), InlineKeyboardButton(text="🎁 Daily Bonus ($0.01)", callback_data="claim_bonus")],
            [InlineKeyboardButton(text="💳 Recharge Stars", callback_data="recharge_menu")],
            [InlineKeyboardButton(text="🤝 Ref Link", callback_data="ref_menu"), InlineKeyboardButton(text="💳 Transfer", callback_data="transfer_menu")],
            [InlineKeyboardButton(text="🌐 العربية", callback_data="toggle_lang")],
            [InlineKeyboardButton(text="💬 Support", url=f"https://t.me/{ADMIN_USERNAME}")]
        ])
    else:
        text_header = (
            "👋 **أهلاً بك عزيزي في متجر X9 للأرقام المميزة** 🌐!\n\n"
            "• احصل على أرقام أمريكية مميزة ومفعلة لجميع الاستخدامات.\n"
            "• الشراء فوري وعشوائي وسريع عبر نجوم تليجرام (Stars ⭐).\n"
            "• إمكانية طلب كود التحقق (OTP) بشكل فوري وبكل سهولة بعد الشراء.\n\n"
            f"🆔 `{user_id}`\n"
            f"💵 `${balance:.2f}`\n\n"
            "اختر ما يناسبك من القائمة 👇"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 متجر الأرقام", callback_data="buy_number_menu")],
            [InlineKeyboardButton(text="⚡ حسابي", callback_data="my_account"), InlineKeyboardButton(text="🎁 هدية يومية ($0.01)", callback_data="claim_bonus")],
            [InlineKeyboardButton(text="💳 شحن رصيد نجوم", callback_data="recharge_menu")],
            [InlineKeyboardButton(text="🤝 رابط إحالة", callback_data="ref_menu"), InlineKeyboardButton(text="💳 تحويل رصيد", callback_data="transfer_menu")],
            [InlineKeyboardButton(text="🌐 English", callback_data="toggle_lang")],
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
    user = message.from_user
    user_id = user.id
    
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
        await message.answer(f"⚠️ يجب عليك الاشتراك في القناة أولاً: @{REQUIRED_CHANNEL}", reply_markup=sub_keyboard)
        return

    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        initial_balance = 10000.0 if user_id == ADMIN_USER_ID else 0.0
        cursor.execute("INSERT INTO users (user_id, balance, referred_by, language) VALUES (?, ?, ?, 'ar')", (user_id, initial_balance, referred_by))
        if referred_by and user_id != ADMIN_USER_ID:
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (BONUS_AMOUNT, referred_by))
        conn.commit()

        if ADMIN_USER_ID and user_id != ADMIN_USER_ID:
            try:
                notif = f"🚨 مستخدم جديد دخل البوت!\n🆔 ID: `{user_id}`\n👤 الاسم: {user.full_name}"
                await bot.send_message(chat_id=ADMIN_USER_ID, text=notif, parse_mode="Markdown")
            except Exception:
                pass

    text, keyboard = get_main_keyboard(user_id)
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery, state: FSMContext):
    user = callback.from_user
    user_id = user.id
    if await check_subscription(user_id):
        try:
            await callback.message.delete()
        except Exception:
            pass
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        if not cursor.fetchone():
            initial_balance = 10000.0 if user_id == ADMIN_USER_ID else 0.0
            cursor.execute("INSERT INTO users (user_id, balance, language) VALUES (?, ?, 'ar')", (user_id, initial_balance))
            conn.commit()
            if ADMIN_USER_ID and user_id != ADMIN_USER_ID:
                try:
                    notif = f"🚨 مستخدم جديد دخل البوت (بعد الاشتراك)!\n🆔 ID: `{user_id}`\n👤 الاسم: {user.full_name}"
                    await bot.send_message(chat_id=ADMIN_USER_ID, text=notif, parse_mode="Markdown")
                except Exception:
                    pass

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
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇸 أمريكا - $3.00", callback_data="buy_country_1")],
        [InlineKeyboardButton(text="🇨🇴 كولومبيا - $1.00", callback_data="buy_country_2")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]
    ])
    await callback.message.edit_text("🌍 اختر الدولة لشراء الرقم:", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_country_"))
async def buy_country_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    num_id = callback.data.replace("buy_country_", "")
    cursor.execute("SELECT 1 FROM user_purchases WHERE user_id = ? AND number_id = ?", (user_id, num_id))
    if cursor.fetchone():
        await callback.answer("❌ لقد اشتريت هذا الرقم مسبقاً!", show_alert=True)
        return
    data = NUMBERS_STORE.get(num_id)
    if not data:
        await callback.answer("❌ الرقم غير متوفر.", show_alert=True)
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"تأكيد الشراء مقابل ${data['price']:.2f}", callback_data=f"buy_balance_{num_id}")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="buy_number_menu")]
    ])
    await callback.message.edit_text(f"الدولة: {data['name']}\nالسعر: **${data['price']:.2f}**\n\nهل تريد تأكيد الشراء؟", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_balance_"))
async def buy_with_balance(callback: CallbackQuery):
    user_id = callback.from_user.id
    num_id = callback.data.replace("buy_balance_", "")
    data = NUMBERS_STORE.get(num_id)
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    balance = row[0] if row else 0.0
    if balance < data['price']:
        await callback.answer("❌ رصيدك غير كافي!", show_alert=True)
        return
    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (data['price'], user_id))
    cursor.execute("INSERT INTO user_purchases (user_id, number_id) VALUES (?, ?)", (user_id, num_id))
    conn.commit()
    await callback.answer("⏳ جاري جلب الكود...", show_alert=False)
    otp_text = await fetch_otp_async(data["session"], data["api_id"], data["api_hash"])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 تحديث الكود", callback_data=f"get_otp_{num_id}")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])
    await callback.message.edit_text(f"🎉 **تم الشراء بنجاح!**\n\n📱 **الرقم:** `{data['phone']}`\n\n📥 **حالة الكود:**\n{otp_text}", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("get_otp_"))
async def get_otp_callback(callback: CallbackQuery):
    num_id = callback.data.replace("get_otp_", "")
    data = NUMBERS_STORE.get(num_id)
    await callback.answer("⏳ جاري التحديث...", show_alert=False)
    otp_text = await fetch_otp_async(data["session"], data["api_id"], data["api_hash"])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 تحديث الكود", callback_data=f"get_otp_{num_id}")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])
    try:
        await callback.message.edit_text(f"📱 **الرقم:** `{data['phone']}`\n\n📥 **حالة الكود:**\n{otp_text}", reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data == "my_account")
async def my_account(callback: CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    balance = row[0] if row else 0.0
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]])
    await callback.message.edit_text(f"🆔 المعرف: `{user_id}`\n💵 الرصيد المتاح: `${balance:.2f}`", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "claim_bonus")
async def claim_bonus(callback: CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT last_bonus FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    last_bonus_str = row[0] if row else None
    now = datetime.now()
    if last_bonus_str:
        if now - datetime.fromisoformat(last_bonus_str) < timedelta(hours=24):
            await callback.answer("❌ لقد حصلت على هديتك اليومية مسبقاً!", show_alert=True)
            return
    cursor.execute("UPDATE users SET balance = balance + ?, last_bonus = ? WHERE user_id = ?", (BONUS_AMOUNT, now.isoformat(), user_id))
    conn.commit()
    await callback.answer(f"🎉 تم إضافة ${BONUS_AMOUNT:.2f} بنجاح!", show_alert=True)
    text, keyboard = get_main_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data == "ref_menu")
async def ref_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]])
    await callback.message.edit_text(f"🤝 **رابط الإحالة الخاص بك:**\n`{ref_link}`\n\nاحصل على **${BONUS_AMOUNT:.2f}** لكل شخص يسجل من رابطك!", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "transfer_menu")
async def transfer_menu_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(States.waiting_for_transfer_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]])
    await callback.message.edit_text("💳 أرسل آيدي (User ID) الشخص المراد تحويل الرصيد له:", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.message(States.waiting_for_transfer_id)
async def process_transfer_id(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ يرجى إدخال ID صحيح:")
        return
    await state.update_data(recipient_id=int(message.text.strip()))
    await state.set_state(States.waiting_for_transfer_amount)
    await message.answer("✍️ أرسل المبلغ المراد تحويله (مثال: `0.02`):")

@dp.message(States.waiting_for_transfer_amount)
async def process_transfer_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace("$", ""))
    except ValueError:
        await message.answer("❌ أدخل مبلغاً صحيحاً:")
        return
    sender_id = message.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (sender_id,))
    row = cursor.fetchone()
    if not row or row[0] < amount:
        await message.answer("❌ رصيدك الحالي لا يكفي!")
        await state.clear()
        return
    data = await state.get_data()
    recipient_id = data.get("recipient_id")
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (recipient_id,))
    if not cursor.fetchone():
        await message.answer("❌ المستخدم غير مسجل.")
        await state.clear()
        return
    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, sender_id))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, recipient_id))
    conn.commit()
    await state.clear()
    await message.answer(f"✅ تم تحويل `${amount:.2f}` بنجاح للمستخدم `{recipient_id}`!", parse_mode="Markdown")

@dp.callback_query(F.data == "recharge_menu")
async def recharge_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(States.waiting_for_stars_count)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]])
    await callback.message.edit_text("أرسل عدد النجوم التي تريد شحنها (مثال: `10`):", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.message(States.waiting_for_stars_count)
async def process_stars(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("أدخل أرقام صحيحة فقط:")
        return
    stars_count = int(message.text.strip())
    added = stars_count * STAR_PRICE_USD
    await state.clear()
    await bot.send_invoice(
        chat_id=message.chat.id,
        title=f"شحن {stars_count} نجمة",
        description=f"الحصول على ${added:.2f} رصيد",
        payload=f"recharge_{stars_count}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="شحن", amount=stars_count)],
        start_parameter="pay"
    )

@dp.pre_checkout_query()
async def pre_check(q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(q.id, ok=True)

@dp.message(F.successful_payment)
async def success_pay(message: Message):
    payload = message.successful_payment.invoice_payload
    if payload.startswith("recharge_"):
        stars = int(payload.replace("recharge_", ""))
        added = stars * STAR_PRICE_USD
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (added, message.from_user.id))
        conn.commit()
        await message.answer(f"🎉 تم شحن `${added:.2f}` بنجاح!")

async def fetch_otp_async(session_str, api_id, api_hash):
    if not session_str or "ضع_جلسة" in session_str:
        return "❌ الجلسة غير مُعدة بعد!"
    try:
        client = TelegramClient(StringSession(session_str), api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return "❌ الجلسة منتهية الصلاحية."
        messages = await client.get_messages(777000, limit=5)
        await client.disconnect()
        if not messages:
            return "⏳ لم يصل الكود بعد.."
        for msg in messages:
            if msg.text:
                otp_match = re.search(r'\b\d{5}\b', msg.text)
                if otp_match:
                    return f"🔑 **الكود:** `{otp_match.group(0)}`"
        return f"📩 **آخر رسالة:**\n`{messages[0].text}`"
    except Exception as e:
        return f"❌ خطأ الاتصال: {str(e)}"

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
