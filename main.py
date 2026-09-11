import os
import re
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
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

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TON_WALLET_ADDRESS = os.getenv("TON_WALLET_ADDRESS", "UQAGJ8uRcdJAq-FxA7Zh_TanaT_0kn2ptxnoPSfzECS9Q2ZU")

DEFAULT_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "aaysam")
DEFAULT_ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "8863784148"))

REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "VPP8P")
BONUS_AMOUNT = 0.01

TEXTS = {
    "support_username": os.getenv("SUPPORT_USERNAME", "aaysam")
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
    
    waiting_for_auto_num_id = State()
    waiting_for_auto_num_name = State()
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

@dp.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        await callback.answer("❌ غير مسموح لك.", show_alert=True)
        return
        
    total_users = len(MEMORY_USERS)
    total_banned = sum(1 for u in MEMORY_USERS.values() if u.get("banned", False))
    total_purchases = len(MEMORY_PURCHASES)
    total_nums = len(MEMORY_NUMBERS)
    
    text = (
        f"📊 **إحصائيات البوت الشاملة:**\n\n"
        f"👥 إجمالي المستخدمين: `{total_users}`\n"
        f"🚫 المستخدمين المحظورين: `{total_banned}`\n"
        f"🛒 إجمالي الأرقام المتاحة: `{total_nums}`\n"
        f"📦 إجمالي عمليات الشراء: `{total_purchases}`\n"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 عودة للوحة التحكم", callback_data="admin_panel_main")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_auto_add_num")
async def admin_auto_add_num_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        await callback.answer("❌ غير مسموح لك.", show_alert=True)
        return
        
    await state.set_state(States.waiting_for_auto_num_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ إلغاء", callback_data="admin_panel_main")]
    ])
    await callback.message.edit_text("🔢 أرسل الآن **معرف فريد (ID)** للرقم أو الدولة (مثال: `usa_1` أو `egypt_2`):", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.message(States.waiting_for_auto_num_id)
async def process_auto_num_id(message: Message, state: FSMContext):
    if message.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    num_id = message.text.strip()
    await state.update_data(auto_num_id=num_id)
    await state.set_state(States.waiting_for_auto_num_name)
    await message.answer("🏷 أرسل الآن **اسم الدولة أو الوصف** الذي سيظهر للمستخدمين (مثال: `🇺🇸 أمريكا - تليجرام`):")

@dp.message(States.waiting_for_auto_num_name)
async def process_auto_num_name(message: Message, state: FSMContext):
    if message.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    num_name = message.text.strip()
    await state.update_data(auto_num_name=num_name)
    await state.set_state(States.waiting_for_auto_num_price)
    await message.answer("💵 أرسل الآن **سعر الرقم** بالدولار (مثال: `1.5`):")

@dp.message(States.waiting_for_auto_num_price)
async def process_auto_num_price(message: Message, state: FSMContext):
    if message.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    try:
        price = float(message.text.strip())
    except ValueError:
        await message.answer("❌ يرجى إدخال رقم صحيح للسعر:")
        return
        
    await state.update_data(auto_num_price=price)
    await state.set_state(States.waiting_for_auto_api_combo)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ إلغاء", callback_data="admin_panel_main")]
    ])
    await message.answer(
        "🔑 اختر نوع الجلسة أو أدخل بيانات الجلسة مباشرة:\n\n"
        "يمكنك إرسال **StringSession** مباشرة أو إرسال رقم الهاتف مع الـ API ID و API Hash بالصيغة التالية:\n"
        "`api_id:api_hash:phone` أو أرسل StringSession جاهزة:",
        reply_markup=keyboard, parse_mode="Markdown"
    )

