import os
import re
import asyncio
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
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

# =====================================================================
# 🛠️ [الإعدادات الأساسية]
# =====================================================================

BOT_TOKEN = "8896024185:AAF911IAOlt_2BS8HXXVaf8Zrxz3y9MKgkY"

DEFAULT_API_ID = 1234567       # استبدلها برقم الـ API ID الخاص بك من my.telegram.org
DEFAULT_API_HASH = "your_api_hash_here"  # استبدلها بالـ API Hash الخاص بك

DEFAULT_ADMIN_USERNAME = "aaysam"
DEFAULT_ADMIN_USER_ID = 8863784148

REQUIRED_CHANNEL = "VPP8P"
BONUS_AMOUNT = 0.01

TEXTS = {
    "welcome_ar": "👋 أهلاً بك عزيزي في متجر X9 للأرقام المميزة 🌐!\n\n🆔 معرفك: `{user_id}`\n💵 رصيدك: `${balance:.2f}`\n\nاختر ما يناسبك من القائمة أدناه 👇",
    "welcome_en": "👋 Welcome to X9 Store for Premium Numbers 🌐!\n\n🆔 ID: `{user_id}`\n💵 Balance: `${balance:.2f}`\n\nChoose what you want from the menu below 👇",
    "support_username": "aaysam"
}

CUSTOM_BUTTONS = [
    {"name": "💬 قناة التليجرام", "url": "https://t.me/VPP8P"},
    {"name": "🔥 جروب الدعم", "url": "https://t.me/aaysam"}
]

CONFIG_DATA = {
    "star_price": 0.01
}

# =====================================================================
# 🚀 [تهيئة البوت والحالات]
# =====================================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

MEMORY_USERS = {
    DEFAULT_ADMIN_USER_ID: {"user_id": DEFAULT_ADMIN_USER_ID, "balance": 10000.0, "language": "ar", "banned": False}
}
MEMORY_NUMBERS = []
MEMORY_PURCHASES = []

class States(StatesGroup):
    waiting_for_stars_count = State()
    waiting_for_transfer_id = State()
    waiting_for_transfer_amount = State()
    
    waiting_for_auto_num_id = State()
    waiting_for_auto_num_name = State()
    waiting_for_auto_num_price = State()
    waiting_for_auto_phone = State()
    waiting_for_auto_code = State()
    waiting_for_auto_password = State()

    waiting_for_star_price = State()
    waiting_for_ban_id = State()
    waiting_for_unban_id = State()
    
    waiting_for_broadcast_msg = State()
    waiting_for_add_balance_id = State()
    waiting_for_add_balance_amount = State()
    waiting_for_deduct_balance_id = State()
    waiting_for_deduct_balance_amount = State()
    waiting_for_set_balance_id = State()
    waiting_for_set_balance_amount = State()
    waiting_for_check_user_id = State()

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

