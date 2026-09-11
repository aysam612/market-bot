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
# 🛠️ [منطقة التعديل الشامل - عدل كل ما تريد هنا بكل حرية]
# =====================================================================

# 1. توكن البوت الخاص بك (يمكنك تغييره هنا)
BOT_TOKEN = "8896024185:AAF911IAOlt_2BS8HXXVaf8Zrxz3y9MKgkY"

# 2. بيانات تليجرام API (لا تقم بتغييرها إلا إذا كنت ترغب بذلك)
DEFAULT_API_ID = 12345678       
DEFAULT_API_HASH = "your_api_hash_here"  

# 3. بيانات المالك الأساسي للبوت
DEFAULT_ADMIN_USERNAME = "aaysam"
DEFAULT_ADMIN_USER_ID = 8863784148

# 4. قناة الإجبارية (اكتب يوزر القناة بدون @، أو اتركه فارغاً إذا لا تريد اشتراك إجباري)
REQUIRED_CHANNEL = "VPP8P"

# 5. قيمة الهدية اليومية ورابط الإحالة ($)
BONUS_AMOUNT = 0.01

# 6. النصوص الافتتاحية والترحيبية للأسواق واللوحات (يمكنك تغيير النصوص كما تحب)
TEXTS = {
    "welcome_ar": "👋 أهلاً بك عزيزي في متجر X9 للأرقام المميزة 🌐!\n\n🆔 معرفك: `{user_id}`\n💵 رصيدك: `${balance:.2f}`\n\nاختر ما يناسبك من القائمة أدناه 👇",
    "welcome_en": "👋 Welcome to X9 Store for Premium Numbers 🌐!\n\n🆔 ID: `{user_id}`\n💵 Balance: `${balance:.2f}`\n\nChoose what you want from the menu below 👇",
    "support_username": "aaysam"
}

# 7. قائمة الأزرار المخصصة الثابتة (يمكنك إضافة أو تعديل أو حذف أي زر تريده هنا)
CUSTOM_BUTTONS = [
    {"name": "💬 قناة التليجرام", "url": "https://t.me/VPP8P"},
    {"name": "🔥 جروب الدعم", "url": "https://t.me/aaysam"}
]

# 8. أسعار الخدمات (سعر النجمة الواحدة بالدولار)
CONFIG_DATA = {
    "star_price": 0.01
}

# =====================================================================
# 🚀 [نهاية منطقة التعديل - الكود البرمجي التشغيلي الأساسي]
# =====================================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# قواعد بيانات الذاكرة المحلية الفورية
MEMORY_USERS = {
    DEFAULT_ADMIN_USER_ID: {"user_id": DEFAULT_ADMIN_USER_ID, "balance": 10000.0, "language": "ar", "banned": False}
}
MEMORY_NUMBERS = []
MEMORY_PURCHASES = []

class States(StatesGroup):
    waiting_for_stars_count = State()
    waiting_for_transfer_id = State()
    waiting_for_transfer_amount = State()
    waiting_for_new_admin_id = State()
    waiting_for_new_admin_username = State()
    waiting_for_btn_name = State()
    waiting_for_btn_url = State()
    
    waiting_for_auto_num_id = State()
    waiting_for_auto_num_name = State()
    waiting_for_auto_num_price = State()
    waiting_for_auto_phone = State()
    waiting_for_auto_code = State()
    waiting_for_auto_password = State()

    waiting_for_new_price = State()
    waiting_for_new_name = State()
    waiting_for_star_price = State()
    waiting_for_ban_id = State()
    waiting_for_unban_id = State()

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
    user = callback.from_user
    user_id = user.id
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
            MEMORY_USERS[user_id] = {
                "user_id": user_id,
                "balance": initial_balance,
                "language": "ar",
                "banned": False
            }
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
        [InlineKeyboardButton(text="✏️ إدارة الأرقام الحالية (تعديل/حذف)", callback_data="admin_manage_nums")],
        [InlineKeyboardButton(text=f"⭐ تعديل سعر النجمة ({current_star_price} حالياً)", callback_data="admin_change_star_price")],
        [InlineKeyboardButton(text="🚫 حظر مستخدم", callback_data="admin_ban_user"), InlineKeyboardButton(text="✅ رفع حظر مستخدم", callback_data="admin_unban_user")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])
    
    text = (
        f"🛠 **لوحة تحكم الأرقام السريعة:**\n"
        f"👤 المالك: `{DEFAULT_ADMIN_USERNAME}` (`{DEFAULT_ADMIN_USER_ID}`)\n\n"
        f"اختر العملية التي تريد تنفيذها:"
    )
    
    if isinstance(event, CallbackQuery):
        await message.edit_text(text, reply_markup=builder, parse_mode="Markdown")
        await event.answer()
    else:
        await message.answer(text, reply_markup=builder, parse_mode="Markdown")

