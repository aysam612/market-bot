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
TON_WALLET_ADDRESS = "UQAGJ8uRcdJAq-FxA7Zh_TanaT_0kn2ptxnoPSfzECS9Q2ZU"

DEFAULT_ADMIN_USERNAME = "aaysam"
DEFAULT_ADMIN_USER_ID = 8863784148

REQUIRED_CHANNEL = "VPP8P"
BONUS_AMOUNT = 0.01

TEXTS = {
    "support_username": "aaysam"
}

CUSTOM_BUTTONS = [
    {"name": "💬 قناة التليجرام", "url": "https://t.me/VPP8P"},
    {"name": "🔥 جروب الدعم", "url": "https://t.me/aaysam"}
]

CONFIG_DATA = {
    "star_price": 0.01,
    "ton_price": 1.35,
    "payment_methods": ["Telegram Stars ⭐", "TON 💎"]
}

# الأقسام الرئيسية المتاحة في المتجر
MAIN_SECTIONS = [
    "شراء حساب جاهز",
    "إنشاء قديم",
    "احتيالي",
    "أرقام تليجرام عادية"
]

# =====================================================================
# 🚀 [تهيئة البوت والحالات]
# =====================================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

MEMORY_USERS = {
    DEFAULT_ADMIN_USER_ID: {"user_id": DEFAULT_ADMIN_USER_ID, "balance": 10000.02, "language": "ar", "banned": False}
}
MEMORY_NUMBERS = []
MEMORY_PURCHASES = []
MEMORY_REFERRALS = set()

