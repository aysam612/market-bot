import os
import random
import asyncio
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, 
    LabeledPrice
)
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from telethon import TelegramClient
from telethon.sessions import StringSession

# ================= إعدادات البوت =================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8526493972:AAEVb5f6rIcPCqMu1wVvEKop3QXvSih9YaE")
CHANNEL_URL = "https://t.me/VPP8P"  # قناة التفعيلات
ADMIN_USERNAME = "@diddy0"

# سعر النجمة الواحدة بالدولار (2 سنت)
STAR_PRICE_USD = 0.02
# سعر الرقم الأمريكي (80 سنت)
USA_NUMBER_PRICE = 0.80

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================= قاعدة البيانات =================
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

# ================= مستودع الأرقام (الأرقام الأمريكية الحقيقية بسعر 80 سنت) =================
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

def usd_to_stars(usd_amount):
    # كل نجمة = 2 سنت (0.02 دولار)
    return max(1, round(usd_amount / STAR_PRICE_USD))

# ================= القائمة الرئيسية =================
def get_main_keyboard(user_id):
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    balance = row[0] if row else 0.0
    
    text_header = (
        "👋 أهلاً بك عزيزي في متجر X9 للأرقام المميزة 🌐!\n\n"
        "• احصل على أرقام أمريكية مميزة ومفعلة لجميع الاستخدامات.\n"
        "• الشراء فوري وعشوائي وسريع عبر نجوم تليجرام (Stars ⭐).\n"
        "• إمكانية طلب كود التحقق (OTP) بشكل فوري وبكل سهولة بعد الشراء.\n\n"
        f"🆔 `{user_id}`\n"
        f"💵 `${balance:.2f}`\n\n"
        "اختر ما يناسبك من القائمة 👇"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 شراء أرقام", callback_data="buy_number_menu")],
        [InlineKeyboardButton(text="⚡ حسابي", callback_data="my_account"), InlineKeyboardButton(text="🎁 هدية يومية", callback_data="claim_bonus")],
        [InlineKeyboardButton(text="💳 شحن رصيد", callback_data="recharge_menu")],
        [InlineKeyboardButton(text="🤝 دعوة صديق", callback_data="ref_menu"), InlineKeyboardButton(text="💳 تحويل رصيد", callback_data="transfer_menu")],
        [InlineKeyboardButton(text="🔥 التفعيلات", url=CHANNEL_URL)],
        [InlineKeyboardButton(text="💬 الدعم الفني", url=f"https://t.me/{ADMIN_USERNAME.replace('@','')}")]
    ])
    return text_header, keyboard

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
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
            # إعطاء الصديق 1 سنت عند الدخول عبر الرابط
            cursor.execute("UPDATE users SET balance = balance + 0.01 WHERE user_id = ?", (ref_id,))
            conn.commit()
            try:
                await bot.send_message(ref_id, "🎉 مبروك! دخل شخص جديد عبر رابط إحالتك وتمت إضافة 1 سنت برصيدك!", parse_mode="Markdown")
            except Exception:
                pass

    text, keyboard = get_main_keyboard(user_id)
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    text, keyboard = get_main_keyboard(user_id)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "buy_number_menu")
async def buy_number_menu(callback: CallbackQuery):
    available_usa = sum(1 for d in NUMBERS_STORE.values() if d["country"] == "usa" and not d["sold"])
    stars_needed = usd_to_stars(USA_NUMBER_PRICE)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🇺🇸 أمريكا ({available_usa}) - ${USA_NUMBER_PRICE} ({stars_needed} نجمة)", callback_data="buy_country_usa")],
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
    stars_count = usd_to_stars(data['price'])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⭐ شراء بالنجوم ({stars_count} نجمة - كل نجمة بـ 2 سنت)", callback_data=f"pay_star_{chosen_id}")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="buy_number_menu")]
    ])
    
    await callback.message.edit_text(
        f" الدولة: {data['name']}\n"
        f" السعر: ${data['price']} (تعادل {stars_count} نجمة، حيث كل نجمة = 2 سنت)\n\n"
        f"اختر الدفع عبر نجوم تليجرام:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_star_"))