async def get_main_keyboard(user_id):
    user = MEMORY_USERS.get(user_id, {})
    balance = user.get("balance", 0.0)
    lang = user.get("language", "ar")
    
    keyboard_buttons = [
        [InlineKeyboardButton(text="🛒 Buy Numbers Store" if lang == 'en' else "🛒 متجر الأرقام", callback_data="buy_number_menu")],
        [InlineKeyboardButton(text="⚡ My Account" if lang == 'en' else "⚡ حسابي", callback_data="my_account"), InlineKeyboardButton(text="🎁 Daily Bonus" if lang == 'en' else "🎁 هدية يومية ($0.01)", callback_data="claim_bonus")],
        [InlineKeyboardButton(text="💳 Recharge Stars" if lang == 'en' else "💳 شحن رصيد نجوم", callback_data="recharge_menu")],
        [InlineKeyboardButton(text="🤝 Ref Link" if lang == 'en' else "🤝 رابط إحالة", callback_data="ref_menu"), InlineKeyboardButton(text="💳 Transfer" if lang == 'en' else "💳 تحويل رصيد", callback_data="transfer_menu")],
    ]
    
    for btn in CUSTOM_BUTTONS:
        keyboard_buttons.append([InlineKeyboardButton(text=btn["name"], url=btn["url"])])
        
    keyboard_buttons.append([InlineKeyboardButton(text="🌐 English" if lang == 'ar' else "🌐 العربية", callback_data="toggle_lang")])
    
    if user_id == DEFAULT_ADMIN_USER_ID:
        keyboard_buttons.append([InlineKeyboardButton(text="🛠 لوحة التحكم الشاملة (Admin Panel)", callback_data="admin_panel_main")])
        
    keyboard_buttons.append([InlineKeyboardButton(text="💬 Support" if lang == 'en' else "💬 الدعم الفني", url=f"https://t.me/{TEXTS['support_username'].replace('@', '')}")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    if lang == 'en':
        text_header = TEXTS["welcome_en"].format(user_id=user_id, balance=balance)
    else:
        text_header = TEXTS["welcome_ar"].format(user_id=user_id, balance=balance)
        
    return text_header, keyboard

@dp.callback_query(F.data == "toggle_lang")
async def toggle_lang_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in MEMORY_USERS:
        MEMORY_USERS[user_id] = {"user_id": user_id, "balance": 0.0, "language": "ar", "banned": False}
    current_lang = MEMORY_USERS[user_id].get("language", "ar")
    new_lang = 'en' if current_lang == 'ar' else 'ar'
    MEMORY_USERS[user_id]["language"] = new_lang
    text, keyboard = await get_main_keyboard(user_id)
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
    
    user_doc = MEMORY_USERS.get(user_id)
    if user_doc and user_doc.get("banned", False):
        await message.answer("❌ عذراً، لقد تم حظرك من استخدام هذا البوت.")
        return

    args = message.text.split()
    referred_by = int(args[1].replace("ref_", "")) if len(args) > 1 and args[1].startswith("ref_") and args[1].replace("ref_", "").isdigit() else None
    if referred_by == user_id:
        referred_by = None

    if not await check_subscription(user_id):
        sub_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 اشترك في القناة", url=f"https://t.me/{REQUIRED_CHANNEL}")],
            [InlineKeyboardButton(text="🔄 تحقق من الاشتراك", callback_data="check_sub")]
        ])
        await message.answer(f"⚠️ يجب عليك الاشتراك في القناة أولاً: @{REQUIRED_CHANNEL}", reply_markup=sub_keyboard)
        return

    if not user_doc:
        initial_balance = 10000.0 if user_id == DEFAULT_ADMIN_USER_ID else 0.0
        MEMORY_USERS[user_id] = {
            "user_id": user_id,
            "balance": initial_balance,
            "referred_by": referred_by,
            "language": "ar",
            "banned": False
        }
        if referred_by and user_id != DEFAULT_ADMIN_USER_ID and referred_by in MEMORY_USERS:
            MEMORY_USERS[referred_by]["balance"] += BONUS_AMOUNT

    text, keyboard = await get_main_keyboard(user_id)
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_doc = MEMORY_USERS.get(user_id)
    if user_doc and user_doc.get("banned", False):
        await callback.answer("❌ أنت محظور من استخدام البوت.", show_alert=True)
        return

    if await check_subscription(user_id):
        try:
            await callback.message.delete()
        except Exception:
            pass
        if not user_doc:
            initial_balance = 10000.0 if user_id == DEFAULT_ADMIN_USER_ID else 0.0
            MEMORY_USERS[user_id] = {"user_id": user_id, "balance": initial_balance, "language": "ar", "banned": False}
        text, keyboard = await get_main_keyboard(user_id)
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await callback.answer("❌ لم تقم بالاشتراك في القناة بعد!", show_alert=True)

@dp.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    user_doc = MEMORY_USERS.get(user_id, {})
    if user_doc.get("banned", False):
        await callback.answer("❌ أنت محظور.", show_alert=True)
        return
    text, keyboard = await get_main_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass
    await callback.answer()

# =====================================================================
# 👑 [لوحة التحكم والخدمات الإضافية]
# =====================================================================