@dp.callback_query(F.data == "admin_auto_add_num")
async def admin_auto_add_num(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    await state.set_state(States.waiting_for_auto_num_id)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
    await callback.message.edit_text("🔢 أرسل **معرف الرقم الأساسي (ID)** بالإنجليزية (مثال: `usa1` أو `1`):", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_auto_num_id)
async def proc_auto_id(message: Message, state: FSMContext):
    await state.update_data(num_id=message.text.strip())
    await state.set_state(States.waiting_for_auto_num_name)
    await message.answer("🏷 أرسل اسم الدولة مع العلم (مثال: `🇺🇸 أمريكا مميز`):")

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
    await message.answer("📱 أرسل الآن **رقم الهاتف** مع رمز الدولة (مثال: `+1234567890`):")

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
        await message.answer("📥 تم إرسال الكود بنجاح!\n\nأرسل الآن **كود التحقق (OTP)** الذي وصلك:")
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
            "num_id": num_id,
            "country": "auto",
            "name": data["num_name"],
            "price": data["num_price"],
            "phone": data["phone"],
            "session": final_session,
            "api_id": DEFAULT_API_ID,
            "api_hash": DEFAULT_API_HASH
        })
        await state.clear()
        await message.answer("✅ **تم تسجيل الدخول وإضافة الرقم بنجاح إلى المتجر!** 🎉")
    except SessionPasswordNeededError:
        await state.set_state(States.waiting_for_auto_password)
        await message.answer("🔐 هذا الحساب محمي بـ **كلمة المرور (التحقق بخطوتين)**. أرسلها الآن:")
    except PhoneCodeInvalidError:
        await message.answer("❌ الكود غير صحيح، أعد إرساله:")
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
            "num_id": num_id,
            "country": "auto",
            "name": data["num_name"],
            "price": data["num_price"],
            "phone": data["phone"],
            "session": final_session,
            "api_id": DEFAULT_API_ID,
            "api_hash": DEFAULT_API_HASH
        })
        await state.clear()
        await message.answer("✅ **تم حفظ الرقم وتفعليه في المتجر بنجاح!** 🎉")
    except Exception as e:
        await state.clear()
        await message.answer(f"❌ كلمة المرور غير صحيحة: `{str(e)}`")

@dp.callback_query(F.data == "admin_ban_user")
async def admin_ban_user_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    await state.set_state(States.waiting_for_ban_id)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
    await callback.message.edit_text("🚫 أرسل **آي دي (User ID)** المستخدم المراد حظره:", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_ban_id)