@dp.message(States.waiting_for_auto_api_combo)
async def process_auto_api_combo(message: Message, state: FSMContext):
    if message.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    text = message.text.strip()
    
    if ":" in text and len(text.split(":")) >= 3:
        parts = text.split(":")
        api_id_str = parts[0].strip()
        api_hash = parts[1].strip()
        phone = parts[2].strip()
        
        if not api_id_str.isdigit():
            await message.answer("❌ صيغة API ID خاطئة. يجب أن يكون رقماً. أعد المحاولة:")
            return
            
        api_id = int(api_id_str)
        await state.update_data(api_id=api_id, api_hash=api_hash, phone=phone, session_type="credentials")
        
        try:
            client = TelegramClient(StringSession(), api_id, api_hash)
            await client.connect()
            sent = await client.send_code_request(phone)
            await state.update_data(phone_code_hash=sent.phone_code_hash)
            await client.disconnect()
        except Exception as e:
            await message.answer(f"❌ حدث خطأ أثناء إرسال كود التحقق عبر تليجرام: {e}\nتأكد من صحة البيانات وأعد إرسالها:")
            return
            
        await state.set_state(States.waiting_for_auto_code)
        await message.answer("📲 تم إرسال كود التحقق (OTP) إلى الحساب.\nأرسل الآن **كود التحقق** الذي تلقيته:")
    else:
        string_session = text
        data = await state.get_data()
        num_id = data.get("auto_num_id")
        num_name = data.get("auto_num_name")
        num_price = data.get("auto_num_price")
        
        MEMORY_NUMBERS.append({
            "id": num_id,
            "name": num_name,
            "price": num_price,
            "session": string_session,
            "api_id": None,
            "api_hash": None,
            "phone": None
        })
        
        await state.clear()
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 عودة للوحة التحكم", callback_data="admin_panel_main")]
        ])
        await message.answer(f"✅ تمت إضافة الرقم بنجاح تام وبصيغة StringSession جاهزة!\n\n🏷 الاسم: {num_name}\n💵 السعر: ${num_price}", reply_markup=keyboard)

@dp.message(States.waiting_for_auto_code)
async def process_auto_code(message: Message, state: FSMContext):
    if message.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    code = message.text.strip()
    await state.update_data(code=code)
    
    data = await state.get_data()
    api_id = data.get("api_id")
    api_hash = data.get("api_hash")
    phone = data.get("phone")
    phone_code_hash = data.get("phone_code_hash")
    
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    
    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        string_session = client.session.save()
        await client.disconnect()
        
        num_id = data.get("auto_num_id")
        num_name = data.get("auto_num_name")
        num_price = data.get("auto_num_price")
        
        MEMORY_NUMBERS.append({
            "id": num_id,
            "name": num_name,
            "price": num_price,
            "session": string_session,
            "api_id": api_id,
            "api_hash": api_hash,
            "phone": phone
        })
        
        await state.clear()
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 عودة للوحة التحكم", callback_data="admin_panel_main")]
        ])
        await message.answer(f"✅ تم تسجيل الدخول وحفظ الجلسة وإضافة الرقم بنجاح تام!\n\n🏷 الاسم: {num_name}\n💵 السعر: ${num_price}", reply_markup=keyboard)
        
    except SessionPasswordNeededError:
        await client.disconnect()
        await state.set_state(States.waiting_for_auto_password)
        await message.answer("🔒 الحساب محمي بكلمة مرور تحقق خطوتين (Two-Step Verification).\nأرسل الآن **كلمة المرور**:")
    except PhoneCodeInvalidError:
        await client.disconnect()
        await message.answer("❌ كود التحقق غير صحيح. أرسل الكود الصحيح مرة أخرى:")
    except Exception as e:
        await client.disconnect()
        await state.clear()
        await message.answer(f"❌ حدث خطأ غير متوقع: {e}")