class States(StatesGroup):
    waiting_for_stars_count = State()
    waiting_for_ton_amount = State()
    waiting_for_transfer_id = State()
    waiting_for_transfer_amount = State()
    
    waiting_for_country = State()
    waiting_for_auto_num_id = State()
    waiting_for_auto_num_price = State()
    waiting_for_auto_api_combo = State()
    waiting_for_auto_phone = State()
    waiting_for_auto_code = State()
    waiting_for_auto_password = State()

    waiting_for_edit_name = State()
    waiting_for_edit_price = State()

    waiting_for_btn_name = State()
    waiting_for_btn_url = State()

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
    waiting_for_payment_setting = State()

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
        [InlineKeyboardButton(text="💳 Recharge Balance & Pay" if lang == 'en' else "💳 شحن الرصيد وطرق الدفع", callback_data="recharge_menu")],
        [InlineKeyboardButton(text="🤝 Ref Link" if lang == 'en' else "🤝 رابط إحالة", callback_data="ref_menu"), InlineKeyboardButton(text="💳 Transfer" if lang == 'en' else "💳 تحويل رصيد", callback_data="transfer_menu")],
    ]
    
    for btn in CUSTOM_BUTTONS:
        keyboard_buttons.append([InlineKeyboardButton(text=btn["name"], url=btn["url"])])
        
    keyboard_buttons.append([InlineKeyboardButton(text="🌐 English" if lang == 'ar' else "🌐 العربية", callback_data="toggle_lang")])
    
    if user_id == DEFAULT_ADMIN_USER_ID:
        keyboard_buttons.append([InlineKeyboardButton(text="🛠 لوحة التحكم الشاملة (Admin Panel)", callback_data="admin_panel_main")])
        
    keyboard_buttons.append([InlineKeyboardButton(text="💬 Support" if lang == 'en' else "💬 الدعم الفني", url=f"https://t.me/{TEXTS['support_username'].replace('@', '')}")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    text_header = (
        "👋 أهلاً بك عزيزي في متجر X9 للأرقام المميزة 🌐!\n\n"
        "• احصل على أرقام عالمية مميزة ومفعلة لجميع الاستخدامات.\n"
        "• الشراء فوري وسريع عبر رصيد البوت أو نجوم تليجرام (Stars ⭐).\n"
        "• إمكانية طلب كود التحقق (OTP) بشكل فوري وبكل سهولة بعد الشراء.\n\n"
        f"🆔 معرفك: `{user_id}`\n"
        f"💵 رصيدك: `${balance:.2f}`\n\n"
        "اختر ما يناسبك من القائمة 👇"
    )
        
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
        initial_balance = 10000.02 if user_id == DEFAULT_ADMIN_USER_ID else 0.0
        MEMORY_USERS[user_id] = {
            "user_id": user_id,
            "balance": initial_balance,
            "referred_by": referred_by,
            "language": "ar",
            "banned": False
        }
        
        if referred_by and user_id != DEFAULT_ADMIN_USER_ID and referred_by in MEMORY_USERS:
            referral_key = (referred_by, user_id)
            if referral_key not in MEMORY_REFERRALS:
                MEMORY_REFERRALS.add(referral_key)
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
            initial_balance = 10000.02 if user_id == DEFAULT_ADMIN_USER_ID else 0.0
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
        [InlineKeyboardButton(text="✏️ إدارة وتعديل الأرقام الحالية", callback_data="admin_manage_nums")],
        [InlineKeyboardButton(text="🔘 إدارة الأزرار الإضافية", callback_data="admin_manage_buttons")],
        [InlineKeyboardButton(text="💎 إعدادات وتعديل طرق الدفع (TON/Stars)", callback_data="admin_payment_settings")],
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

@dp.callback_query(F.data == "admin_payment_settings")
async def admin_payment_settings(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    methods = ", ".join(CONFIG_DATA.get("payment_methods", []))
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ تعديل / إضافة طريقة دفع جديدة", callback_data="admin_edit_pay_method")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]
    ])
    await callback.message.edit_text(f"💳 **إدارة طرق الدفع:**\n\nالطرق الحالية المفعلة: `{methods}`\n\nعنوان محفظة التون المربوط:\n`{TON_WALLET_ADDRESS}`", reply_markup=back_kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_edit_pay_method")
async def admin_edit_pay_method(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    await state.set_state(States.waiting_for_payment_setting)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_payment_settings")]])
    await callback.message.edit_text("✍️ أرسل أسماء طرق الدفع مفصولة بفواصل (مثال: `Telegram Stars, TON, USDT`):", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_payment_setting)
async def process_payment_setting(message: Message, state: FSMContext):
    text = message.text.strip()
    methods = [m.strip() for m in text.split(",")]
    CONFIG_DATA["payment_methods"] = methods
    await state.clear()
    await message.answer(f"✅ تم تحديث طرق الدفع بنجاح لتصبح: `{', '.join(methods)}`")

@dp.callback_query(F.data == "admin_manage_buttons")
async def admin_manage_buttons(callback: CallbackQuery):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    buttons = [[InlineKeyboardButton(text="➕ إضافة زر جديد", callback_data="admin_add_btn")]]
    for idx, btn in enumerate(CUSTOM_BUTTONS):
        buttons.append([InlineKeyboardButton(text=f"🗑 حذف: {btn['name']}", callback_data=f"del_btn_{idx}")])
    buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")])
    await callback.message.edit_text("🔘 **إدارة الأزرار الخارجية في القائمة الرئيسية:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data == "admin_add_btn")
async def admin_add_btn_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    await state.set_state(States.waiting_for_btn_name)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_manage_buttons")]])
    await callback.message.edit_text("🏷 أرسل اسم الزر الجديد (مثال: `🔥 قناة العروض`):", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_btn_name)
async def proc_btn_name(message: Message, state: FSMContext):
    await state.update_data(btn_name=message.text.strip())
    await state.set_state(States.waiting_for_btn_url)
    await message.answer("🔗 أرسل رابط الزر (مثال: `https://t.me/...`):")

@dp.message(States.waiting_for_btn_url)
async def proc_btn_url(message: Message, state: FSMContext):
    url = message.text.strip()
    data = await state.get_data()
    CUSTOM_BUTTONS.append({"name": data["btn_name"], "url": url})
    await state.clear()
    await message.answer("✅ تمت إضافة الزر بنجاح إلى القائمة الرئيسية!")

@dp.callback_query(F.data.startswith("del_btn_"))
async def delete_custom_button(callback: CallbackQuery):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    idx = int(callback.data.replace("del_btn_", ""))
    if 0 <= idx < len(CUSTOM_BUTTONS):
        removed = CUSTOM_BUTTONS.pop(idx)
        await callback.answer(f"✅ تم حذف الزر ({removed['name']}) بنجاح!", show_alert=True)
    
    buttons = [[InlineKeyboardButton(text="➕ إضافة زر جديد", callback_data="admin_add_btn")]]
    for i, btn in enumerate(CUSTOM_BUTTONS):
        buttons.append([InlineKeyboardButton(text=f"🗑 حذف: {btn['name']}", callback_data=f"del_btn_{i}")])
    buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")])
    await callback.message.edit_text("🔘 **إدارة الأزرار الخارجية في القائمة الرئيسية:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

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
        f"شارك رابطك مع أصدقائك واحصل على `{BONUS_AMOUNT}$` لكل شخص يدخل عن طريقك!\n"
        f"*(ملاحظة: البوت محمي ضد الإحالات الوهمية أو الدخول المتكرر من نفس الحسابات الفرعية)*\n\n"
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

# =====================================================================
# 💳 [نظام الشحن وطرق الدفع]
# =====================================================================

@dp.callback_query(F.data == "recharge_menu")
async def recharge_menu_handler(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ شحن عبر نجوم تليجرام (Stars)", callback_data="recharge_stars_flow")],
        [InlineKeyboardButton(text="💎 شحن عبر عملة TON", callback_data="recharge_ton_flow")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]
    ])
    text = (
        "💳 **قائمة شحن الرصيد وطرق الدفع المتاحة:**\n\n"
        "• **نجوم تليجرام (Stars):** دفع فوري وآمن داخل التطبيق.\n"
        "• **عملة TON:** تحويل رقمي مباشر عبر محفظتك.\n\n"
        "اختر وسيلة الشحن المناسبة أدناه 👇"
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "recharge_stars_flow")
async def recharge_stars_flow(callback: CallbackQuery, state: FSMContext):
    await state.set_state(States.waiting_for_stars_count)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="recharge_menu")]
    ])
    text = (
        "⭐ **شحن الرصيد عبر نجوم تليجرام:**\n\n"
        "📌 **ملاحظة هامة:** النجمة الواحدة تساوي سنت واحد (`$0.01`).\n\n"
        "أرسل الآن عدد النجوم التي تريد شحنها (مثال: `10` أو `100`):"
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
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
        description=f"شحن {count} نجمة في رصيدك بالبوت (النجمة = $0.01)",
        payload=f"stars_pay_{count}",
        currency="XTR",
        prices=prices
    )

