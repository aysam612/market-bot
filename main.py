import os
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
BOT_TOKEN = "8947041920:AAFF8llkbKrI8WqBowy1IEjC8kso8ya7NJQ"
ADMIN_USERNAME = "diddy0"

# قناة الاشتراك الإجباري
REQUIRED_CHANNEL = "VPP8P"

# سعر الرقم الأمريكي الأساسي
USA_NUMBER_PRICE = 0.50

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

# ================= قاعدة البيانات الأساسية =================
conn = sqlite3.connect("telegram_bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0.0,
    last_bonus TEXT,
    referred_by INTEGER
)
""")
conn.commit()

# ================= مخزن الأرقام الأساسي =================
NUMBERS_STORE = {
    "1": {
        "country": "usa", 
        "name": "🇺🇸 أمريكا (غير سليمين)", 
        "price": USA_NUMBER_PRICE, 
        "phone": "+13025060244",
        "session": "1AZWarzYBu4DsJhY23nLFER2qDvE9lqCBXrQ27HVWKLqXChIJflm3zoBMhdsya9NdpEfChtBNOBW7PLtdyciAT5rXmZKBC7ky85O3NzH_DWwHs-K_Jrqal9vPyPawIjgq0S3wEumn2ntGrXL3sZObdteRHVh5M-1mdnW7_vIa7W3DQk00P_k7e595JFTtY0kvbC5CeI4yTswQ0ZFxBDgMtH099iKenqtEB6K3-somzxxNiZaPTMl_XYJCNmaBfOA_f-tIb_I1jjekQ-hVeKLh9d5hP2b-05rH1cuqb92EZGWMNm6Wy3KW86nGC7ShF3Cum5yoYlwbj-By4R8XlI3otfuyOvFz5Io=",
        "api_id": 34198296, 
        "api_hash": "8b007a14ebc08f01120d0ebs8ba4d595", 
        "sold": False, 
        "buyer_id": None
    },
    "2": {
        "country": "usa", 
        "name": "🇺🇸 أمريكا (غير سليمين)", 
        "price": USA_NUMBER_PRICE, 
        "phone": "+13649004531",
        "session": "1AZWarzYBu2uAspmH_zOu7qW53ONrFQw6vhIypDVm5N9LMiUAmBhkON--qPfBcT83HDjTJUeBWNJQ0UELHaLo0xnDnVi3MTm9ZyaGlIO-h5P2LH7OB1jghSFqD_ysUgbUagvN6p8BElr4gmVNO2L5I5sOL52rzHHwbcRCKB-DQvrXH3D7X7yBUXT7UZ8kKs0Ve_926fUoLoUzI1UBvGmdP5Gd8cYHmZJiDjUxFkALKNHlexdJToWLiY-svegkzXGq1ICBjaGGNCMAk__P1-W-HvRv2NbTfX3SDaPFzitNJzqRfxFDf8tysezYXHnzRbBz4cvqEQqcSVrTwvwI6kW7h5uA8Pz2zk0=",
        "api_id": 34198296, 
        "api_hash": "8b007a14ebc08f01120d0ebs8ba4d595", 
        "sold": False, 
        "buyer_id": None
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

def get_main_keyboard(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    balance = row[0] if row and row[0] is not None else 0.0
    
    text_header = (
        "🤖 **أهلاً بك في متجر الأرقام الرسمي** 🌐\n\n"
        "• يمكنك شراء أرقام تليجرام واستقبال الكود مباشرة.\n"
        "• اشحن رصيدك عبر نجوم تليجرام واستفد من العروض.\n\n"
        f"🆔 المعرف: `{user_id}`\n"
        f"💵 رصيدك: `${balance:.2f}`\n\n"
        "اختر من القائمة أدناه 👇"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 شراء رقم جديد", callback_data="buy_number_menu")],
        [InlineKeyboardButton(text="⚡ حسابي", callback_data="my_account"), InlineKeyboardButton(text="🎁 هدية يومية ($0.01)", callback_data="claim_bonus")],
        [InlineKeyboardButton(text="💳 شحن رصيد نجوم", callback_data="recharge_menu")],
        [InlineKeyboardButton(text="🤝 رابط إحالة ($0.01)", callback_data="ref_menu"), InlineKeyboardButton(text="💳 تحويل رصيد", callback_data="transfer_menu")],
        [InlineKeyboardButton(text="💬 الدعم الفني", url=f"https://t.me/{ADMIN_USERNAME}")]
    ])
    return text_header, keyboard

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
        cursor.execute("INSERT INTO users (user_id, balance, referred_by) VALUES (?, 0.0, ?)", (user_id, referred_by))
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
            cursor.execute("INSERT INTO users (user_id, balance) VALUES (?, 0.0)", (user_id,))
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
    available_usa = sum(1 for d in NUMBERS_STORE.values() if d["country"] == "usa" and not d["sold"])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🇺🇸 أمريكا (غير سليمين) ({available_usa}) - ${USA_NUMBER_PRICE:.2f}", callback_data="buy_country_usa")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]
    ])
    await callback.message.edit_text("🌍 **اختر الدولة لشراء رقم:**", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

# شراء عشوائي مباشر عند اختيار الدولة
@dp.callback_query(F.data == "buy_country_usa")
async def buy_country_usa_handler(callback: CallbackQuery):
    available_ids = [nid for nid, d in NUMBERS_STORE.items() if d["country"] == "usa" and not d["sold"]]
    
    if not available_ids:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="buy_number_menu")]])
        await callback.message.edit_text("للأسف نفدت الأرقام المتوفرة حالياً 🔴", reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer()
        return

    # اختيار رقم عشوائي تلقائياً
    num_id = random.choice(available_ids)
    data = NUMBERS_STORE[num_id]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"تأكيد الشراء من الرصيد (${data['price']:.2f})", callback_data=f"buy_balance_{num_id}")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="buy_number_menu")]
    ])
    await callback.message.edit_text(
        f"الدولة: {data['name']}\nالسعر: ${data['price']:.2f}\n\nسيتم اختيار رقم لك تلقائياً عند تأكيد الشراء.\nتأكيد عملية الشراء؟",
        reply_markup=keyboard, parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_balance_"))
async def buy_with_balance(callback: CallbackQuery):
    user_id = callback.from_user.id
    num_id = callback.data.replace("buy_balance_", "")
    data = NUMBERS_STORE.get(num_id)
    
    if not data or data["sold"]:
        await callback.answer("عذراً، الرقم تم بيعه لمستخدم آخر! حاول مجدداً.", show_alert=True)
        return
        
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0]
    
    if balance < data["price"]:
        await callback.answer("❌ رصيدك غير كافٍ لشراء هذا الرقم!", show_alert=True)
        return

    # خصم سعر الرقم فقط والاحتفاظ بالمتبقي
    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (data["price"], user_id))
    conn.commit()
    
    NUMBERS_STORE[num_id]["sold"] = True
    NUMBERS_STORE[num_id]["buyer_id"] = user_id
    
    await callback.answer("⏳ جاري جلب كود التفعيل...", show_alert=False)
    otp_text = await fetch_otp_async(data["session"], data["api_id"], data["api_hash"])
    
    success_msg = (
        f"✅ **تم الشراء بنجاح!**\n\n"
        f"📱 **الرقم المخصص لك:** `{data['phone']}`\n"
        f"💵 **الخصم:** ${data['price']:.2f}\n\n"
        f"📥 **كود التحقق (OTP):**\n`{otp_text}`\n\n"
        f"💡 **ملاحظة هامّة جداً:**\nقم بطلب كود التفعيل داخل تطبيق تيليجرام أولاً، ثم اضغط على زر **(🔄 تحديث الكود)** بالأسفل ليظهر لك الكود فوراً."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 تحديث الكود (OTP)", callback_data=f"get_otp_{num_id}")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(success_msg, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("get_otp_"))
async def get_otp_callback(callback: CallbackQuery):
    num_id = callback.data.replace("get_otp_", "")
    data = NUMBERS_STORE.get(num_id)
    if not data:
        await callback.answer("الرقم غير موجود!", show_alert=True)
        return
    await callback.answer("⏳ جاري الاتصال وتحديث الكود...", show_alert=False)
    otp_text = await fetch_otp_async(data["session"], data["api_id"], data["api_hash"])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 تحديث الكود (OTP)", callback_data=f"get_otp_{num_id}")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])
    
    msg = (
        f"📱 **الرقم:** `{data['phone']}`\n\n"
        f"📥 **الكود الحالي (OTP):**\n`{otp_text}`\n\n"
        f"💡 **ملاحظة:** قم بطلب كود التفعيل في تطبيق تيليجرام أولاً، ثم اضغط على زر **(🔄 تحديث الكود)** ليظهر لك الكود فوراً."
    )
    try:
        await callback.message.edit_text(msg, reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data == "recharge_menu")
async def recharge_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(States.waiting_for_stars_count)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]])
    await callback.message.edit_text(
        "💳 **شحن الرصيد عبر نجوم تليجرام:**\n\n"
        "🌟 **سعر الشحن:** كل 1 نجمة = 0.02$ (2 سنت)\n\n"
        "أرسل عدد النجوم التي تريد شراءها (مثال: `10` أو `50`):",
        reply_markup=keyboard, parse_mode="Markdown"
    )
    await callback.answer()

@dp.message(States.waiting_for_stars_count)
async def process_custom_stars_input(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ يرجى إدخال أرقام فقط:")
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
        
        await message.answer(f"🎉 **تم الشحن بنجاح!**\nتم إضافة `${added_balance:.2f}` إلى رصيدك مقابل `{stars_count}` نجمة.", parse_mode="Markdown")

@dp.callback_query(F.data == "my_account")
async def my_account(callback: CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]])
    await callback.message.edit_text(f"⚡ **تفاصيل حسابك:**\n\n🆔 المعرف: `{user_id}`\n💵 الرصيد المتاح: `${balance:.2f}`", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "claim_bonus")
async def claim_bonus(callback: CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT last_bonus, balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    last_bonus_str = row[0]
    
    now = datetime.now()
    if last_bonus_str:
        last_bonus = datetime.fromisoformat(last_bonus_str)
        if now - last_bonus < timedelta(hours=24):
            await callback.answer("❌ لقد حصلت على هديتك اليومية بالفعل، عد غداً!", show_alert=True)
            return

    cursor.execute("UPDATE users SET balance = balance + ?, last_bonus = ? WHERE user_id = ?", (BONUS_AMOUNT, now.isoformat(), user_id))
    conn.commit()
    await callback.answer(f"🎉 تم إضافة ${BONUS_AMOUNT:.2f} (سنت واحد) إلى رصيدك!", show_alert=True)
    text, keyboard = get_main_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data == "ref_menu")
async def ref_menu(callback: CallbackQuery):
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{callback.from_user.id}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]])
    await callback.message.edit_text(
        f"🤝 **رابط الإحالة الخاص بك:**\n`{ref_link}`\n\n"
        f"احصل على **${BONUS_AMOUNT:.2f}** (سنت واحد) فوراً عن كل شخص يسجل من رابطك!", 
        reply_markup=keyboard, parse_mode="Markdown"
    )
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
    await message.answer("✍️ أرسل المبلغ المراد تحويله:")

@dp.message(States.waiting_for_transfer_amount)
async def process_transfer_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace("$", ""))
    except ValueError:
        await message.answer("❌ أدخل مبلغاً صحيحاً:")
        return
    
    sender_id = message.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (sender_id,))
    sender_balance = cursor.fetchone()[0]
    
    if sender_balance < amount:
        await message.answer("❌ رصيدك الحالي لا يكفي لإتمام عملية التحويل!")
        await state.clear()
        return

    data = await state.get_data()
    recipient_id = data.get("recipient_id")
    
    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, sender_id))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, recipient_id))
    conn.commit()
    await state.clear()
    await message.answer(f"✅ تم تحويل `${amount:.2f}` بنجاح للمستخدم `{recipient_id}`!", parse_mode="Markdown")

async def fetch_otp_async(session_str, api_id, api_hash):
    if not session_str:
        return "لا توجد جلسة ❌"
    try:
        client = TelegramClient(StringSession(session_str), api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return "الجلسة منتهية أو محظورة عام ❌"
        messages = await client.get_messages(777000, limit=1)
        await client.disconnect()
        if not messages:
            return "لم يصل كود التفعيل بعد ⏳ (اطلب الكود في تطبيق تيليجرام ثم اضغط تحديث)"
        return messages[0].message
    except Exception as e:
        return f"خطأ في الاتصال: {str(e)}"

async def main():
    print("جاري تشغيل بوت الأرقام الأساسي...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
    await asyncio.sleep(1)
    await dp.start_polling(bot, close_bot_session=True)

if __name__ == "__main__":
    asyncio.run(main())
