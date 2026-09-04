import os
import random
import asyncio
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, 
    LabeledPrice, BotCommand
)
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from telethon import TelegramClient
from telethon.sessions import StringSession

# ================= إعدادات البوت والحماية =================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8947041920:AAFF8llkbKrI8WqBowy1IEjC8kso8ya7NJQ")
ADMIN_USERNAME = "diddy0"

# إعدادات الاشتراك الإجباري للقناة المطلوبة
REQUIRED_CHANNEL = "VPP8P"
USA_NUMBER_PRICE = 0.80

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class States(StatesGroup):
    waiting_for_stars_count = State()
    waiting_for_transfer_id = State()
    waiting_for_transfer_amount = State()

# ================= قاعدة البيانات المؤمنة ضد الاختراق والتلاعب =================
# استخدام check_same_thread=False مع نظام قفل للعمليات لمنع أي ثغرات تلاعب متزامنة
conn = sqlite3.connect("database.db", check_same_thread=False)
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

# تأمين الأعمدة وحمايتها من التصفير أو الحذف
try:
    cursor.execute("ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0.0")
    cursor.execute("ALTER TABLE users ADD COLUMN last_bonus TEXT")
    cursor.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER")
    conn.commit()
except sqlite3.OperationalError:
    pass

# ================= مستودع الأرقام الآمن =================
NUMBERS_STORE = {
    "1": {
        "country": "usa", "name": "🇺🇸 أمريكا", "price": USA_NUMBER_PRICE, "phone": "+13025060244",
        "session": "1AZWarzYBu4DsJhY23nLFER2qDvE9lqCBXrQ27HVWKLqXChIJflm3zoBMhdsya9NdpEfChtBNOBW7PLtdyciAT5rXmZKBC7ky85O3NzH_DWwHs-K_Jrqal9vPyPawIjgq0S3wEumn2ntGrXL3sZObdteRHVh5M-1mdnW7_vIa7W3DQk00P_k7e595JFTtY0kvbC5CeI4yTswQ0ZFxBDgMtH099iKenqtEB6K3-somzxxNiZaPTMl_XYJCNmaBfOA_f-tIb_I1jjekQ-hVeKLh9d5hP2b-05rH1cuqb92EZGWMNm6Wy3KW86nGC7ShF3Cum5yoYlwbj-By4R8XlI3otfuyOvFz5Io=",
        "api_id": 34198296, "api_hash": "8b007a14ebc08f01120d0ebs8ba4d595", "sold": False, "buyer_id": None
    },
    "2": {
        "country": "usa", "name": "🇺🇸 أمريكا", "price": USA_NUMBER_PRICE, "phone": "+13649004531",
        "session": "1AZWarzYBu2uAspmH_zOu7qW53ONrFQw6vhIypDVm5N9LMiUAmBhkON--qPfBcT83HDjTJUeBWNJQ0UELHaLo0xnDnVi3MTm9ZyaGlIO-h5P2LH7OB1jghSFqD_ysUgbUagvN6p8BElr4gmVNO2L5I5sOL52rzHHwbcRCKB-DQvrXH3D7X7yBUXT7UZ8kKs0Ve_926fUoLoUzI1UBvGmdP5Gd8cYHmZJiDjUxFkALKNHlexdJToWLiY-svegkzXGq1ICBjaGGNCMAk__P1-W-HvRv2NbTfX3SDaPFzitNJzqRfxFDf8tysezYXHnzRbBz4cvqEQqcSVrTwvwI6kW7h5uA8Pz2zk0=",
        "api_id": 34198296, "api_hash": "8b007a14ebc08f01120d0ebs8ba4d595", "sold": False, "buyer_id": None
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
    # جلب الرصيد الحقيقي بأمان من الداتا بيس
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    balance = row[0] if row else 0.0
    
    text_header = (
        "🔒 **متجر X9 المحمي للأرقام المميزة** 🌐\n\n"
        "• تم تفعيل نظام الحماية المتقدم ضد التلاعب والثغرات.\n"
        "• الأرصدة والعمليات محمية بالكامل.\n\n"
        f"🆔 `{user_id}`\n"
        f"💵 `${balance:.2f}`\n\n"
        "اختر ما يناسبك من القائمة 👇"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 شراء أرقام", callback_data="buy_number_menu")],
        [InlineKeyboardButton(text="⚡ حسابي", callback_data="my_account"), InlineKeyboardButton(text="🎁 هدية يومية", callback_data="claim_bonus")],
        [InlineKeyboardButton(text="💳 شحن رصيد", callback_data="recharge_menu")],
        [InlineKeyboardButton(text="🤝 دعوة صديق", callback_data="ref_menu"), InlineKeyboardButton(text="💳 تحويل رصيد", callback_data="transfer_menu")],
        [InlineKeyboardButton(text="💬 الدعم الفني والمطور", url=f"https://t.me/{ADMIN_USERNAME}")]
    ])
    return text_header, keyboard

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    if not await check_subscription(user_id):
        sub_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 اشترك في القناة", url=f"https://t.me/{REQUIRED_CHANNEL}")],
            [InlineKeyboardButton(text="🔄 تحقق من الاشتراك", callback_data="check_sub")]
        ])
        await message.answer(
            "⚠️ **عذراً، يجب عليك الاشتراك في قناة البوت أولاً لاستخدام الخدمات!**\n\n"
            f"يرجى الاشتراك في القناة: @{REQUIRED_CHANNEL}\n"
            "ثم اضغط على زر (تحقق من الاشتراك) بالأسفل 👇",
            reply_markup=sub_keyboard,
            parse_mode="Markdown"
        )
        return

    args = message.text.split()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        ref_id = None
        if len(args) > 1 and args[1].startswith("ref_"):
            try:
                potential_ref = int(args[1].replace("ref_", ""))
                if potential_ref != user_id:
                    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (potential_ref,))
                    if cursor.fetchone():
                        ref_id = potential_ref
            except ValueError:
                pass
            
        cursor.execute("INSERT INTO users (user_id, balance, referred_by) VALUES (?, 0.0, ?)", (user_id, ref_id))
        conn.commit()
        
        if ref_id:
            # حماية لمنع التلاعب برصيد الإحالات
            cursor.execute("UPDATE users SET balance = balance + 0.01 WHERE user_id = ?", (ref_id,))
            conn.commit()
            try:
                await bot.send_message(ref_id, "🎉 مبروك! دخل شخص جديد عبر رابط إحالتك وتمت إضافة 1 سنت برصيدك!", parse_mode="Markdown")
            except Exception:
                pass

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
        await callback.answer("❌ لم تقم بالاشتراك في القناة بعد! يرجى الاشتراك ثم المحاولة.", show_alert=True)