@dp.callback_query(F.data == "recharge_ton_flow")
async def recharge_ton_flow(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="recharge_menu")]
    ])
    text = (
        "💎 **شحن الرصيد عبر عملة TON:**\n\n"
        "قم بالتحويل إلى عنوان المحفظة أدناه، ثم تواصل مع الدعم الفني أو أرسل إيصال التحويل ليتم شحن رصيدك فوراً:\n\n"
        f"📌 **عنوان المحفظة:**\n`{TON_WALLET_ADDRESS}`\n\n"
        f"💡 **سعر التون الواحد التقريبي:** `${CONFIG_DATA.get('ton_price', 1.35)}`\n\n"
        "💬 للتأكيد وإضافة الرصيد بعد التحويل، راسل الدعم الفني: "
        f"[@{TEXTS['support_username']}]"
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

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

# =====================================================================
# 📱 [خطوات إضافة الرقم وتحديد القسم والتفاصيل]
# =====================================================================

@dp.callback_query(F.data == "admin_auto_add_num")
async def admin_auto_add_num(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    
    # عرض الأقسام المحددة للاختيار
    keyboard_buttons = []
    for sec in MAIN_SECTIONS:
        keyboard_buttons.append([InlineKeyboardButton(text=f"📁 {sec}", callback_data=f"sec_{sec}")])
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")])
    
    await callback.message.edit_text("📁 اختر القسم المناسب لإضافة الرقم إليه:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("sec_"))
async def process_section_choice(callback: CallbackQuery, state: FSMContext):
    section_name = callback.data.replace("sec_", "")
    await state.update_data(num_section=section_name)
    await state.set_state(States.waiting_for_country)
    
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_auto_add_num")]])
    await callback.message.edit_text(
        f"✅ تم اختيار القسم: `{section_name}`\n\n"
        "✍️ **الآن اكتب تفاصيل الرقم/الدولة كما تريد أن تظهر للمستخدم (مثال: `هندي انشاء 2022 🇮🇳`):**", 
        reply_markup=back_kb, 
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message(States.waiting_for_country)
async def proc_country(message: Message, state: FSMContext):
    country_details = message.text.strip()
    await state.update_data(country=country_details)
    await state.set_state(States.waiting_for_auto_num_id)
    await message.answer(f"✅ التفاصيل: `{country_details}`\n\n🔢 الآن أرسل معرف الرقم الأساسي (ID) بالإنجليزية (مثال: `num1`):", parse_mode="Markdown")

@dp.message(States.waiting_for_auto_num_id)
async def proc_auto_id(message: Message, state: FSMContext):
    await state.update_data(num_id=message.text.strip())
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
    
    await state.set_state(States.waiting_for_auto_api_combo)
    await message.answer("🔑 أرسل **API_ID** و **API_HASH** معاً مفصولين بنقطتين (مثال:\n`39585443:ad1eb1cdc57ef6913c531da5e4163256`):")

@dp.message(States.waiting_for_auto_api_combo)
async def proc_auto_api_combo(message: Message, state: FSMContext):
    text = message.text.strip()
    if ":" not in text:
        await message.answer("❌ الصيغة غير صحيحة. يجب أن تكون بالشكل:\n`API_ID:API_HASH`\nأعد الإرسال:")
        return
    parts = text.split(":", 1)
    try:
        api_id = int(parts[0].strip())
        api_hash = parts[1].strip()
    except ValueError:
        await message.answer("❌ تأكد من صحة البيانات، أعد المحاولة:")
        return

    await state.update_data(api_id=api_id, api_hash=api_hash)
    await state.set_state(States.waiting_for_auto_phone)
    await message.answer("📱 أرسل الآن رقم الهاتف مع رمز الدولة (مثال: `+1234567890`):")

@dp.message(States.waiting_for_auto_phone)
async def proc_auto_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    data = await state.get_data()
    await message.answer("⏳ جاري الاتصال بتليجرام وإرسال كود التحقق...")
    try:
        client = TelegramClient(StringSession(), data["api_id"], data["api_hash"])
        await client.connect()
        sent_code = await client.send_code_request(phone)
        session_str = client.session.save()
        await client.disconnect()
        
        await state.update_data(phone=phone, phone_code_hash=sent_code.phone_code_hash, client_session=session_str)
        await state.set_state(States.waiting_for_auto_code)
        await message.answer("📥 تم إرسال الكود بنجاح، أرسله الآن:")
    except Exception as e:
        await state.clear()
        await message.answer(f"❌ حدث خطأ في البيانات:\n`{str(e)}`\n\nأعد المحاولة من لوحة التحكم.")

@dp.message(States.waiting_for_auto_code)
async def proc_auto_code(message: Message, state: FSMContext):
    code = re.sub(r'\D', '', message.text.strip())
    data = await state.get_data()
    try:
        client = TelegramClient(StringSession(data["client_session"]), data["api_id"], data["api_hash"])
        await client.connect()
        await client.sign_in(phone=data["phone"], code=code, phone_code_hash=data["phone_code_hash"])
        final_session = client.session.save()
        await client.disconnect()
        
        num_id = data["num_id"]
        global MEMORY_NUMBERS
        MEMORY_NUMBERS = [n for n in MEMORY_NUMBERS if n["num_id"] != num_id]
        MEMORY_NUMBERS.append({
            "num_id": num_id, "section": data["num_section"], "country": data["country"],
            "price": data["num_price"], "phone": data["phone"],
            "session": final_session, "api_id": data["api_id"], "api_hash": data["api_hash"]
        })
        await state.clear()
        await message.answer("✅ تم إضافة الرقم وتفعليه بنجاح ضمن القسم والتفاصيل المحددة!")
    except SessionPasswordNeededError:
        await state.set_state(States.waiting_for_auto_password)
        await message.answer("🔐 الحساب محمي بكلمة مرور (تحقق بخطوتين)، أرسلها الآن:")
    except Exception as e:
        await message.answer(f"❌ الكود غير صحيح أو حدث خطأ: `{str(e)}`\n\nأعد إرسال الكود الصحيح:")

@dp.message(States.waiting_for_auto_password)
async def proc_auto_password(message: Message, state: FSMContext):
    password = message.text.strip()
    data = await state.get_data()
    try:
        client = TelegramClient(StringSession(data["client_session"]), data["api_id"], data["api_hash"])
        await client.connect()
        await client.sign_in(password=password)
        final_session = client.session.save()
        await client.disconnect()
        
        num_id = data["num_id"]
        global MEMORY_NUMBERS
        MEMORY_NUMBERS = [n for n in MEMORY_NUMBERS if n["num_id"] != num_id]
        MEMORY_NUMBERS.append({
            "num_id": num_id, "section": data["num_section"], "country": data["country"],
            "price": data["num_price"], "phone": data["phone"],
            "session": final_session, "api_id": data["api_id"], "api_hash": data["api_hash"]
        })
        await state.clear()
        await message.answer("✅ تم تفعيل الرقم وحفظه بنجاح!")
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
        sec = num.get('section', '')
        cntry = num.get('country', '')
        buttons.append([
            InlineKeyboardButton(text=f"🗑 [{sec}] {cntry}", callback_data=f"del_num_{num['num_id']}"),
            InlineKeyboardButton(text="✏️ تعديل", callback_data=f"edit_num_{num['num_id']}")
        ])
    buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")])
    await callback.message.edit_text("⚙️ **إدارة الأرقام:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("edit_num_"))
async def edit_number_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    num_id = callback.data.replace("edit_num_", "")
    await state.update_data(editing_num_id=num_id)
    await state.set_state(States.waiting_for_edit_name)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_manage_nums")]])
    await callback.message.edit_text("✍️ أرسل التفاصيل الجديدة (مثال: `هندي انشاء 2022 🇮🇳`):", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_edit_name)
async def proc_edit_name(message: Message, state: FSMContext):
    await state.update_data(new_country=message.text.strip())
    await state.set_state(States.waiting_for_edit_price)
    await message.answer("💵 أرسل السعر الجديد بالدولار (مثال: `2.00`):")

@dp.message(States.waiting_for_edit_price)
async def proc_edit_price(message: Message, state: FSMContext):
    try:
        new_price = float(message.text.strip().replace("$", ""))
    except ValueError:
        await message.answer("❌ أدخل سعراً صحيحاً:")
        return
    
    data = await state.get_data()
    num_id = data["editing_num_id"]
    new_country = data["new_country"]
    
    global MEMORY_NUMBERS
    for num in MEMORY_NUMBERS:
        if num["num_id"] == num_id:
            num["country"] = new_country
            num["price"] = new_price
            break
            
    await state.clear()
    await message.answer("✅ تم تعديل بيانات الرقم بنجاح!")

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
        buttons.append([
            InlineKeyboardButton(text=f"🗑 {num.get('section','')} | {num.get('country','')}", callback_data=f"del_num_{num['num_id']}"),
            InlineKeyboardButton(text="✏️ تعديل", callback_data=f"edit_num_{num['num_id']}")
        ])
    buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")])
    await callback.message.edit_text("⚙️ **إدارة الأرقام:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# =====================================================================
# 🛒 [عرض الأقسام غير الفارغة فقط للمستخدمين]
# =====================================================================

@dp.callback_query(F.data == "buy_number_menu")
async def buy_number_menu(callback: CallbackQuery):
    if not MEMORY_NUMBERS:
        back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]])
        await callback.message.edit_text("📭 عذراً، لا توجد أرقام متاحة للبيع في الوقت الحالي.", reply_markup=back_kb)
        await callback.answer()
        return

    # فحص الأقسام التي تحتوي على أرقام فقط (التي ليس فيها أرقام يتم إخفاؤها تلقائياً)
    active_sections = {}
    for num in MEMORY_NUMBERS:
        sec = num.get("section")
        if sec:
            active_sections[sec] = active_sections.get(sec, 0) + 1

    if not active_sections:
        back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]])
        await callback.message.edit_text("📭 عذراً، لا توجد أقسام تحتوي على أرقام حالياً.", reply_markup=back_kb)
        await callback.answer()
        return

    buttons = []
    for sec, count in active_sections.items():
        buttons.append([InlineKeyboardButton(text=f"📁 {sec} (متاح: {count})", callback_data=f"view_sec_{sec}")])
        
    buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")])
    await callback.message.edit_text("🛒 **اختر القسم المطلوب لتصفح الأرقام:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("view_sec_"))
async def view_section_numbers(callback: CallbackQuery):
    sec_name = callback.data.replace("view_sec_", "")
    matched_nums = [n for n in MEMORY_NUMBERS if n.get("section") == sec_name]
    
    if not matched_nums:
        await callback.answer("❌ لا توجد أرقام في هذا القسم حالياً.", show_alert=True)
        return

    buttons = []
    for num in matched_nums:
        details = num.get("country", "رقم مميز")
        price = num["price"]
        buttons.append([
            InlineKeyboardButton(
                text=f"{details} | 💵 ${price:.2f}", 
                callback_data=f"buy_num_{num['num_id']}"
            )
        ])
        
    buttons.append([InlineKeyboardButton(text="🔙 رجوع للأقسام", callback_data="buy_number_menu")])
    await callback.message.edit_text(f"📁 **الأرقام المتوفرة في قسم ({sec_name}):**\nاختر الرقم المناسب لعرض التفاصيل والشراء:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_num_"))