async def process_ban_user(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ يرجى إدخال آي دي صحيح:")
        return
    target_id = int(message.text.strip())
    if target_id not in MEMORY_USERS:
        MEMORY_USERS[target_id] = {"user_id": target_id, "balance": 0.0, "language": "ar"}
    MEMORY_USERS[target_id]["banned"] = True
    await state.clear()
    await message.answer(f"✅ تم حظر المستخدم `{target_id}` بنجاح.")

@dp.callback_query(F.data == "admin_unban_user")
async def admin_unban_user_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    await state.set_state(States.waiting_for_unban_id)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
    await callback.message.edit_text("✅ أرسل **آي دي (User ID)** لرفع الحظر عنه:", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_unban_id)
async def process_unban_user(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ يرجى إدخال آي دي صحيح:")
        return
    target_id = int(message.text.strip())
    if target_id in MEMORY_USERS:
        MEMORY_USERS[target_id]["banned"] = False
    await state.clear()
    await message.answer(f"✅ تم رفع الحظر عن المستخدم `{target_id}`.")

@dp.callback_query(F.data == "admin_change_star_price")
async def admin_change_star_price(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    current_price = CONFIG_DATA.get("star_price", 0.01)
    await state.set_state(States.waiting_for_star_price)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
    await callback.message.edit_text(f"⭐ السعر الحالي للنجمة هو: `${current_price}`\n\nأرسل السعر الجديد بالدولار:", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_star_price)
async def process_star_price(message: Message, state: FSMContext):
    try:
        new_price = float(message.text.strip().replace("$", ""))
    except ValueError:
        await message.answer("❌ أرسل رقماً صحيحاً:")
        return
    CONFIG_DATA["star_price"] = new_price
    await state.clear()
    await message.answer(f"✅ **تم تحديث سعر النجمة ليصبح:** `${new_price}`")

@dp.callback_query(F.data == "admin_manage_nums")
async def admin_manage_nums(callback: CallbackQuery):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    if not MEMORY_NUMBERS:
        await callback.answer("❌ لا توجد أرقام مضافة حالياً.", show_alert=True)
        return
        
    buttons = []
    for data in MEMORY_NUMBERS:
        num_id = data["num_id"]
        buttons.append([
            InlineKeyboardButton(text=f"✏️ {data['name']}", callback_data=f"edit_name_{num_id}"),
            InlineKeyboardButton(text=f"💵 ${data['price']}", callback_data=f"edit_price_{num_id}"),
            InlineKeyboardButton(text=f"🗑 حذف", callback_data=f"del_num_{num_id}")
        ])
    buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")])
    await callback.message.edit_text("⚙️ إدارة الأرقام المضافة:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("del_num_"))
async def process_del_num(callback: CallbackQuery):
    num_id = callback.data.replace("del_num_", "")
    global MEMORY_NUMBERS
    MEMORY_NUMBERS = [n for n in MEMORY_NUMBERS if n["num_id"] != num_id]
    await callback.answer("✅ تم الحذف بنجاح!", show_alert=True)
    await admin_manage_nums(callback)

@dp.callback_query(F.data.startswith("edit_price_"))
async def process_edit_num_price(callback: CallbackQuery, state: FSMContext):
    num_id = callback.data.replace("edit_price_", "")
    await state.set_state(States.waiting_for_new_price)
    await state.update_data(edit_num_id=num_id)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_manage_nums")]])
    await callback.message.edit_text("💵 أرسل السعر الجديد بالدولار:", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_new_price)
async def save_new_num_price(message: Message, state: FSMContext):
    try:
        new_price = float(message.text.strip().replace("$", ""))
    except ValueError:
        await message.answer("❌ أدخل سعراً صحيحاً:")
        return
    data = await state.get_data()
    num_id = data.get("edit_num_id")
    for n in MEMORY_NUMBERS:
        if n["num_id"] == num_id:
            n["price"] = new_price
    await state.clear()
    await message.answer(f"✅ **تم تحديث السعر إلى `${new_price}` بنجاح!**")

@dp.callback_query(F.data.startswith("edit_name_"))
async def process_edit_num_name(callback: CallbackQuery, state: FSMContext):
    num_id = callback.data.replace("edit_name_", "")
    await state.set_state(States.waiting_for_new_name)
    await state.update_data(edit_num_id=num_id)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_manage_nums")]])
    await callback.message.edit_text("🏷 أرسل الاسم الجديد للرقم:", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_new_name)
async def save_new_num_name(message: Message, state: FSMContext):
    new_name = message.text.strip()
    data = await state.get_data()
    num_id = data.get("edit_num_id")
    for n in MEMORY_NUMBERS:
        if n["num_id"] == num_id:
            n["name"] = new_name
    await state.clear()
    await message.answer(f"✅ **تم تحديث الاسم إلى:** `{new_name}` بنجاح!")

@dp.callback_query(F.data == "buy_number_menu")
async def buy_number_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_doc = MEMORY_USERS.get(user_id, {})
    if user_doc.get("banned", False):
        await callback.answer("❌ أنت محظور.", show_alert=True)
        return
    lang = user_doc.get("language", "ar")
    purchased_ids = [p["number_id"] for p in MEMORY_PURCHASES if p["user_id"] == user_id]
    
    buttons = []
    for data in MEMORY_NUMBERS:
        num_id = data["num_id"]
        if num_id not in purchased_ids:
            buttons.append([InlineKeyboardButton(text=f"{data['name']} - ${data['price']:.2f}", callback_data=f"buy_country_{num_id}")])
    
    if lang == 'en':
        buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="main_menu")])
        text_msg = "🌍 Choose a country to buy a number:\n\n⚠️ **Important:** No compensation if logged out."
    else:
        buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")])
        text_msg = "🌍 اختر الدولة لشراء الرقم:\n\n⚠️ **تنبيه:** لا يوجد تعويض في حال تسجيل الخروج."

    await callback.message.edit_text(text_msg, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
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
    
    if user_id not in MEMORY_USERS:
        MEMORY_USERS[user_id] = {"balance": 0.0, "language": "ar"}
    balance = MEMORY_USERS[user_id].get("balance", 0.0)
    
    if balance < data['price']:
        await callback.answer("❌ رصيدك غير كافي!", show_alert=True)
        return
        
    MEMORY_USERS[user_id]["balance"] -= data['price']
    MEMORY_PURCHASES.append({"user_id": user_id, "number_id": num_id})
    
    lang = MEMORY_USERS[user_id].get("language", "ar")
    await callback.answer("⏳ جاري جلب الكود...", show_alert=False)
    otp_text = await fetch_otp_async(data["session"], data["api_id"], data["api_hash"], lang)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 طلب كود (OTP)", callback_data=f"get_otp_{num_id}")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])
    await callback.message.edit_text(f"🎉 **تم الشراء بنجاح!**\n\n📱 **الرقم:** `{data['phone']}`\n\n📥 **حالة الكود:**\n{otp_text}", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("get_otp_"))
async def get_otp_callback(callback: CallbackQuery):
    num_id = callback.data.replace("get_otp_", "")
    data = next((n for n in MEMORY_NUMBERS if n["num_id"] == num_id), None)
    user_id = callback.from_user.id
    lang = MEMORY_USERS.get(user_id, {}).get("language", "ar")
    
    await callback.answer("⏳ جاري جلب الكود...", show_alert=False)
    otp_text = await fetch_otp_async(data["session"], data["api_id"], data["api_hash"], lang)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 طلب كود (OTP)", callback_data=f"get_otp_{num_id}")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])
    try:
        await callback.message.edit_text(f"📱 **الرقم:** `{data['phone']}`\n\n📥 **حالة الكود:**\n{otp_text}", reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data == "my_account")
async def my_account(callback: CallbackQuery):
    user_id = callback.from_user.id
    balance = MEMORY_USERS.get(user_id, {}).get("balance", 0.0)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]])
    await callback.message.edit_text(f"🆔 المعرف: `{user_id}`\n💵 الرصيد المتاح: `${balance:.2f}`", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "claim_bonus")