@dp.message(States.waiting_for_auto_password)
async def process_auto_password(message: Message, state: FSMContext):
    if message.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    password = message.text.strip()
    data = await state.get_data()
    api_id = data.get("api_id")
    api_hash = data.get("api_hash")
    phone = data.get("phone")
    code = data.get("code")
    phone_code_hash = data.get("phone_code_hash")
    
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    
    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
    except Exception:
        pass
        
    try:
        await client.sign_in(password=password)
        string_session = client.session.save()
        await client.disconnect()
        
        num_id = data.get("auto_num_id")
        num_name = data.get("auto_num_name")
        num_price = data.get("auto_num_price")
        
        MEMORY_NUMBERS.append({
            "id": num_id,
            "name": num_name,
            "price": num_price,
            "session": string_session,
            "api_id": api_id,
            "api_hash": api_hash,
            "phone": phone
        })
        
        await state.clear()
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 عودة للوحة التحكم", callback_data="admin_panel_main")]
        ])
        await message.answer(f"✅ تم تخطي التحقق بخطوتين وحفظ الجلسة وإضافة الرقم بنجاح!\n\n🏷 الاسم: {num_name}\n💵 السعر: ${num_price}", reply_markup=keyboard)
    except Exception as e:
        await client.disconnect()
        await state.clear()
        await message.answer(f"❌ كلمة المرور خاطئة أو حدث خطأ: {e}")

@dp.callback_query(F.data == "admin_manage_nums")
async def admin_manage_nums_handler(callback: CallbackQuery):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        await callback.answer("❌ غير مسموح لك.", show_alert=True)
        return
        
    if not MEMORY_NUMBERS:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 عودة للوحة التحكم", callback_data="admin_panel_main")]
        ])
        await callback.message.edit_text("📭 لا توجد أرقام مضافة حالياً في المتجر.", reply_markup=keyboard)
        await callback.answer()
        return

    buttons = []
    for idx, num in enumerate(MEMORY_NUMBERS):
        num_identifier = num.get("id") or str(idx)
        buttons.append([
            InlineKeyboardButton(text=f"🗑 حذف: {num.get('name')} (${num.get('price')})", callback_data=f"admin_del_num_{num_identifier}")
        ])
        
    buttons.append([InlineKeyboardButton(text="🔙 عودة للوحة التحكم", callback_data="admin_panel_main")])
    await callback.message.edit_text("⚙️ **إدارة الأرقام الحالية:**\nاختر رقماً لحذفه من المتجر:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_del_num_"))
async def admin_delete_number_callback(callback: CallbackQuery):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        await callback.answer("❌ غير مسموح لك.", show_alert=True)
        return
        
    target_id = callback.data.replace("admin_del_num_", "")
    global MEMORY_NUMBERS
    initial_len = len(MEMORY_NUMBERS)
    MEMORY_NUMBERS = [n for n in MEMORY_NUMBERS if str(n.get("id")) != target_id]
    
    if len(MEMORY_NUMBERS) < initial_len:
        await callback.answer("✅ تم حذف الرقم بنجاح!", show_alert=True)
    else:
        await callback.answer("❌ لم يتم العثور على الرقم.", show_alert=True)
        
    if not MEMORY_NUMBERS:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 عودة للوحة التحكم", callback_data="admin_panel_main")]
        ])
        await callback.message.edit_text("📭 لا توجد أرقام مضافة حالياً في المتجر.", reply_markup=keyboard)
        return

    buttons = []
    for idx, num in enumerate(MEMORY_NUMBERS):
        num_identifier = num.get("id") or str(idx)
        buttons.append([
            InlineKeyboardButton(text=f"🗑 حذف: {num.get('name')} (${num.get('price')})", callback_data=f"admin_del_num_{num_identifier}")
        ])
        
    buttons.append([InlineKeyboardButton(text="🔙 عودة للوحة التحكم", callback_data="admin_panel_main")])
    await callback.message.edit_text("⚙️ **إدارة الأرقام الحالية:**\nاختر رقماً لحذفه من المتجر:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        await callback.answer("❌ غير مسموح لك.", show_alert=True)
        return
        
    await state.set_state(States.waiting_for_broadcast_msg)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ إلغاء", callback_data="admin_panel_main")]
    ])
    await callback.message.edit_text("📢 أرسل الآن **الرسالة** التي تريد إذاعتها لجميع مستخدمي البوت:", reply_markup=keyboard)
    await callback.answer()