async def buy_number_details(callback: CallbackQuery):
    num_id = callback.data.replace("buy_num_", "")
    data = next((n for n in MEMORY_NUMBERS if n["num_id"] == num_id), None)
    if not data:
        await callback.answer("❌ هذا الرقم غير متوفر حالياً.", show_alert=True)
        return
        
    sec = data.get("section", "")
    details = data.get("country", "")
    price = data["price"]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 تأكيد الشراء مقابل ${price:.2f}", callback_data=f"confirm_buy_{num_id}")],
        [InlineKeyboardButton(text="🔙 رجوع للقسم", callback_data=f"view_sec_{sec}")]
    ])
    
    text = (
        f"📋 **تفاصيل الرقم المطلوب:**\n\n"
        f"📁 القسم: `{sec}`\n"
        f"📌 الوصف: `{details}`\n"
        f"💵 السعر: **${price:.2f}**\n\n"
        "هل تريد إتمام عملية الشراء فوراً؟"
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("confirm_buy_"))
async def confirm_buy_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    num_id = callback.data.replace("confirm_buy_", "")
    
    global MEMORY_NUMBERS
    data = next((n for n in MEMORY_NUMBERS if n["num_id"] == num_id), None)
    if not data:
        await callback.answer("❌ عذراً، لقد سبقك شخص آخر في شراء هذا الرقم!", show_alert=True)
        return

    balance = MEMORY_USERS.get(user_id, {}).get("balance", 0.0)
    if balance < data['price']:
        await callback.answer("❌ رصيدك غير كافي لشراء هذا الرقم!", show_alert=True)
        return
        
    MEMORY_USERS[user_id]["balance"] -= data['price']
    MEMORY_NUMBERS = [n for n in MEMORY_NUMBERS if n["num_id"] != num_id]
    
    MEMORY_PURCHASES.append({"user_id": user_id, "number_id": num_id, "num_data": data})
    
    otp_text = await fetch_otp_async(data["session"], data["api_id"], data["api_hash"])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 طلب كود (OTP)", callback_data=f"get_otp_{num_id}")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])
    await callback.message.edit_text(f"🎉 **تم الشراء بنجاح!**\n\n📱 **الرقم:** `{data['phone']}`\n📌 **التفاصيل:** `{data.get('country','')}`\n\n📥 **حالة الكود:**\n{otp_text}", reply_markup=keyboard, parse_mode="Markdown")

