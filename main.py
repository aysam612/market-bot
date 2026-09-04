import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder

# إعدادات البوت والقناة
TOKEN = "YOUR_BOT_TOKEN_HERE"  # ضع توكن البوت هنا
CHANNEL_USERNAME = "@VPP8P"    # معرف قناتك الإجبارية

bot = Bot(token=TOKEN)
dp = Dispatcher()

# تعريف حالات الـ FSM لإدخال عدد النجوم المخصص
class RechargeState(StatesGroup):
    waiting_for_stars = State()

# إعداد قاعدة البيانات SQLite
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    last_bonus TEXT,
    referred_by INTEGER
)
""")
conn.commit()

# دالة التحقق من الاشتراك الإجباري
async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

# القائمة الرئيسية
def main_menu():
    keyboard = InlineKeyboardBuilder()
    keyboard.row(InlineKeyboardButton(text="🛒 شراء رقم (80 سنت / 40 نجمة)", callback_data="buy_number"))
    keyboard.row(InlineKeyboardButton(text="🎁 تجميع النقاط والهدية اليومية", callback_data="ref_menu"))
    keyboard.row(InlineKeyboardButton(text="⭐ شحن الرصيد بالنجوم", callback_data="recharge_menu"))
    return keyboard.as_markup()

# أمر البدء
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    args = message.text.split()
    
    cursor.execute("SELECT balance, last_bonus FROM users WHERE user_id = ?", (user_id,))
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
            
        cursor.execute("INSERT INTO users (user_id, balance, referred_by) VALUES (?, 0, ?)", (user_id, ref_id))
        conn.commit()
        
        if ref_id:
            cursor.execute("UPDATE users SET balance = balance + 1 WHERE user_id = ?", (ref_id,))
            conn.commit()
            try:
                await bot.send_message(ref_id, "🎉 مبروك! دخل شخص جديد عبر رابط إحالتك وحصلت على **1 سنت** إضافي!")
            except Exception:
                pass

    is_subbed = await check_subscription(user_id)
    if not is_subbed:
        sub_kb = InlineKeyboardBuilder()
        sub_kb.row(InlineKeyboardButton(text="📢 اشترك في القناة", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"))
        sub_kb.row(InlineKeyboardButton(text="✅ تحقق من الاشتراك", callback_data="check_sub"))
        await message.answer(
            f"⚠️ عذراً عزيزي، يجب عليك الاشتراك في قناة البوت أولاً لتتمكن من استخدامه:\n{CHANNEL_USERNAME}\n\nبعد الاشتراك اضغط على زر التحقق بالأسفل 👇",
            reply_markup=sub_kb.as_markup()
        )
        return

    await message.answer(
        "👋 أهلاً بك في **X9 Store** للأرقام والخدمات الرقمية!\n\n"
        "اختر ما يناسبك من القائمة أدناه 👇",
        reply_markup=main_menu()
    )

@dp.callback_query(F.data == "check_sub")
async def process_check_sub(callback: types.CallbackQuery):
    if await check_subscription(callback.from_user.id):
        await callback.message.delete()
        await callback.message.answer("✅ تم التحقق بنجاح! أهلاً بك:", reply_markup=main_menu())
    else:
        await callback.answer("❌ لم تقم بالاشتراك في القناة بعد!", show_alert=True)

@dp.callback_query(F.data == "ref_menu")
async def ref_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0]
    
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🎁 استلام الهدية اليومية (1 سنت)", callback_data="claim_bonus"))
    kb.row(InlineKeyboardButton(text="« عودة للقائمة الرئيسية", callback_data="main_menu"))
    
    text = (
        "🎁 **نظام تجميع النقاط والإحالات**\n\n"
        f"💰 رصيدك الحالي: **{balance} سنت**\n\n"
        "📌 **رابط الإحالة الخاص بك:**\n"
        f"`{ref_link}`\n\n"
        "🔗 قم بمشاركة الرابط مع أصدقائك. عن كل شخص يدخل البوت عبر رابطك، تحصل فوراً على **1 سنت**!\n"
        "⏰ وتحصل على **1 سنت** مجاني يومياً من زر الهدية بالأسفل."
    )
    await callback.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "claim_bonus")
async def claim_bonus(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    now = datetime.now()
    
    cursor.execute("SELECT last_bonus FROM users WHERE user_id = ?", (user_id,))
    last_bonus_str = cursor.fetchone()[0]
    
    if last_bonus_str:
        last_bonus_time = datetime.fromisoformat(last_bonus_str)
        if now - last_bonus_time < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last_bonus_time)
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            await callback.answer(f"⏳ لقد استلمت هديتك اليومية مسبقاً. يمكنك الاستلام بعد: {hours} ساعة و {minutes} دقيقة.", show_alert=True)
            return

    cursor.execute("UPDATE users SET balance = balance + 1, last_bonus = ? WHERE user_id = ?", (now.isoformat(), user_id))
    conn.commit()
    
    await callback.answer("🎉 مبروك! تم إضافة 1 سنت إلى رصيدك بنجاح.", show_alert=True)
    await ref_menu(callback)

# طلب شحن الرصيد المخصص (تفعيل حالة FSM)
@dp.callback_query(F.data == "recharge_menu")
async def recharge_menu(callback: types.CallbackQuery, state: FSMContext):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="« عودة للقائمة الرئيسية", callback_data="main_menu"))
    
    await state.set_state(RechargeState.waiting_for_stars)
    await callback.message.edit_text(
        "⭐ **شحن الرصيد المخصص بالنجوم (XTR)**\n\n"
        "القاعدة: **كل نجمة واحدة = 2 سنت** (حتى لو أردت شحن 1، 5، 100، أو 1000 نجمة!)\n\n"
        "✍️ **الآن، أرسل في المحادثة عدد النجوم التي تريد شحنها:**\n(مثلاً اكتب: `5` أو `50` أو `1000`)",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

# استقبال عدد النجوم المكتوب من المستخدم
@dp.message(RechargeState.waiting_for_stars)
async def process_custom_stars(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ خطأ! يرجى إرسال رقم صحيح فقط (مثلاً: 10 أو 50).")
        return
    
    stars_count = int(message.text)
    if stars_count <= 0:
        await message.answer("❌ يجب أن يكون عدد النجوم أكبر من صفر.")
        return
    
    cents_gained = stars_count * 2
    await state.clear()
    
    # إرسال الفاتورة بالعدد المخصص الذي طلبه المستخدم
    title = f"شحن {cents_gained} سنت"
    description = f"إضافة {cents_gained} سنت إلى رصيدك الداخلي مقابل {stars_count} نجمة"
    payload = f"recharge_custom_{stars_count}"
    prices = [LabeledPrice(label="XTR", amount=stars_count)]

    await bot.send_invoice(
        chat_id=message.from_user.id,
        title=title,
        description=description,
        payload=payload,
        currency="XTR",
        prices=prices
    )

@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("👋 أهلاً بك مجدداً في القائمة الرئيسية:", reply_markup=main_menu())

@dp.callback_query(F.data == "buy_number")
async def buy_number_options(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🛒 شراء بالسنتات (80 سنت)", callback_data="buy_with_balance"))
    kb.row(InlineKeyboardButton(text="⭐ شراء بالنجوم الفورية (40 نجمة)", callback_data="buy_with_stars"))
    kb.row(InlineKeyboardButton(text="« عودة للقائمة الرئيسية", callback_data="main_menu"))
    
    await callback.message.edit_text(
        "🛍️ **شراء رقم جديد**\n\n"
        "سعر الرقم: **80 سنت** أو **40 نجمة تليجرام**.\n"
        "اختر طريقة الدفع التي تفضلها:",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "buy_with_balance")
async def buy_with_balance(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0]
    
    if balance < 80:
        await callback.answer(f"❌ رصيدك الحالي ({balance} سنت) لا يكفي لشراء رقم. يلزمك 80 سنت على الأقل. اجمع النقاط أو اشحن بالنجوم!", show_alert=True)
        return
    
    cursor.execute("UPDATE users SET balance = balance - 80 WHERE user_id = ?", (user_id,))
    conn.commit()
    
    await callback.message.edit_text(
        "✅ **تمت عملية الشراء بنجاح!**\n\n"
        "🇺🇸 رقمك الأمريكي/العالمي:\n"
        "`+1 (555) 019-8234`\n"
        "🔑 كود التحقق (OTP): وصلك بنجاح.\n\n"
        "شكراً لاستخدامك متجرنا!",
        reply_markup=InlineKeyboardBuilder().add(InlineKeyboardButton(text="« عودة للقائمة", callback_data="main_menu")).as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "buy_with_stars")
async def process_stars_payment(callback: types.CallbackQuery):
    title = "شراء رقم مميز"
    description = "الحصول على رقم فوري مع كود الـ OTP"
    payload = "buy_number_xtr"
    prices = [LabeledPrice(label="XTR", amount=40)]

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=title,
        description=description,
        payload=payload,
        currency="XTR",
        prices=prices
    )
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# معالجة نجاح الدفع (سواء شراء رقم أو شحن عدد مخصص من النجوم)
@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    payment_info = message.successful_payment
    payload = payment_info.invoice_payload
    user_id = message.from_user.id
    
    if payload == "buy_number_xtr":
        await message.answer(
            "✅ **تم الدفع بنجاح عبر نجوم تليجرام!**\n\n"
            "🇺🇸 رقمك الجديد:\n"
            "`+1 (555) 892-3311`\n"
            "استمتع بخدمتك!",
            reply_markup=main_menu(),
            parse_mode="Markdown"
        )
    elif payload.startswith("recharge_custom_"):
        try:
            stars_count = int(payload.replace("recharge_custom_", ""))
            cents_gained = stars_count * 2
            
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (cents_gained, user_id))
            conn.commit()
            
            await message.answer(
                f"⭐ تم شحن رصيدك بنجاح بـ **{cents_gained} سنت** (مقابل {stars_count} نجمة)!",
                reply_markup=main_menu(),
                parse_mode="Markdown"
            )
        except Exception:
            pass

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