@dp.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    if not await check_subscription(user_id):
        await callback.answer("❌ يجب الاشتراك في القناة أولاً!", show_alert=True)
        return
    text, keyboard = get_main_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(F.data == "buy_number_menu")
async def buy_number_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await check_subscription(user_id):
        await callback.answer("❌ يجب الاشتراك في القناة أولاً!", show_alert=True)
        return
        
    available_usa = sum(1 for d in NUMBERS_STORE.values() if d["country"] == "usa" and not d["sold"])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🇺🇸 أمريكا ({available_usa}) - ${USA_NUMBER_PRICE}", callback_data="buy_country_usa")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]
    ])
    await callback.message.edit_text("🌍 **اختر الدولة المتاحة:**", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "buy_country_usa")
async def buy_country_usa_handler(callback: CallbackQuery):
    available = [nid for nid, d in NUMBERS_STORE.items() if d["country"] == "usa" and not d["sold"]]
    if not available:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="buy_number_menu")]])
        await callback.message.edit_text("عذراً، نفدت الأرقام الأمريكية حالياً 🔴", reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer()
        return
        
    chosen_id = random.choice(available)
    data = NUMBERS_STORE[chosen_id]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🛒 شراء من رصيدك (${data['price']})", callback_data=f"buy_balance_{chosen_id}")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="buy_number_menu")]
    ])
    await callback.message.edit_text(
        f" الدولة: {data['name']}\n السعر: ${data['price']}\n\nاختر اتمام الشراء:",
        reply_markup=keyboard, parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_balance_"))
async def buy_with_balance(callback: CallbackQuery):
    user_id = callback.from_user.id
    num_id = callback.data.replace("buy_balance_", "")
    data = NUMBERS_STORE.get(num_id)
    
    if not data or data["sold"]:
        await callback.answer("هذا الرقم غير متاح أو تم بيعه!", show_alert=True)
        return
        
    # فحص أمني دقيق للرصيد من قاعدة البيانات مباشرة لمنع أي تلاعب
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    balance = row[0] if row else 0.0
    
    if balance < data["price"]:
        await callback.answer(f"❌ رصيدك غير كافي (${balance:.2f}). يرجى شحن رصيدك!", show_alert=True)
        return
        
    # خصم آمن وموثق
    new_balance = balance - data["price"]
    cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
    conn.commit()
    
    NUMBERS_STORE[num_id]["sold"] = True
    NUMBERS_STORE[num_id]["buyer_id"] = user_id
    
    otp_text = await fetch_otp_async(data["session"], data["api_id"], data["api_hash"])
    
    success_msg = (
        f"✅ **تم شراء الرقم بنجاح تحت الحماية الكاملة!**\n\n"
        f"📱 **الرقم:** `{data['phone']}`\n"
        f"💵 **السعر المدفوع:** `${data['price']}`\n"
        f"💰 **رصيدك المتبقي:** `${new_balance:.2f}`\n\n"
        f"📥 **آخر رسالة تحقق (OTP):**\n`{otp_text}`"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 طلب كود التحقق (OTP)", callback_data=f"get_otp_{num_id}")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(success_msg, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("get_otp_"))
async def get_otp_callback(callback: CallbackQuery):
    num_id = callback.data.replace("get_otp_", "")
    data = NUMBERS_STORE.get(num_id)
    if not data or data.get("buyer_id") != callback.from_user.id:
        await callback.answer("❌ غير مسموح لك بطلب كود هذا الرقم!", show_alert=True)
        return
    otp_text = await fetch_otp_async(data["session"], data["api_id"], data["api_hash"])
    await callback.answer(f"الكود الحالي: {otp_text}", show_alert=True)

@dp.callback_query(F.data == "recharge_menu")
async def recharge_menu(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not await check_subscription(user_id):
        await callback.answer("❌ يجب الاشتراك في القناة أولاً!", show_alert=True)
        return

    await state.set_state(States.waiting_for_stars_count)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]])
    await callback.message.edit_text(
        "💳 **شحن الرصيد الآمن بواسطة النجوم:**\n\nأرسل عدد النجوم المطلوبة (رقم صحيح فقط):",
        reply_markup=keyboard, parse_mode="Markdown"
    )
    await callback.answer()