@dp.callback_query(F.data == "admin_panel_main")
@dp.message(Command("admin"))
async def admin_panel_handler(event, state: FSMContext = None):
    if state:
        await state.clear()
    user_id = event.from_user.id
    message = event.message if isinstance(event, CallbackQuery) else event
        
    if user_id != DEFAULT_ADMIN_USER_ID:
        if isinstance(event, CallbackQuery):
            await event.answer("عذراً، هذه اللوحة مخصصة لمالك البوت فقط! ❌", show_alert=True)
        else:
            await message.answer("عذراً، هذه اللوحة مخصصة لمالك البوت فقط! ❌")
        return
        
    current_star_price = CONFIG_DATA.get("star_price", 0.01)

    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ إضافة رقم تليجرام جديد", callback_data="admin_auto_add_num")],
        [InlineKeyboardButton(text="✏️ إدارة الأرقام الحالية", callback_data="admin_manage_nums")],
        [InlineKeyboardButton(text="👥 إحصائيات البوت والمستخدمين", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 إذاعة رسالة للجميع", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="➕ إضافة رصيد لمستخدم", callback_data="admin_add_balance"), InlineKeyboardButton(text="➖ خصم رصيد من مستخدم", callback_data="admin_deduct_balance")],
        [InlineKeyboardButton(text="🎯 تعيين رصيد محدد", callback_data="admin_set_balance"), InlineKeyboardButton(text="🔍 الاستعلام عن مستخدم", callback_data="admin_check_user")],
        [InlineKeyboardButton(text=f"⭐ تعديل سعر النجمة ({current_star_price})", callback_data="admin_change_star_price")],
        [InlineKeyboardButton(text="🚫 حظر مستخدم", callback_data="admin_ban_user"), InlineKeyboardButton(text="✅ رفع حظر", callback_data="admin_unban_user")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])
    
    text = (
        f"🛠 **لوحة التحكم الشاملة والمتقدمة:**\n"
        f"👤 المالك: `{DEFAULT_ADMIN_USERNAME}` (`{DEFAULT_ADMIN_USER_ID}`)\n\n"
        f"اختر العملية التي تريد تنفيذها من القائمة أدناه:"
    )
    
    if isinstance(event, CallbackQuery):
        await message.edit_text(text, reply_markup=builder, parse_mode="Markdown")
        await event.answer()
    else:
        await message.answer(text, reply_markup=builder, parse_mode="Markdown")

@dp.callback_query(F.data == "my_account")
async def my_account_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = MEMORY_USERS.get(user_id, {})
    balance = user.get("balance", 0.0)
    purchased_count = sum(1 for p in MEMORY_PURCHASES if p["user_id"] == user_id)
    
    text = (
        f"⚡ **معلومات حسابك:**\n\n"
        f"🆔 المعرف: `{user_id}`\n"
        f"💵 الرصيد الحالي: `${balance:.2f}`\n"
        f"🛒 عدد الأرقام المشتراة: `{purchased_count}`"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "claim_bonus")
async def claim_bonus_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = MEMORY_USERS.get(user_id)
    if not user:
        await callback.answer("❌ حدث خطأ، أرسل /start", show_alert=True)
        return
        
    now = datetime.now()
    last_claim = user.get("last_claim")
    if last_claim and (now - last_claim) < timedelta(hours=24):
        remaining = timedelta(hours=24) - (now - last_claim)
        hours, remainder = divmod(int(remaining.total_seconds()), 3600)
        minutes = remainder // 60
        await callback.answer(f"⏳ لقد حصلت على الهدية مسبقاً. انتظر {hours} ساعة و {minutes} دقيقة.", show_alert=True)
        return

    user["balance"] += 0.01
    user["last_claim"] = now
    await callback.answer("🎁 مبروك! حصلت على هدية بقيمة $0.01 بنجاح.", show_alert=True)
    text, keyboard = await get_main_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data == "ref_menu")
async def ref_menu_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    text = (
        f"🤝 **نظام الإحالة والأصدقاء:**\n\n"
        f"شارك رابطك مع أصدقائك واحصل على `{BONUS_AMOUNT}$` لكل شخص يدخل عن طريقك!\n\n"
        f"🔗 رابطك الخاص:\n`{ref_link}`"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "transfer_menu")
async def transfer_menu_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(States.waiting_for_transfer_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]
    ])
    await callback.message.edit_text("💳 أرسل آي دي (ID) المستخدم الذي تريد التحويل إليه:", reply_markup=keyboard)
    await callback.answer()