@dp.message(States.waiting_for_broadcast_msg)
async def process_broadcast_msg(message: Message, state: FSMContext):
    if message.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
        
    broadcast_text = message.text
    await state.clear()
    
    sent_count = 0
    failed_count = 0
    
    status_msg = await message.answer("⏳ جاري بدء الإذاعة لجميع المستخدمين...")
    
    for user_id in MEMORY_USERS.keys():
        try:
            await bot.send_message(user_id, broadcast_text)
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed_count += 1
            
    await status_msg.edit_text(
        f"✅ **تمت الإذاعة بنجاح!**\n\n"
        f"📤 الرسائل المرسلة بنجاح: `{sent_count}`\n"
        f"❌ فشل الإرسال لـ: `{failed_count}` مستخدم"
    )

@dp.callback_query(F.data == "admin_add_balance")
async def admin_add_balance_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        await callback.answer("❌ غير مسموح لك.", show_alert=True)
        return
    await state.set_state(States.waiting_for_add_balance_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ إلغاء", callback_data="admin_panel_main")]])
    await callback.message.edit_text("➕ أرسل **معرف المستخدم (User ID)** المراد إضافة الرصيد له:", reply_markup=keyboard)
    await callback.answer()

@dp.message(States.waiting_for_add_balance_id)
async def process_add_balance_id(message: Message, state: FSMContext):
    if message.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ يرجى إدخال رقم آي دي (ID) صحيح:")
        return
        
    await state.update_data(target_user_id=uid)
    await state.set_state(States.waiting_for_add_balance_amount)
    await message.answer("💵 أرسل الآن **المبلغ** المراد إضافته (مثال: `5.0` أو `10.25`):")

@dp.message(States.waiting_for_add_balance_amount)
async def process_add_balance_amount(message: Message, state: FSMContext):
    if message.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    try:
        amount = float(message.text.strip())
    except ValueError:
        await message.answer("❌ يرجى إدخال رقم صحيح للمبلغ:")
        return
        
    data = await state.get_data()
    uid = data.get("target_user_id")
    await state.clear()
    
    if uid not in MEMORY_USERS:
        MEMORY_USERS[uid] = {"user_id": uid, "balance": 0.0, "language": "ar", "banned": False}
        
    MEMORY_USERS[uid]["balance"] += amount
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 عودة للوحة التحكم", callback_data="admin_panel_main")]])
    await message.answer(f"✅ تمت إضافة مبلغ `${amount:.2f}` بنجاح إلى حساب المستخدم (`{uid}`)!\nرصيده الحالي: `${MEMORY_USERS[uid]['balance']:.2f}`", reply_markup=keyboard)
    
    try:
        await bot.send_message(uid, f"🎁 قام المشرف بإضافة رصيد إلى حسابك بقيمة `${amount:.2f}`!")
    except Exception:
        pass

@dp.callback_query(F.data == "admin_deduct_balance")
async def admin_deduct_balance_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        await callback.answer("❌ غير مسموح لك.", show_alert=True)
        return
    await state.set_state(States.waiting_for_deduct_balance_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ إلغاء", callback_data="admin_panel_main")]])
    await callback.message.edit_text("➖ أرسل **معرف المستخدم (User ID)** المراد خصم الرصيد منه:", reply_markup=keyboard)
    await callback.answer()

@dp.message(States.waiting_for_deduct_balance_id)
async def process_deduct_balance_id(message: Message, state: FSMContext):
    if message.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ يرجى إدخال رقم آي دي (ID) صحيح:")
        return
        
    await state.update_data(target_user_id=uid)
    await state.set_state(States.waiting_for_deduct_balance_amount)
    await message.answer("💵 أرسل الآن **المبلغ** المراد خصمه:")

@dp.message(States.waiting_for_deduct_balance_amount)
async def process_deduct_balance_amount(message: Message, state: FSMContext):
    if message.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    try:
        amount = float(message.text.strip())
    except ValueError:
        await message.answer("❌ يرجى إدخال رقم صحيح للمبلغ:")
        return
        
    data = await state.get_data()
    uid = data.get("target_user_id")
    await state.clear()
    
    if uid not in MEMORY_USERS:
        await message.answer("❌ هذا المستخدم غير موجود في سجلات البوت.")
        return
        
    MEMORY_USERS[uid]["balance"] = max(0.0, MEMORY_USERS[uid]["balance"] - amount)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 عودة للوحة التحكم", callback_data="admin_panel_main")]])
    await message.answer(f"✅ تم خصم مبلغ `${amount:.2f}` بنجاح من حساب المستخدم (`{uid}`)!\nرصيده الحالي: `${MEMORY_USERS[uid]['balance']:.2f}`", reply_markup=keyboard)

@dp.callback_query(F.data == "admin_ban_user")
async def admin_ban_user_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        await callback.answer("❌ غير مسموح لك.", show_alert=True)
        return
    await state.set_state(States.waiting_for_ban_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ إلغاء", callback_data="admin_panel_main")]])
    await callback.message.edit_text("🚫 أرسل **معرف المستخدم (User ID)** المراد حظره من البوت:", reply_markup=keyboard)
    await callback.answer()

@dp.message(States.waiting_for_ban_id)
async def process_ban_user_id(message: Message, state: FSMContext):
    if message.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ يرجى إدخال رقم آي دي (ID) صحيح:")
        return
        
    await state.clear()
    if uid not in MEMORY_USERS:
        MEMORY_USERS[uid] = {"user_id": uid, "balance": 0.0, "language": "ar", "banned": True}
    else:
        MEMORY_USERS[uid]["banned"] = True
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 عودة للوحة التحكم", callback_data="admin_panel_main")]])
    await message.answer(f"✅ تم حظر المستخدم (`{uid}`) بنجاح تام من استخدام البوت.", reply_markup=keyboard)

@dp.callback_query(F.data == "admin_unban_user")
async def admin_unban_user_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        await callback.answer("❌ غير مسموح لك.", show_alert=True)
        return
    await state.set_state(States.waiting_for_unban_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ إلغاء", callback_data="admin_panel_main")]])
    await callback.message.edit_text("✅ أرسل **معرف المستخدم (User ID)** لرفع الحظر عنه:", reply_markup=keyboard)
    await callback.answer()

@dp.message(States.waiting_for_unban_id)
async def process_unban_user_id(message: Message, state: FSMContext):
    if message.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ يرجى إدخال رقم آي دي (ID) صحيح:")
        return
        
    await state.clear()
    if uid in MEMORY_USERS:
        MEMORY_USERS[uid]["banned"] = False
        await message.answer(f"✅ تم رفع الحظر عن المستخدم (`{uid}`) بنجاح.")
    else:
        await message.answer("❌ المستخدم غير مسجل أصلاً في البوت.")

@dp.callback_query(F.data == "admin_check_user")
async def admin_check_user_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        await callback.answer("❌ غير مسموح لك.", show_alert=True)
        return
    await state.set_state(States.waiting_for_check_user_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ إلغاء", callback_data="admin_panel_main")]])
    await callback.message.edit_text("🔍 أرسل **معرف المستخدم (User ID)** للاستعلام عن معلوماته:", reply_markup=keyboard)
    await callback.answer()

@dp.message(States.waiting_for_check_user_id)
async def process_check_user_id(message: Message, state: FSMContext):
    if message.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ يرجى إدخال رقم آي دي (ID) صحيح:")
        return
        
    await state.clear()
    user_data = MEMORY_USERS.get(uid)
    if not user_data:
        await message.answer("❌ هذا المستخدم غير موجود في سجلات البوت.")
        return
        
    purchased_count = sum(1 for p in MEMORY_PURCHASES if p["user_id"] == uid)
    
    text = (
        f"👤 **معلومات المستخدم المطلوبة:**\n\n"
        f"🆔 المعرف: `{uid}`\n"
        f"💵 الرصيد الحالي: `${user_data.get('balance', 0.0):.2f}`\n"
        f"🌐 اللغة المفضلة: `{user_data.get('language', 'ar')}`\n"
        f"🚫 الحالة: `{'محظور ❌' if user_data.get('banned', False) else 'نشط ✅'}`\n"
        f"🛒 عدد الأرقام المشتراة: `{purchased_count}`"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 عودة للوحة التحكم", callback_data="admin_panel_main")]])
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data == "admin_change_star_price")
async def admin_change_star_price_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        await callback.answer("❌ غير مسموح لك.", show_alert=True)
        return
    await state.set_state(States.waiting_for_star_price)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ إلغاء", callback_data="admin_panel_main")]])
    await callback.message.edit_text(f"⭐ السعر الحالي للنجمة: `${CONFIG_DATA.get('star_price', 0.01)}`\n\nأرسل السعر الجديد للنجمة الواحدة بالدولار:", reply_markup=keyboard)
    await callback.answer()

@dp.message(States.waiting_for_star_price)
async def process_change_star_price(message: Message, state: FSMContext):
    if message.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    try:
        new_price = float(message.text.strip())
    except ValueError:
        await message.answer("❌ يرجى إدخال رقم صحيح للسعر:")
        return
        
    CONFIG_DATA["star_price"] = new_price
    await state.clear()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 عودة للوحة التحكم", callback_data="admin_panel_main")]])
    await message.answer(f"✅ تم تحديث سعر النجمة بنجاح ليصبح: `${new_price}`", reply_markup=keyboard)

@dp.callback_query(F.data == "buy_number_menu")
async def buy_number_menu_handler(callback: CallbackQuery):
    if not MEMORY_NUMBERS:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 القائمة الرئيسية", callback_data="main_menu")]])
        await callback.message.edit_text("📭 عذراً، لا توجد أرقام متاحة للشراء في الوقت الحالي. يجدر بك العودة لاحقاً.", reply_markup=keyboard)
        await callback.answer()
        return

    buttons = []
    for idx, num in enumerate(MEMORY_NUMBERS):
        num_identifier = num.get("id") or str(idx)
        buttons.append([
            InlineKeyboardButton(text=f"🛒 {num.get('name')} - ${num.get('price')}", callback_data=f"buy_num_item_{num_identifier}")
        ])
        
    buttons.append([InlineKeyboardButton(text="🔙 القائمة الرئيسية", callback_data="main_menu")])
    await callback.message.edit_text("🛒 **متجر الأرقام المميزة:**\nاختر الرقم الذي تريد شراءه:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_num_item_"))
async def buy_num_item_handler(callback: CallbackQuery):
    target_id = callback.data.replace("buy_num_item_", "")
    num_data = None
    for idx, num in enumerate(MEMORY_NUMBERS):
        if str(num.get("id") or str(idx)) == target_id:
            num_data = num
            break
            
    if not num_data:
        await callback.answer("❌ هذا الرقم لم يعد متوفراً أو تم بيعه.", show_alert=True)
        return
        
    price = num_data.get("price")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 تأكيد الشراء مقابل ${price:.2f}", callback_data=f"confirm_buy_{target_id}")],
        [InlineKeyboardButton(text="🔙 إلغاء", callback_data="buy_number_menu")]
    ])
    await callback.message.edit_text(
        f"📱 **تفاصيل الرقم المطلوب:**\n\n"
        f"🏷 القسم/الدولة: {num_data.get('name')}\n"
        f"💵 السعر: `${price:.2f}`\n\n"
        f"هل أنت متأكد من رغبتك في إتمام عملية الشراء من رصيدك بالبوت؟",
        reply_markup=keyboard, parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("confirm_buy_"))
async def confirm_buy_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    target_id = callback.data.replace("confirm_buy_", "")
    
    user_data = MEMORY_USERS.get(user_id, {"balance": 0.0})
    balance = user_data.get("balance", 0.0)
    
    num_index = -1
    num_data = None
    for idx, num in enumerate(MEMORY_NUMBERS):
        if str(num.get("id") or str(idx)) == target_id:
            num_index = idx
            num_data = num
            break
            
    if not num_data:
        await callback.answer("❌ عذراً، تم بيع هذا الرقم مسبقاً!", show_alert=True)
        return
        
    price = num_data.get("price")
    if balance < price:
        await callback.answer("❌ رصيدك غير كافي لإتمام الشراء. قم بشحن رصيدك أولاً.", show_alert=True)
        return
        
    MEMORY_USERS[user_id]["balance"] -= price
    MEMORY_NUMBERS.pop(num_index)
    
    MEMORY_PURCHASES.append({
        "user_id": user_id,
        "number_id": target_id,
        "num_data": num_data,
        "time": datetime.now()
    })
    
    phone_number = num_data.get("phone") or "متاح عبر الجلسة"
    session_str = num_data.get("session")
    api_id = num_data.get("api_id")
    api_hash = num_data.get("api_hash")
    
    otp_text = "⏳ اضغط على زر طلب الكود أدناه لجلب أحدث رسالة تحقق وصلت للرقم."
    if session_str and api_id and api_hash:
        try:
            client = TelegramClient(StringSession(session_str), api_id, api_hash)
            await client.connect()
            messages = await client.get_messages(777000, limit=3)
            await client.disconnect()
            for msg in messages:
                if msg.text and any(c.isdigit() for c in msg.text):
                    otp_text = f"🔑 آخر كود تحقق تم العثور عليه:\n`{msg.text}`"
                    break
        except Exception:
            pass

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 جلب كود التحقق (OTP)", callback_data=f"get_otp_{target_id}")],
        [InlineKeyboardButton(text="🔙 القائمة الرئيسية", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        f"🎉 **تمت عملية الشراء بنجاح تام!**\n\n"
        f"📱 **رقم الهاتف:** `{phone_number}`\n"
        f"💵 **المبلغ المخصوم:** `${price:.2f}`\n\n"
        f"📥 **حالة كود التحقق:**\n{otp_text}",
        reply_markup=keyboard, parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("get_otp_"))
async def get_otp_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    target_id = callback.data.replace("get_otp_", "")
    
    purchased_item = None
    for p in MEMORY_PURCHASES:
        if p["user_id"] == user_id and p["number_id"] == target_id:
            purchased_item = p
            break
            
    if not purchased_item:
        await callback.answer("❌ لم يتم العثور على هذا الرقم في سجل مشترياتك.", show_alert=True)
        return
        
    num_data = purchased_item["num_data"]
    session_str = num_data.get("session")
    api_id = num_data.get("api_id")
    api_hash = num_data.get("api_hash")
    phone_number = num_data.get("phone") or "غير متوفر"
    
    otp_text = "⏳ لم يتم العثور على رسائل تحقق جديدة بعد."
    if session_str and api_id and api_hash:
        try:
            client = TelegramClient(StringSession(session_str), api_id, api_hash)
            await client.connect()
            messages = await client.get_messages(777000, limit=5)
            await client.disconnect()
            for msg in messages:
                if msg.text:
                    otp_text = f"🔑 أحدث رسالة تحقق وصلت:\n`{msg.text}`"
                    break
        except Exception as e:
            otp_text = f"⚠️ حدث خطأ أثناء الاتصال بجلسة تليجرام لجلب الكود: {e}"
    else:
        otp_text = "📌 هذا الرقم محفوظ بصيغة StringSession مباشرة. يمكنك استخدامه مباشرة في تطبيقات تليجرام."

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 جلب كود التحقق (OTP)", callback_data=f"get_otp_{target_id}")],
        [InlineKeyboardButton(text="🔙 القائمة الرئيسية", callback_data="main_menu")]
    ])
    
    try:
        await callback.message.edit_text(
            f"📱 **تفاصيل الرقم المشتري:**\n\n"
            f"📞 **رقم الهاتف:** `{phone_number}`\n\n"
            f"📥 **حالة الرسائل:**\n{otp_text}",
            reply_markup=keyboard, parse_mode="Markdown"
        )
    except Exception:
        pass
    await callback.answer("✅ تم تحديث حالة الكود.")

async def main():
    print("🤖 Bot started successfully and polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