async def claim_bonus(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in MEMORY_USERS:
        MEMORY_USERS[user_id] = {"balance": 0.0, "language": "ar"}
    user_doc = MEMORY_USERS[user_id]
    last_bonus_str = user_doc.get("last_bonus")
    
    now = datetime.now()
    if last_bonus_str:
        if now - datetime.fromisoformat(last_bonus_str) < timedelta(hours=24):
            await callback.answer("❌ لقد حصلت على هديتك اليومية مسبقاً!", show_alert=True)
            return
            
    MEMORY_USERS[user_id]["balance"] += BONUS_AMOUNT
    MEMORY_USERS[user_id]["last_bonus"] = now.isoformat()
    
    await callback.answer(f"🎉 تم إضافة ${BONUS_AMOUNT:.2f} بنجاح!", show_alert=True)
    text, keyboard = await get_main_keyboard(user_id)
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
    if sender_id not in MEMORY_USERS:
        MEMORY_USERS[sender_id] = {"balance": 0.0}
    sender_balance = MEMORY_USERS[sender_id].get("balance", 0.0)
    
    if sender_balance < amount:
        await message.answer("❌ رصيدك الحالي لا يكفي!")
        await state.clear()
        return
        
    data = await state.get_data()
    recipient_id = data.get("recipient_id")
    if recipient_id not in MEMORY_USERS:
        await message.answer("❌ المستخدم غير مسجل في البوت.")
        await state.clear()
        return
        
    MEMORY_USERS[sender_id]["balance"] -= amount
    MEMORY_USERS[recipient_id]["balance"] += amount
    await state.clear()
    await message.answer(f"✅ تم تحويل `${amount:.2f}` بنجاح إلى المستخدم `{recipient_id}`!")

@dp.callback_query(F.data == "recharge_menu")
async def recharge_menu(callback: CallbackQuery, state: FSMContext):
    star_price = CONFIG_DATA.get("star_price", 0.01)
    await state.set_state(States.waiting_for_stars_count)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]])
    await callback.message.edit_text(f"أرسل عدد النجوم التي تريد شحنها (النجمة الواحدة = ${star_price}):", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.message(States.waiting_for_stars_count)
async def process_stars(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("أدخل أرقام صحيحة فقط:")
        return
    stars_count = int(message.text.strip())
    star_price = CONFIG_DATA.get("star_price", 0.01)
    added = stars_count * star_price
    await state.clear()
    await bot.send_invoice(
        chat_id=message.chat.id,
        title=f"شحن {stars_count} نجمة",
        description=f"الحصول على ${added:.2f} رصيد",
        payload=f"recharge_{stars_count}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"{stars_count} Stars", amount=stars_count)],
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
        star_price = CONFIG_DATA.get("star_price", 0.01)
        added = stars * star_price
        user_id = message.from_user.id
        if user_id not in MEMORY_USERS:
            MEMORY_USERS[user_id] = {"balance": 0.0}
        MEMORY_USERS[user_id]["balance"] += added
        await message.answer(f"🎉 تم شحن `${added:.2f}` بنجاح إلى رصيدك!")

async def fetch_otp_async(session_str, api_id, api_hash, lang='ar'):
    if not session_str:
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
            return "⏳ لم يصل الكود بعد، اضغط على زر طلب كود مجدداً."
        for msg in messages:
            if msg.text:
                otp_match = re.search(r'\b\d{5,6}\b', msg.text)
                if otp_match:
                    return f"🔑 **كود التحقق:** `{otp_match.group(0)}`"
        return "⏳ لم يصل كود تفعيل جديد بعد."
    except Exception as e:
        return f"❌ خطأ في الاتصال: `{str(e)}`"

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