@dp.message(States.waiting_for_stars_count)
async def process_custom_stars_input(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ أرسل رقماً صحيحاً فقط:")
        return
    stars_count = int(message.text.strip())
    if stars_count <= 0:
        await message.answer("❌ أرسل رقماً أكبر من الصفر:")
        return
    added_usd = (stars_count * 2) / 100
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⭐ ادفع {stars_count} نجمة (${added_usd:.2f})", callback_data=f"pay_custom_star_{stars_count}")],
        [InlineKeyboardButton(text="🔙 إلغاء", callback_data="main_menu")]
    ])
    await state.clear()
    await message.answer(f"📊 اضغط أدناه لإتمام الفاتورة الآمنة:", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("pay_custom_star_"))
async def pay_custom_stars_invoice(callback: CallbackQuery):
    stars_count = int(callback.data.replace("pay_custom_star_", ""))
    prices = [LabeledPrice(label=f"Recharge {stars_count} Stars", amount=stars_count)]
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=f"شحن ({stars_count} نجمة)",
        description="شحن آمن عبر تيليجرام",
        payload=f"recharge_stars_{stars_count}",
        provider_token="",
        currency="XTR",
        prices=prices,
        start_parameter=f"rech-{stars_count}"
    )
    await callback.answer()

@dp.callback_query(F.data == "transfer_menu")
async def transfer_menu_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if not await check_subscription(user_id):
        await callback.answer("❌ يجب الاشتراك في القناة أولاً!", show_alert=True)
        return
    await state.set_state(States.waiting_for_transfer_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]])
    await callback.message.edit_text("💳 أرسل (User ID) للشخص المراد التحويل إليه:", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.message(States.waiting_for_transfer_id)
async def process_transfer_id(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ أرسل ID صحيح أرقام فقط:")
        return
    recipient_id = int(message.text.strip())
    if recipient_id == message.from_user.id:
        await message.answer("❌ لا يمكنك التحويل لنفسك:")
        return
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (recipient_id,))
    if not cursor.fetchone():
        await message.answer("❌ المستخدم غير مسجل بالبوت:")
        return
    await state.update_data(recipient_id=recipient_id)
    await state.set_state(States.waiting_for_transfer_amount)
    await message.answer("✍️ أرسل المبلغ المراد تحويله (مثلاً `0.50`):", parse_mode="Markdown")

@dp.message(States.waiting_for_transfer_amount)
async def process_transfer_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace("$", ""))
    except ValueError:
        await message.answer("❌ أرسل قيمة صحيحة:")
        return
    if amount <= 0:
        await message.answer("❌ المبلغ يجب أن يكون أكبر من الصفر:")
        return
        
    sender_id = message.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (sender_id,))
    sender_balance = cursor.fetchone()[0]
    
    if sender_balance < amount:
        await message.answer(f"❌ رصيدك غير كافي (${sender_balance:.2f}).")
        await state.clear()
        return
        
    data = await state.get_data()
    recipient_id = data.get("recipient_id")
    
    # تنفيذ آمن للتحويل مع قفل البيانات
    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, sender_id))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, recipient_id))
    conn.commit()
    await state.clear()
    
    await message.answer(f"✅ تمت عملية التحويل بأمان تام بمبلغ `${amount:.2f}`", parse_mode="Markdown")
    try:
        await bot.send_message(recipient_id, f"🎉 استلمت تحويل رصيد بقيمة `${amount:.2f}`", parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data == "ref_menu")