@dp.message(States.waiting_for_transfer_id)
async def process_transfer_id(message: Message, state: FSMContext):
    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ يرجى إرسال رقم آي دي (ID) صحيح:")
        return
        
    if target_id not in MEMORY_USERS:
        await message.answer("❌ هذا المستخدم غير مسجل في البوت:")
        return
    if target_id == message.from_user.id:
        await message.answer("❌ لا يمكنك التحويل لنفسك:")
        return
        
    await state.update_data(transfer_id=target_id)
    await state.set_state(States.waiting_for_transfer_amount)
    await message.answer("💵 أرسل المبلغ المراد تحويله بالدولار (مثال: `1.00`):")

@dp.message(States.waiting_for_transfer_amount)
async def process_transfer_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace("$", ""))
    except ValueError:
        await message.answer("❌ أدخل رقماً صحيحاً للمبلغ:")
        return
        
    if amount <= 0:
        await message.answer("❌ المبلغ يجب أن يكون أكبر من صفر:")
        return
        
    sender_id = message.from_user.id
    sender_balance = MEMORY_USERS.get(sender_id, {}).get("balance", 0.0)
    if sender_balance < amount:
        await message.answer("❌ رصيدك غير كافي لإتمام عملية التحويل هذه.")
        await state.clear()
        return
        
    data = await state.get_data()
    target_id = data["transfer_id"]
    
    MEMORY_USERS[sender_id]["balance"] -= amount
    MEMORY_USERS[target_id]["balance"] += amount
    await state.clear()
    
    await message.answer(f"✅ تم تحويل مبلغ `${amount:.2f}` بنجاح إلى المستخدم (`{target_id}`)!")
    try:
        await bot.send_message(target_id, f"💰 وصلك تحويل برصيد `${amount:.2f}` من المستخدم (`{sender_id}`).")
    except Exception:
        pass

@dp.callback_query(F.data == "recharge_menu")
async def recharge_menu_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(States.waiting_for_stars_count)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]
    ])
    await callback.message.edit_text("⭐ أرسل عدد النجوم التي تريد شحنها (مثال: `10`):", reply_markup=keyboard)
    await callback.answer()

@dp.message(States.waiting_for_stars_count)
async def process_stars_invoice(message: Message, state: FSMContext):
    try:
        count = int(message.text.strip())
    except ValueError:
        await message.answer("❌ أدخل رقماً صحيحاً لعدد النجوم:")
        return
    if count <= 0:
        await message.answer("❌ العدد يجب أن يكون أكبر من صفر:")
        return
        
    await state.clear()
    star_price = CONFIG_DATA.get("star_price", 0.01)
    total_price_cents = int(count * star_price * 100)
    if total_price_cents < 1:
        total_price_cents = 1
        
    prices = [LabeledPrice(label=f"{count} Stars", amount=total_price_cents)]
    await message.bot.send_invoice(
        chat_id=message.chat.id,
        title="شحن رصيد النجوم",
        description=f"شحن {count} نجمة في رصيدك بالبوت",
        payload=f"stars_pay_{count}",
        currency="XTR",
        prices=prices
    )

@dp.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    payload = message.successful_payment.invoice_payload
    if payload.startswith("stars_pay_"):
        try:
            count = int(payload.replace("stars_pay_", ""))
            star_price = CONFIG_DATA.get("star_price", 0.01)
            added_usd = count * star_price
            user_id = message.from_user.id
            if user_id not in MEMORY_USERS:
                MEMORY_USERS[user_id] = {"user_id": user_id, "balance": 0.0, "language": "ar", "banned": False}
            MEMORY_USERS[user_id]["balance"] += added_usd
            await message.answer(f"✅ تم الدفع بنجاح! وإضافة `${added_usd:.2f}` إلى رصيدك.")
        except Exception:
            pass