async def pay_with_stars(callback: CallbackQuery):
    num_id = callback.data.replace("pay_star_", "")
    data = NUMBERS_STORE.get(num_id)
    
    if not data or data["sold"]:
        await callback.answer("هذا الرقم غير متاح!", show_alert=True)
        return
        
    stars_count = usd_to_stars(data['price'])
    prices = [LabeledPrice(label="USA Number Stars", amount=stars_count)]
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="شراء رقم أمريكي",
        description=f"شراء رقم أمريكي مقابل {stars_count} نجمة (كل نجمة = 2 سنت)",
        payload=f"buy_usa_star_{num_id}",
        provider_token="",
        currency="XTR",
        prices=prices,
        start_parameter=f"buy-{num_id}"
    )
    await callback.answer()

@dp.callback_query(F.data == "recharge_menu")
async def recharge_menu(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ شحن الرصيد بالنجوم (كل نجمة = 2 سنت)", callback_data="rech_stars_info")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]
    ])
    await callback.message.edit_text("💳 **شحن الرصيد:**\n\nنظام الشحن مخصص عبر نجوم تليجرام (Stars) حيث **كل نجمة = 2 سنت**.", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "rech_stars_info")
async def rech_stars_info(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ شحن 7 نجوم (تساوي 14 سنت)", callback_data="pay_custom_star_7")],
        [InlineKeyboardButton(text="⭐ شحن 40 نجمة (تساوي 80 سنت)", callback_data="pay_custom_star_40")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="recharge_menu")]
    ])
    await callback.message.edit_text("⭐ **اختر باقة شحن النجوم المناسبة لك:**\n(ملاحظة: سعر النجمة الواحدة هو 2 سنت)", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_custom_star_"))
async def pay_custom_stars(callback: CallbackQuery):
    stars_count = int(callback.data.replace("pay_custom_star_", ""))
    total_cents = stars_count * 2
    
    prices = [LabeledPrice(label=f"Recharge {stars_count} Stars", amount=stars_count)]
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=f"شحن رصيد ({stars_count} نجمة)",
        description=f"شحن رصيد بقيمة {total_cents} سنت (كل نجمة = 2 سنت)",
        payload=f"recharge_stars_{stars_count}",
        provider_token="",
        currency="XTR",
        prices=prices,
        start_parameter=f"rech-{stars_count}"
    )
    await callback.answer()

@dp.callback_query(F.data == "ref_menu")
async def ref_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]])
    await callback.message.edit_text(
        f"🤝 **نظام دعوة الأصدقاء:**\n\nشارك الرابط الخاص بك واكسب رصيداً (يحصل صديقك على 1 سنت عند الدخول):\n`{ref_link}`",
        reply_markup=keyboard, parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "claim_bonus")
async def claim_bonus(callback: CallbackQuery):
    user_id = callback.from_user.id
    now = datetime.now()
    
    cursor.execute("SELECT last_bonus FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    last_bonus_str = row[0] if row else None
    
    if last_bonus_str:
        last_time = datetime.fromisoformat(last_bonus_str)
        if now - last_time < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last_time)
            hours, rem = divmod(int(remaining.total_seconds()), 3600)
            minutes, _ = divmod(rem, 60)
            await callback.answer(f"⏳ الهدية متاحة بعد {hours} ساعة و {minutes} دقيقة.", show_alert=True)
            return

    # الهدية اليومية أصبحت 1 سنت
    cursor.execute("UPDATE users SET balance = balance + 0.01, last_bonus = ? WHERE user_id = ?", (now.isoformat(), user_id))
    conn.commit()
    await callback.answer("🎉 مبروك! تمت إضافة الهدية اليومية (1 سنت) برصيدك.", show_alert=True)
    
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
    await callback.message.edit_text(f"⚡ **معلومات الحساب:**\n\n🆔 المعرف: `{user_id}`\n💵 الرصيد: `${balance:.2f}`", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

async def main():
    print("Starting X9 Store Bot (Custom Stars & 80 Cents USA)...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
