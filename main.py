import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder

# إعدادات البوت والقناة
TOKEN = "YOUR_BOT_TOKEN_HERE"  # ضع توكن البوت هنا
CHANNEL_USERNAME = "@VPP8P"    # معرف قناتك الإجبارية

bot = Bot(token=TOKEN)
dp = Dispatcher()

# إعداد قاعدة البيانات SQLite
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

# إنشاء الجدول إذا لم يكن موجوداً
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

# أمر البدء (مع دعم الإحالات والاشتراك الإجباري)
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split()
    
    # التحقق من قاعدة البيانات وتسجيل المستخدم إن لم يكن موجوداً
    cursor.execute("SELECT balance, last_bonus FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        # فحص وجود كود إحالة في الرابط
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
        
        # إذا دخل عبر إحالة صحيحة، نعطي صاحب الرابط 1 سنت
        if ref_id:
            cursor.execute("UPDATE users SET balance = balance + 1 WHERE user_id = ?", (ref_id,))
            conn.commit()
            try:
                await bot.send_message(ref_id, "🎉 مبروك! دخل شخص جديد عبر رابط إحالتك وحصلت على **1 سنت** إضافي!")
            except Exception:
                pass

    # التحقق من الاشتراك الإجباري في القناة
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

# زر التحقق من الاشتراك
@dp.callback_query(F.data == "check_sub")
async def process_check_sub(callback: types.CallbackQuery):
    if await check_subscription(callback.from_user.id):
        await callback.message.delete()
        await callback.message.answer("✅ تم التحقق بنجاح! أهلاً بك:", reply_markup=main_menu())
    else:
        await callback.answer("❌ لم تقم بالاشتراك في القناة بعد!", show_alert=True)

# قائمة الإحالات والهدية اليومية
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

# استلام الهدية اليومية (كل 24 ساعة)
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

    # تحديث الرصيد ووقت الهدية
    cursor.execute("UPDATE users SET balance = balance + 1, last_bonus = ? WHERE user_id = ?", (now.isoformat(), user_id))
    conn.commit()
    
    await callback.answer("🎉 مبروك! تم إضافة 1 سنت إلى رصيدك بنجاح.", show_alert=True)
    await ref_menu(callback)

# قائمة شحن الرصيد المرنة (كل نجمة = 2 سنت، تبدأ من نجمة واحدة)
@dp.callback_query(F.data == "recharge_menu")
async def recharge_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⭐ شحن 1 نجمة = 2 سنت", callback_data="pay_stars_1"))
    kb.row(InlineKeyboardButton(text="⭐ شحن 5 نجوم = 10 سنت", callback_data="pay_stars_5"))
    kb.row(InlineKeyboardButton(text="⭐ شحن 10 نجوم = 20 سنت", callback_data="pay_stars_10"))
    kb.row(InlineKeyboardButton(text="⭐ شحن 25 نجمة = 50 سنت", callback_data="pay_stars_25"))
    kb.row(InlineKeyboardButton(text="« عودة للقائمة الرئيسية", callback_data="main_menu"))
    
    await callback.message.edit_text(
        "⭐ **شحن الرصيد الداخلي بالنجوم (XTR)**\n\n"
        "الحسبة المرنة: **كل نجمة واحدة = 2 سنت**!\n"
        "اختر عدد النجوم التي تريد دفعها ليتم إضافتها فوراً لرصيدك الداخلي:",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

# العودة للقائمة الرئيسية عبر الأزرار
@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text("👋 أهلاً بك مجدداً في القائمة الرئيسية:", reply_markup=main_menu())

# شراء رقم
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

# الشراء باستخدام الرصيد الداخلي (السنتات)
@dp.callback_query(F.data == "buy_with_balance")
async def buy_with_balance(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0]
    
    if balance < 80:
        await callback.answer(f"❌ رصيدك الحالي ({balance} سنت) لا يكفي لشراء رقم. يلزمك 80 سنت على الأقل. اجمع النقاط عبر الإحالات أو اشحن بالنجوم!", show_alert=True)
        return
    
    # خصم الرصيد وإتمام الطلب
    cursor.execute("UPDATE users SET balance = balance - 80 WHERE user_id = ?", (user_id,))
    conn.commit()
    
    # هنا تضع كود تسليم الرقم الفعلي للمستخدم
    await callback.message.edit_text(
        "✅ **تمت عملية الشراء بنجاح!**\n\n"
        "🇺🇸 رقمك الأمريكي/العالمي:\n"
        "`+1 (555) 019-8234`\n"
        "🔑 كود التحقق (OTP): سيظهر هنا أو وصلك عبر النظام.\n\n"
        "شكراً لاستخدامك متجرنا!",
        reply_markup=InlineKeyboardBuilder().add(InlineKeyboardButton(text="« عودة للقائمة", callback_data="main_menu")).as_markup(),
        parse_mode="Markdown"
    )

# معالجة فواتير نجوم تليجرام والشحن المرن
@dp.callback_query(F.data.in_(["buy_with_stars", "pay_stars_1", "pay_stars_5", "pay_stars_10", "pay_stars_25"]))
async def process_stars_payment(callback: types.CallbackQuery):
    if callback.data == "buy_with_stars":
        title = "شراء رقم مميز"
        description = "الحصول على رقم فوري مع كود الـ OTP"
        payload = "buy_number_xtr"
        prices = [LabeledPrice(label="XTR", amount=40)] # 40 نجمة = 80 سنت
    elif callback.data == "pay_stars_1":
        title = "شحن 2 سنت"
        description = "إضافة 2 سنت لرصيدك الداخلي (مقابل 1 نجمة)"
        payload = "recharge_1"
        prices = [LabeledPrice(label="XTR", amount=1)]
    elif callback.data == "pay_stars_5":
        title = "شحن 10 سنت"
        description = "إضافة 10 سنت لرصيدك الداخلي (مقابل 5 نجوم)"
        payload = "recharge_5"
        prices = [LabeledPrice(label="XTR", amount=5)]
    elif callback.data == "pay_stars_10":
        title = "شحن 20 سنت"
        description = "إضافة 20 سنت لرصيدك الداخلي (مقابل 10 نجوم)"
        payload = "recharge_10"
        prices = [LabeledPrice(label="XTR", amount=10)]
    else:
        title = "شحن 50 سنت"
        description = "إضافة 50 سنت لرصيدك الداخلي (مقابل 25 نجمة)"
        payload = "recharge_25"
        prices = [LabeledPrice(label="XTR", amount=25)]

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=title,
        description=description,
        payload=payload,
        currency="XTR",
        prices=prices
    )
    await callback.answer()

# معالجة تفاصيل الدفع المسبق (Pre-checkout)
@dp.pre_checkout_query()
async def pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# تأكيد نجاح الدفع بالنجوم وإضافة الرصيد أو الخدمة
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
    elif payload == "recharge_1":
        cursor.execute("UPDATE users SET balance = balance + 2 WHERE user_id = ?", (user_id,))
        conn.commit()
        await message.answer("⭐ تم شحن رصيدك بنجاح بـ **2 سنت**!", reply_markup=main_menu(), parse_mode="Markdown")
    elif payload == "recharge_5":
        cursor.execute("UPDATE users SET balance = balance + 10 WHERE user_id = ?", (user_id,))
        conn.commit()
        await message.answer("⭐ تم شحن رصيدك بنجاح بـ **10 سنت**!", reply_markup=main_menu(), parse_mode="Markdown")
    elif payload == "recharge_10":
        cursor.execute("UPDATE users SET balance = balance + 20 WHERE user_id = ?", (user_id,))
        conn.commit()
        await message.answer("⭐ تم شحن رصيدك بنجاح بـ **20 سنت**!", reply_markup=main_menu(), parse_mode="Markdown")
    elif payload == "recharge_25":
        cursor.execute("UPDATE users SET balance = balance + 50 WHERE user_id = ?", (user_id,))
        conn.commit()
        await message.answer("⭐ تم شحن رصيدك بنجاح بـ **50 سنت**!", reply_markup=main_menu(), parse_mode="Markdown")

# تشغيل البوت
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