@dp.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: CallbackQuery):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    total_users = len(MEMORY_USERS)
    total_nums = len(MEMORY_NUMBERS)
    total_purchases = len(MEMORY_PURCHASES)
    banned_users = sum(1 for u in MEMORY_USERS.values() if u.get("banned", False))
    
    text = (
        f"📊 **إحصائيات البوت الشاملة:**\n\n"
        f"👥 إجمالي المستخدمين: `{total_users}`\n"
        f"🚫 عدد المحظورين: `{banned_users}`\n"
        f"📱 الأرقام المتاحة: `{total_nums}`\n"
        f"🛒 العمليات المباعة: `{total_purchases}`\n"
    )
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
    await callback.message.edit_text(text, reply_markup=back_kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    await state.set_state(States.waiting_for_broadcast_msg)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
    await callback.message.edit_text("📢 أرسل الرسالة المراد إذاعتها لجميع المستخدمين:", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_broadcast_msg)
async def execute_broadcast(message: Message, state: FSMContext):
    broadcast_text = message.text
    await state.clear()
    sent_count = 0
    for uid in MEMORY_USERS.keys():
        try:
            await bot.send_message(uid, broadcast_text, parse_mode="Markdown")
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await message.answer(f"✅ تمت الإذاعة بنجاح لـ `{sent_count}` مستخدم.")

@dp.callback_query(F.data == "admin_ban_user")
async def admin_ban_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    await state.set_state(States.waiting_for_ban_id)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
    await callback.message.edit_text("🚫 أرسل آي دي (ID) المستخدم المراد حظره:", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_ban_id)
async def execute_ban(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ أدخل آي دي صحيح:")
        return
    await state.clear()
    if uid in MEMORY_USERS:
        MEMORY_USERS[uid]["banned"] = True
        await message.answer(f"✅ تم حظر المستخدم (`{uid}`) بنجاح.")
    else:
        await message.answer("❌ المستخدم غير موجود في الذاكرة.")

@dp.callback_query(F.data == "admin_unban_user")
async def admin_unban_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    await state.set_state(States.waiting_for_unban_id)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
    await callback.message.edit_text("✅ أرسل آي دي (ID) المستخدم لرفع الحظر عنه:", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_unban_id)
async def execute_unban(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ أدخل آي دي صحيح:")
        return
    await state.clear()
    if uid in MEMORY_USERS:
        MEMORY_USERS[uid]["banned"] = False
        await message.answer(f"✅ تم رفع الحظر عن المستخدم (`{uid}`).")
    else:
        await message.answer("❌ المستخدم غير موجود.")

@dp.callback_query(F.data == "admin_change_star_price")
async def admin_change_star_price_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    await state.set_state(States.waiting_for_star_price)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
    await callback.message.edit_text("⭐ أرسل السعر الجديد للنجمة الواحدة بالدولار (مثال: `0.02`):", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_star_price)
async def execute_change_star_price(message: Message, state: FSMContext):
    try:
        new_price = float(message.text.strip().replace("$", ""))
    except ValueError:
        await message.answer("❌ أدخل سعراً صحيحاً:")
        return
    CONFIG_DATA["star_price"] = new_price
    await state.clear()
    await message.answer(f"✅ تم تعديل سعر النجمة بنجاح إلى: `{new_price}`")

@dp.callback_query(F.data == "admin_add_balance")
async def admin_add_balance_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    await state.set_state(States.waiting_for_add_balance_id)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
    await callback.message.edit_text("➕ أرسل آي دي (ID) المستخدم لإضافة رصيد له:", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_add_balance_id)
async def proc_add_balance_id(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ أدخل آي دي صحيح:")
        return
    await state.update_data(target_user=uid)
    await state.set_state(States.waiting_for_add_balance_amount)
    await message.answer("💵 أرسل المبلغ المراد إضافته (مثال: `5.00`):")

@dp.message(States.waiting_for_add_balance_amount)
async def proc_add_balance_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace("$", ""))
    except ValueError:
        await message.answer("❌ أدخل مبلغاً صحيحاً:")
        return
    data = await state.get_data()
    uid = data["target_user"]
    await state.clear()
    if uid not in MEMORY_USERS:
        MEMORY_USERS[uid] = {"user_id": uid, "balance": 0.0, "language": "ar", "banned": False}
    MEMORY_USERS[uid]["balance"] += amount
    await message.answer(f"✅ تمت إضافة `${amount:.2f}` إلى حساب المستخدم (`{uid}`) بنجاح.")

@dp.callback_query(F.data == "admin_deduct_balance")
async def admin_deduct_balance_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    await state.set_state(States.waiting_for_deduct_balance_id)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
    await callback.message.edit_text("➖ أرسل آي دي (ID) المستخدم لخصم رصيد منه:", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_deduct_balance_id)
async def proc_deduct_balance_id(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ أدخل آي دي صحيح:")
        return
    await state.update_data(target_user=uid)
    await state.set_state(States.waiting_for_deduct_balance_amount)
    await message.answer("💵 أرسل المبلغ المراد خصمه:")

@dp.message(States.waiting_for_deduct_balance_amount)
async def proc_deduct_balance_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace("$", ""))
    except ValueError:
        await message.answer("❌ أدخل مبلغاً صحيحاً:")
        return
    data = await state.get_data()
    uid = data["target_user"]
    await state.clear()
    if uid in MEMORY_USERS:
        MEMORY_USERS[uid]["balance"] = max(0.0, MEMORY_USERS[uid]["balance"] - amount)
        await message.answer(f"✅ تم خصم `${amount:.2f}` من حساب المستخدم (`{uid}`).")
    else:
        await message.answer("❌ المستخدم غير موجود.")

@dp.callback_query(F.data == "admin_set_balance")
async def admin_set_balance_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    await state.set_state(States.waiting_for_set_balance_id)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
    await callback.message.edit_text("🎯 أرسل آي دي (ID) المستخدم لتعيين رصيد له:", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_set_balance_id)
async def proc_set_balance_id(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ أدخل آي دي صحيح:")
        return
    await state.update_data(target_user=uid)
    await state.set_state(States.waiting_for_set_balance_amount)
    await message.answer("💵 أرسل الرصيد الجديد كاملاً:")

@dp.message(States.waiting_for_set_balance_amount)
async def proc_set_balance_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace("$", ""))
    except ValueError:
        await message.answer("❌ أدخل رقماً صحيحاً:")
        return
    data = await state.get_data()
    uid = data["target_user"]
    await state.clear()
    if uid not in MEMORY_USERS:
        MEMORY_USERS[uid] = {"user_id": uid, "balance": 0.0, "language": "ar", "banned": False}
    MEMORY_USERS[uid]["balance"] = amount
    await message.answer(f"✅ تم تعيين رصيد المستخدم (`{uid}`) ليصبح `${amount:.2f}`.")

@dp.callback_query(F.data == "admin_check_user")
async def admin_check_user_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    await state.set_state(States.waiting_for_check_user_id)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
    await callback.message.edit_text("🔍 أرسل آي دي (ID) المستخدم للاستعلام عنه:", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_check_user_id)
async def proc_check_user(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ أدخل آي دي صحيح:")
        return
    await state.clear()
    user = MEMORY_USERS.get(uid)
    if not user:
        await message.answer("❌ هذا المستخدم غير مسجل في البوت.")
        return
    
    text = (
        f"👤 **معلومات المستخدم:**\n\n"
        f"🆔 الآي دي: `{uid}`\n"
        f"💵 الرصيد: `${user.get('balance', 0.0):.2f}`\n"
        f"🌐 اللغة: `{user.get('language', 'ar')}`\n"
        f"🚫 محظور: `{'نعم' if user.get('banned', False) else 'لا'}`"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.callback_query(F.data == "admin_auto_add_num")
async def admin_auto_add_num(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    await state.set_state(States.waiting_for_auto_num_id)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
    await callback.message.edit_text("🔢 أرسل معرف الرقم الأساسي (ID) بالإنجليزية (مثال: `usa1`):", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_auto_num_id)
async def proc_auto_id(message: Message, state: FSMContext):
    await state.update_data(num_id=message.text.strip())
    await state.set_state(States.waiting_for_auto_num_name)
    await message.answer("🏷 أرسل اسم الدولة مع العلم (مثال: `🇺🇸 أمريكا`):")

@dp.message(States.waiting_for_auto_num_name)
async def proc_auto_name(message: Message, state: FSMContext):
    await state.update_data(num_name=message.text.strip())
    await state.set_state(States.waiting_for_auto_num_price)
    await message.answer("💵 أرسل السعر بالدولار (مثال: `1.50`):")

@dp.message(States.waiting_for_auto_num_price)
async def proc_auto_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip().replace("$", ""))
    except ValueError:
        await message.answer("❌ أدخل سعراً صحيحاً:")
        return
    await state.update_data(num_price=price)
    await state.set_state(States.waiting_for_auto_phone)
    await message.answer("📱 أرسل الآن رقم الهاتف مع رمز الدولة (مثال: `+1234567890`):")

@dp.message(States.waiting_for_auto_phone)
async def proc_auto_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    await message.answer("⏳ جاري الاتصال بتليجرام وإرسال كود التحقق...")
    try:
        client = TelegramClient(StringSession(), DEFAULT_API_ID, DEFAULT_API_HASH)
        await client.connect()
        sent_code = await client.send_code_request(phone)
        await state.update_data(phone=phone, phone_code_hash=sent_code.phone_code_hash, client_session=client.session.save())
        await client.disconnect()
        await state.set_state(States.waiting_for_auto_code)
        await message.answer("📥 تم إرسال الكود بنجاح، أرسله الآن:")
    except Exception as e:
        await state.clear()
        await message.answer(f"❌ حدث خطأ:\n`{str(e)}`")

@dp.message(States.waiting_for_auto_code)
async def proc_auto_code(message: Message, state: FSMContext):
    code = message.text.strip()
    data = await state.get_data()
    try:
        client = TelegramClient(StringSession(data["client_session"]), DEFAULT_API_ID, DEFAULT_API_HASH)
        await client.connect()
        await client.sign_in(phone=data["phone"], code=code, phone_code_hash=data["phone_code_hash"])
        final_session = client.session.save()
        await client.disconnect()
        
        num_id = data["num_id"]
        global MEMORY_NUMBERS
        MEMORY_NUMBERS = [n for n in MEMORY_NUMBERS if n["num_id"] != num_id]
        MEMORY_NUMBERS.append({
            "num_id": num_id, "country": "auto", "name": data["num_name"],
            "price": data["num_price"], "phone": data["phone"],
            "session": final_session, "api_id": DEFAULT_API_ID, "api_hash": DEFAULT_API_HASH
        })
        await state.clear()
        await message.answer("✅ تم إضافة الرقم وتفعيله بنجاح!")
    except SessionPasswordNeededError:
        await state.set_state(States.waiting_for_auto_password)
        await message.answer("🔐 الحساب محمي بكلمة مرور (تحقق بخطوتين)، أرسلها الآن:")
    except Exception as e:
        await state.clear()
        await message.answer(f"❌ حدث خطأ: `{str(e)}`")

@dp.message(States.waiting_for_auto_password)
async def proc_auto_password(message: Message, state: FSMContext):
    password = message.text.strip()
    data = await state.get_data()
    try:
        client = TelegramClient(StringSession(data["client_session"]), DEFAULT_API_ID, DEFAULT_API_HASH)
        await client.connect()
        await client.sign_in(password=password)
        final_session = client.session.save()
        await client.disconnect()
        
        num_id = data["num_id"]
        global MEMORY_NUMBERS
        MEMORY_NUMBERS = [n for n in MEMORY_NUMBERS if n["num_id"] != num_id]
        MEMORY_NUMBERS.append({
            "num_id": num_id, "country": "auto", "name": data["num_name"],
            "price": data["num_price"], "phone": data["phone"],
            "session": final_session, "api_id": DEFAULT_API_ID, "api_hash": DEFAULT_API_HASH
        })
        await state.clear()
        await message.answer("✅ تم تفعيل الرقم بنجاح!")
    except Exception as e:
        await state.clear()
        await message.answer(f"❌ خطأ: `{str(e)}`")

@dp.callback_query(F.data == "admin_manage_nums")
async def admin_manage_nums_handler(callback: CallbackQuery):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    if not MEMORY_NUMBERS:
        back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
        await callback.message.edit_text("📭 لا توجد أرقام مضافة حالياً.", reply_markup=back_kb)
        await callback.answer()
        return

    buttons = []
    for num in MEMORY_NUMBERS:
        buttons.append([InlineKeyboardButton(text=f"🗑 حذف: {num['name']} ({num['phone']})", callback_data=f"del_num_{num['num_id']}")])
    buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")])
    await callback.message.edit_text("⚙️ اختر الرقم الذي تريد حذفه:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("del_num_"))
async def delete_number_handler(callback: CallbackQuery):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    num_id = callback.data.replace("del_num_", "")
    global MEMORY_NUMBERS
    MEMORY_NUMBERS = [n for n in MEMORY_NUMBERS if n["num_id"] != num_id]
    await callback.answer("✅ تم حذف الرقم بنجاح!", show_alert=True)
    
    if not MEMORY_NUMBERS:
        back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
        await callback.message.edit_text("📭 لا توجد أرقام مضافة حالياً.", reply_markup=back_kb)
        return

    buttons = []
    for num in MEMORY_NUMBERS:
        buttons.append([InlineKeyboardButton(text=f"🗑 حذف: {num['name']} ({num['phone']})", callback_data=f"del_num_{num['num_id']}")])
    buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")])
    await callback.message.edit_text("⚙️ اختر الرقم الذي تريد حذفه:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data == "buy_number_menu")
async def buy_number_menu(callback: CallbackQuery):
    buttons = []
    for data in MEMORY_NUMBERS:
        num_id = data["num_id"]
        buttons.append([InlineKeyboardButton(text=f"{data['name']} - ${data['price']:.2f}", callback_data=f"buy_country_{num_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")])
    await callback.message.edit_text("🌍 اختر الدولة لشراء الرقم:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_country_"))
async def buy_country_handler(callback: CallbackQuery):
    num_id = callback.data.replace("buy_country_", "")
    data = next((n for n in MEMORY_NUMBERS if n["num_id"] == num_id), None)
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
    data = next((n for n in MEMORY_NUMBERS if n["num_id"] == num_id), None)
    
    balance = MEMORY_USERS.get(user_id, {}).get("balance", 0.0)
    if balance < data['price']:
        await callback.answer("❌ رصيدك غير كافي!", show_alert=True)
        return
        
    MEMORY_USERS[user_id]["balance"] -= data['price']
    MEMORY_PURCHASES.append({"user_id": user_id, "number_id": num_id})
    
    otp_text = await fetch_otp_async(data["session"], data["api_id"], data["api_hash"])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 طلب كود (OTP)", callback_data=f"get_otp_{num_id}")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])
    await callback.message.edit_text(f"🎉 **تم الشراء بنجاح!**\n\n📱 **الرقم:** `{data['phone']}`\n\n📥 **حالة الكود:**\n{otp_text}", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("get_otp_"))
async def get_otp_callback(callback: CallbackQuery):
    num_id = callback.data.replace("get_otp_", "")
    data = next((n for n in MEMORY_NUMBERS if n["num_id"] == num_id), None)
    if not data:
        await callback.answer("❌ الرقم غير موجود.", show_alert=True)
        return
    otp_text = await fetch_otp_async(data["session"], data["api_id"], data["api_hash"])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 طلب كود (OTP)", callback_data=f"get_otp_{num_id}")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])
    try:
        await callback.message.edit_text(f"📱 **الرقم:** `{data['phone']}`\n\n📥 **حالة الكود المحدثة:**\n{otp_text}", reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass
    await callback.answer("تم تحديث حالة الكود!")

async def fetch_otp_async(session_str, api_id, api_hash):
    try:
        client = TelegramClient(StringSession(session_str), api_id, api_hash)
        await client.connect()
        messages = await client.get_messages(777000, limit=3)
        await client.disconnect()
        for msg in messages:
            if msg.text:
                otp_match = re.search(r'\b\d{5,6}\b', msg.text)
                if otp_match:
                    return f"🔑 **كود التحقق:** `{otp_match.group(0)}`"
        return "⏳ لم يصل كود تفعيل جديد بعد."
    except Exception as e:
        return f"❌ خطأ: `{str(e)}`"

# =====================================================================
# 🏁 [تشغيل البوت]
# =====================================================================
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