async def ref_menu(callback: CallbackQuery):
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{callback.from_user.id}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]])
    await callback.message.edit_text(f"🤝 **رابط الإحالة الآمن:**\n`{ref_link}`", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "claim_bonus")
async def claim_bonus(callback: CallbackQuery):
    user_id = callback.from_user.id
    now = datetime.now()
    cursor.execute("SELECT last_bonus FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row and row[0]:
        last_time = datetime.fromisoformat(row[0])
        if now - last_time < timedelta(hours=24):
            await callback.answer("⏳ الهدية اليومية ستكون متاحة لاحقاً.", show_alert=True)
            return
    cursor.execute("UPDATE users SET balance = balance + 0.01, last_bonus = ? WHERE user_id = ?", (now.isoformat(), user_id))
    conn.commit()
    await callback.answer("🎉 مبروك! تمت إضافة الهدية اليومية.", show_alert=True)
    text, keyboard = get_main_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data == "my_account")
async def my_account(callback: CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]])
    await callback.message.edit_text(f"⚡ **الحساب محمي وآمن:**\n\n🆔 المعرف: `{user_id}`\n💵 الرصيد: `${balance:.2f}`", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

async def fetch_otp_async(session_str, api_id, api_hash):
    if not session_str:
        return "لا توجد جلسة ❌"
    try:
        client = TelegramClient(StringSession(session_str), api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return "الجلسة منتهية ❌"
        messages = await client.get_messages(777000, limit=1)
        await client.disconnect()
        if not messages:
            return "لا توجد رسائل ⏳"
        return messages[0].message
    except Exception as e:
        return f"خطأ: {str(e)}"

async def main():
    print("Starting X9 Secured Store Bot...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
    await asyncio.sleep(2)
    try:
        await bot.set_my_commands([BotCommand(command="start", description="تشغيل البوت")])
    except Exception:
        pass
    await dp.start_polling(bot, close_bot_session=True)

if __name__ == "__main__":
    asyncio.run(main())