async def fetch_otp_async(session_str: str, api_id: int, api_hash: str) -> str:
    try:
        client = TelegramClient(StringSession(session_str), api_id, api_hash)
        await client.connect()
        messages = await client.get_messages(777000, limit=5)
        await client.disconnect()
        
        for msg in messages:
            if msg.text:
                otp_match = re.search(r'\b\d{5,6}\b', msg.text)
                if otp_match:
                    return f"🔑 **كود التحقق الأحدث:** `{otp_match.group(0)}`\n\n*(اضغط على زر التحديث في الأسفل إذا لم يصلك كود جديد بعد)*"
        return "⏳ لم يصل كود تفعيل جديد بعد."
    except Exception as e:
        return f"❌ حدث خطأ أثناء جلب الكود:\n`{str(e)}`"

@dp.callback_query(F.data.startswith("get_otp_"))
async def refresh_otp_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    num_id = callback.data.replace("get_otp_", "")
    
    purchase = next((p for p in MEMORY_PURCHASES if p["user_id"] == user_id and p["number_id"] == num_id), None)
    if not purchase:
        # تمت معالجة المشكلة هنا وتصحيح التنبيه بنجاح بدون أي تكرار
        await callback.answer("❌ لم يتم العثور على تفاصيل هذا الرقم في سجلك.", show_alert=True)
        return
        
    data = purchase["num_data"]
    await callback.answer("🔄 جاري فحص رسائل تليجرام لجلب الكود الجديد...")
    
    otp_text = await fetch_otp_async(data["session"], data["api_id"], data["api_hash"])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 تحديث الكود (OTP)", callback_data=f"get_otp_{num_id}")],
        [InlineKeyboardButton(text="🔙 القائمة الرئيسية", callback_data="main_menu")]
    ])
    try:
        await callback.message.edit_text(f"📱 **الرقم:** `{data['phone']}`\n\n📥 **حالة الكود المحدث:**\n{otp_text}", reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass

# =====================================================================
# 🚀 [تشغيل البوت الأساسي]
# =====================================================================

async def main():
    print("🤖 البوت يعمل الآن بكفاءة...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("⚠️ تم إيقاف البوت بنجاح.")
