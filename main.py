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
from motor.motor_asyncio import AsyncIOMotorClient

# التوكن الصحيح الخاص بك
BOT_TOKEN = "8896024185:AAF911IAOlt_2BS8HXXVaf8Zrxz3y9MKgkY"

# رابط مونجو الصحيح والمحدث (ضع كلمة المرور مكان <db_password>)
MONGO_URI = "mongodb+srv://aysamaysam426_db_user:<db_password>@aysam.ut0hpt5.mongodb.net/?appName=aysam"

# الاتصال بقاعدة البيانات
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["x9_store_db"]

# مجموعات البيانات (Collections)
users_collection = db["users"]
config_collection = db["config"]
purchases_collection = db["purchases"]
buttons_collection = db["buttons"]
numbers_collection = db["numbers"]

DEFAULT_API_ID = 12345678       
DEFAULT_API_HASH = "your_api_hash_here"  

DEFAULT_ADMIN_USERNAME = "aaysam"
DEFAULT_ADMIN_USER_ID = 8863784148

REQUIRED_CHANNEL = "VPP8P"
BONUS_AMOUNT = 0.01

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

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

async def init_db():
    config = await config_collection.find_one({"_id": "main_config"})
    if not config:
        await config_collection.update_one(
            {"_id": "main_config"},
            {"$set": {"admin_id": DEFAULT_ADMIN_USER_ID, "admin_username": DEFAULT_ADMIN_USERNAME, "star_price": 0.01}},
            upsert=True
        )
    admin_user = await users_collection.find_one({"user_id": DEFAULT_ADMIN_USER_ID})
    if not admin_user:
        await users_collection.update_one(
            {"user_id": DEFAULT_ADMIN_USER_ID},
            {"$set": {"user_id": DEFAULT_ADMIN_USER_ID, "balance": 10000.0, "language": "ar", "banned": False}},
            upsert=True
        )

async def get_current_admin():
    config = await config_collection.find_one({"_id": "main_config"})
    if not config:
        return DEFAULT_ADMIN_USER_ID, DEFAULT_ADMIN_USERNAME
    return config.get("admin_id", DEFAULT_ADMIN_USER_ID), config.get("admin_username", DEFAULT_ADMIN_USERNAME)

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

async def get_user_language(user_id: int) -> str:
    user = await users_collection.find_one({"user_id": user_id})
    return user.get("language", "ar") if user else "ar"

async def get_main_keyboard(user_id):
    admin_id, _ = await get_current_admin()
    user = await users_collection.find_one({"user_id": user_id}) or {}
    balance = user.get("balance", 0.0)
    lang = user.get("language", "ar")
    
    custom_buttons = await buttons_collection.find().to_list(length=100)
    
    keyboard_buttons = [
        [InlineKeyboardButton(text="🛒 Buy Numbers Store" if lang == 'en' else "🛒 متجر الأرقام", callback_data="buy_number_menu")],
        [InlineKeyboardButton(text="⚡ My Account" if lang == 'en' else "⚡ حسابي", callback_data="my_account"), InlineKeyboardButton(text="🎁 Daily Bonus" if lang == 'en' else "🎁 هدية يومية ($0.01)", callback_data="claim_bonus")],
        [InlineKeyboardButton(text="💳 Recharge Stars" if lang == 'en' else "💳 شحن رصيد نجوم", callback_data="recharge_menu")],
        [InlineKeyboardButton(text="🤝 Ref Link" if lang == 'en' else "🤝 رابط إحالة", callback_data="ref_menu"), InlineKeyboardButton(text="💳 Transfer" if lang == 'en' else "💳 تحويل رصيد", callback_data="transfer_menu")],
    ]
    
    for btn in custom_buttons:
        keyboard_buttons.append([InlineKeyboardButton(text=btn["name"], url=btn["url"])])
        
    keyboard_buttons.append([InlineKeyboardButton(text="🌐 English" if lang == 'ar' else "🌐 العربية", callback_data="toggle_lang")])
    
    if user_id == admin_id:
        keyboard_buttons.append([InlineKeyboardButton(text="🛠 لوحة التحكم (Admin Panel)", callback_data="admin_panel_main")])
        
    _, admin_username = await get_current_admin()
    keyboard_buttons.append([InlineKeyboardButton(text="💬 Support" if lang == 'en' else "💬 الدعم الفني", url=f"https://t.me/{admin_username.replace('@', '')}")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    if lang == 'en':
        text_header = (
            "👋 **Welcome to X9 Store for Premium Numbers** 🌐!\n\n"
            f"🆔 `{user_id}`\n"
            f"💵 `${balance:.2f}`\n\n"
            "Choose what suits you from the menu 👇"
        )
    else:
        text_header = (
            "👋 أهلاً بك عزيزي في متجر X9 للأرقام المميزة 🌐!\n\n"
            f"🆔 `{user_id}`\n"
            f"💵 `${balance:.2f}`\n\n"
            "اختر ما يناسبك من القائمة 👇"
        )
    return text_header, keyboard

@dp.callback_query(F.data == "toggle_lang")
async def toggle_lang_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    current_lang = await get_user_language(user_id)
    new_lang = 'en' if current_lang == 'ar' else 'ar'
    await users_collection.update_one({"user_id": user_id}, {"$set": {"language": new_lang}}, upsert=True)
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
    admin_id, _ = await get_current_admin()
    
    user_doc = await users_collection.find_one({"user_id": user_id}) or {}
    if user_doc.get("banned", False):
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
        initial_balance = 10000.0 if user_id == admin_id else 0.0
        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "balance": initial_balance, "referred_by": referred_by, "language": "ar", "banned": False}},
            upsert=True
        )
        if referred_by and user_id != admin_id:
            await users_collection.update_one({"user_id": referred_by}, {"$inc": {"balance": BONUS_AMOUNT}})

    text, keyboard = await get_main_keyboard(user_id)
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery, state: FSMContext):
    user = callback.from_user
    user_id = user.id
    admin_id, _ = await get_current_admin()
    user_doc = await users_collection.find_one({"user_id": user_id}) or {}
    if user_doc.get("banned", False):
        await callback.answer("❌ أنت محظور من استخدام البوت.", show_alert=True)
        return

    if await check_subscription(user_id):
        try:
            await callback.message.delete()
        except Exception:
            pass
        if not user_doc:
            initial_balance = 10000.0 if user_id == admin_id else 0.0
            await users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"user_id": user_id, "balance": initial_balance, "language": "ar", "banned": False}},
                upsert=True
            )
        text, keyboard = await get_main_keyboard(user_id)
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await callback.answer("❌ لم تقم بالاشتراك في القناة بعد!", show_alert=True)

@dp.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    user_doc = await users_collection.find_one({"user_id": user_id}) or {}
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
        
    admin_id, admin_username = await get_current_admin()
    if user_id != admin_id:
        if isinstance(event, CallbackQuery):
            await event.answer("عذراً، هذه اللوحة مخصصة لمالك البوت فقط! ❌", show_alert=True)
        else:
            await message.answer("عذراً، هذه اللوحة مخصصة لمالك البوت فقط! ❌")
        return
        
    config = await config_collection.find_one({"_id": "main_config"}) or {}
    current_star_price = config.get("star_price", 0.01)

    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ إضافة رقم (بالرقم والكود مباشرة)", callback_data="admin_auto_add_num")],
        [InlineKeyboardButton(text="✏️ إدارة الأرقام (تعديل/حذف)", callback_data="admin_manage_nums")],
        [InlineKeyboardButton(text=f"⭐ تعديل سعر النجمة ({current_star_price} حالياً)", callback_data="admin_change_star_price")],
        [InlineKeyboardButton(text="➕ إضافة زر مخصص", callback_data="admin_add_btn"), InlineKeyboardButton(text="🗑 حذف زر مخصص", callback_data="admin_del_btn")],
        [InlineKeyboardButton(text="🚫 حظر مستخدم", callback_data="admin_ban_user"), InlineKeyboardButton(text="✅ رفع حظر مستخدم", callback_data="admin_unban_user")],
        [InlineKeyboardButton(text="⚙️ تغيير يوزر/آي دي المالك", callback_data="admin_change_settings")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])
    
    text = (
        f"🛠 **لوحة التحكم المركزية الشاملة:**\n"
        f"👤 المالك الحالي: `{admin_username}` (`{admin_id}`)\n\n"
        f"اختر الإجراء الذي ترغب بتنفيذه:"
    )
    
    if isinstance(event, CallbackQuery):
        await message.edit_text(text, reply_markup=builder, parse_mode="Markdown")
        await event.answer()
    else:
        await message.answer(text, reply_markup=builder, parse_mode="Markdown")

@dp.callback_query(F.data == "admin_auto_add_num")
async def admin_auto_add_num(callback: CallbackQuery, state: FSMContext):
    admin_id, _ = await get_current_admin()
    if callback.from_user.id != admin_id:
        return
    await state.set_state(States.waiting_for_auto_num_id)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
    await callback.message.edit_text("🔢 أرسل **معرف الرقم (ID)** كرمز فريد بالإنجليزية (مثال: `1` أو `usa`):", reply_markup=back_kb)
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
    await message.answer("💵 أرسل سعر الرقم بالدولار (مثال: `1.50`):")

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
        await numbers_collection.update_one(
            {"num_id": num_id},
            {"$set": {
                "num_id": num_id,
                "country": "auto",
                "name": data["num_name"],
                "price": data["num_price"],
                "phone": data["phone"],
                "session": final_session,
                "api_id": DEFAULT_API_ID,
                "api_hash": DEFAULT_API_HASH
            }},
            upsert=True
        )
        await state.clear()
        await message.answer("✅ **تم تسجيل الدخول وإضافة الرقم بنجاح إلى المتجر!** 🎉")
    except SessionPasswordNeededError:
        await state.set_state(States.waiting_for_auto_password)
        await message.answer("🔐 هذا الحساب محمي بـ **كلمة المرور**. أرسلها الآن:")
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
        await numbers_collection.update_one(
            {"num_id": num_id},
            {"$set": {
                "num_id": num_id,
                "country": "auto",
                "name": data["num_name"],
                "price": data["num_price"],
                "phone": data["phone"],
                "session": final_session,
                "api_id": DEFAULT_API_ID,
                "api_hash": DEFAULT_API_HASH
            }},
            upsert=True
        )
        await state.clear()
        await message.answer("✅ **تم حفظ الرقم وتفعليه في المتجر بنجاح!** 🎉")
    except Exception as e:
        await state.clear()
        await message.answer(f"❌ كلمة المرور غير صحيحة أو خطأ: `{str(e)}`")

@dp.callback_query(F.data == "admin_ban_user")
async def admin_ban_user_prompt(callback: CallbackQuery, state: FSMContext):
    admin_id, _ = await get_current_admin()
    if callback.from_user.id != admin_id:
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
    await users_collection.update_one({"user_id": target_id}, {"$set": {"banned": True}}, upsert=True)
    await state.clear()
    await message.answer(f"✅ تم حظر المستخدم `{target_id}` بنجاح.")

@dp.callback_query(F.data == "admin_unban_user")
async def admin_unban_user_prompt(callback: CallbackQuery, state: FSMContext):
    admin_id, _ = await get_current_admin()
    if callback.from_user.id != admin_id:
        return
    await state.set_state(States.waiting_for_unban_id)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
    await callback.message.edit_text("✅ أرسل **آي دي (User ID)** المستخدم لرفع الحظر عنه:", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_unban_id)
async def process_unban_user(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ يرجى إدخال آي دي صحيح:")
        return
    target_id = int(message.text.strip())
    await users_collection.update_one({"user_id": target_id}, {"$set": {"banned": False}})
    await state.clear()
    await message.answer(f"✅ تم رفع الحظر عن المستخدم `{target_id}`.")

@dp.callback_query(F.data == "admin_change_star_price")
async def admin_change_star_price(callback: CallbackQuery, state: FSMContext):
    admin_id, _ = await get_current_admin()
    if callback.from_user.id != admin_id:
        return
    config = await config_collection.find_one({"_id": "main_config"}) or {}
    current_price = config.get("star_price", 0.01)
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
    await config_collection.update_one({"_id": "main_config"}, {"$set": {"star_price": new_price}})
    await state.clear()
    await message.answer(f"✅ **تم تحديث سعر النجمة ليصبح:** `${new_price}`")

@dp.callback_query(F.data == "admin_manage_nums")
async def admin_manage_nums(callback: CallbackQuery):
    admin_id, _ = await get_current_admin()
    if callback.from_user.id != admin_id:
        return
    numbers = await numbers_collection.find().to_list(length=100)
    if not numbers:
        await callback.answer("❌ لا توجد أرقام مضافة.", show_alert=True)
        return
        
    buttons = []
    for data in numbers:
        num_id = data["num_id"]
        buttons.append([
            InlineKeyboardButton(text=f"✏️ اسم: {data['name']}", callback_data=f"edit_name_{num_id}"),
            InlineKeyboardButton(text=f"💵 سعر: ${data['price']}", callback_data=f"edit_price_{num_id}"),
            InlineKeyboardButton(text=f"🗑 حذف", callback_data=f"del_num_{num_id}")
        ])
    buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")])
    await callback.message.edit_text("⚙️ اختر ما تريد تعديله أو حذفه للرقم:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("del_num_"))
async def process_del_num(callback: CallbackQuery):
    num_id = callback.data.replace("del_num_", "")
    await numbers_collection.delete_one({"num_id": num_id})
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
    await numbers_collection.update_one({"num_id": num_id}, {"$set": {"price": new_price}})
    await state.clear()
    await message.answer(f"✅ **تم تحديث السعر إلى `${new_price}` بنجاح!**")

@dp.callback_query(F.data.startswith("edit_name_"))
async def process_edit_num_name(callback: CallbackQuery, state: FSMContext):
    num_id = callback.data.replace("edit_name_", "")
    await state.set_state(States.waiting_for_new_name)
    await state.update_data(edit_num_id=num_id)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_manage_nums")]])
    await callback.message.edit_text("🏷 أرسل الاسم الجديد للرقم (مثال: `🇺🇸 أمريكا مميز`):", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_new_name)
async def save_new_num_name(message: Message, state: FSMContext):
    new_name = message.text.strip()
    data = await state.get_data()
    num_id = data.get("edit_num_id")
    await numbers_collection.update_one({"num_id": num_id}, {"$set": {"name": new_name}})
    await state.clear()
    await message.answer(f"✅ **تم تحديث اسم الرقم إلى:** `{new_name}` بنجاح!")

@dp.callback_query(F.data == "admin_change_settings")
async def admin_change_settings(callback: CallbackQuery, state: FSMContext):
    admin_id, _ = await get_current_admin()
    if callback.from_user.id != admin_id:
        return
    await state.set_state(States.waiting_for_new_admin_id)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
    await callback.message.edit_text("⚙️ أرسل **آي دي (ID)** المالك الجديد:", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_new_admin_id)
async def process_new_admin_id(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ أرقام فقط:")
        return
    await state.update_data(new_admin_id=int(message.text.strip()))
    await state.set_state(States.waiting_for_new_admin_username)
    await message.answer("👤 أرسل **يوزر (Username)** المالك الجديد:")

@dp.message(States.waiting_for_new_admin_username)
async def process_new_admin_username(message: Message, state: FSMContext):
    data = await state.get_data()
    new_id = data.get("new_admin_id")
    new_uname = message.text.strip()
    if not new_uname.startswith("@"):
        new_uname = "@" + new_uname
    await config_collection.update_one({"_id": "main_config"}, {"$set": {"admin_id": new_id, "admin_username": new_uname}})
    await state.clear()
    await message.answer(f"✅ **تم تحديث بيانات المالك!**\n👤 {new_uname}\n🆔 `{new_id}`")

@dp.callback_query(F.data == "admin_add_btn")
async def admin_add_btn(callback: CallbackQuery, state: FSMContext):
    admin_id, _ = await get_current_admin()
    if callback.from_user.id != admin_id:
        return
    await state.set_state(States.waiting_for_btn_name)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
    await callback.message.edit_text("🏷 أرسل **اسم الزر** الجديد:", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_btn_name)
async def process_btn_name(message: Message, state: FSMContext):
    await state.update_data(btn_name=message.text.strip())
    await state.set_state(States.waiting_for_btn_url)
    await message.answer("🔗 أرسل **رابط (URL)** الزر:")

@dp.message(States.waiting_for_btn_url)
async def process_btn_url(message: Message, state: FSMContext):
    data = await state.get_data()
    await buttons_collection.insert_one({"name": data.get("btn_name"), "url": message.text.strip()})
    await state.clear()
    await message.answer("✅ **تمت إضافة الزر بنجاح!**")

@dp.callback_query(F.data == "admin_del_btn")
async def admin_del_btn(callback: CallbackQuery):
    admin_id, _ = await get_current_admin()
    if callback.from_user.id != admin_id:
        return
    custom_buttons = await buttons_collection.find().to_list(length=100)
    if not custom_buttons:
        await callback.answer("❌ لا توجد أزرار.", show_alert=True)
        return
    buttons_list = []
    for btn in custom_buttons:
        buttons_list.append([InlineKeyboardButton(text=f"🗑 حذف: {btn['name']}", callback_data=f"del_btn_{str(btn['_id'])}")])
    buttons_list.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")])
    await callback.message.edit_text("🗑 اختر الزر لحذفه:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons_list))
    await callback.answer()

@dp.callback_query(F.data.startswith("del_btn_"))
async def process_delete_btn(callback: CallbackQuery):
    from bson import ObjectId
    btn_id = callback.data.replace("del_btn_", "")
    try:
        await buttons_collection.delete_one({"_id": ObjectId(btn_id)})
    except Exception:
        pass
    await callback.answer("✅ تم الحذف بنجاح!", show_alert=True)
    await admin_panel_handler(callback)

@dp.callback_query(F.data == "buy_number_menu")
async def buy_number_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_doc = await users_collection.find_one({"user_id": user_id}) or {}
    if user_doc.get("banned", False):
        await callback.answer("❌ أنت محظور.", show_alert=True)
        return
    lang = user_doc.get("language", "ar")
    purchases = await purchases_collection.find({"user_id": user_id}).to_list(length=1000)
    purchased_ids = [p["number_id"] for p in purchases]
    
    numbers_store = await numbers_collection.find().to_list(length=100)
    buttons = []
    for data in numbers_store:
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
    user_id = callback.from_user.id
    num_id = callback.data.replace("buy_country_", "")
    data = await numbers_collection.find_one({"num_id": num_id})
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
    data = await numbers_collection.find_one({"num_id": num_id})
    
    user_doc = await users_collection.find_one({"user_id": user_id}) or {}
    balance = user_doc.get("balance", 0.0)
    
    if balance < data['price']:
        await callback.answer("❌ رصيدك غير كافي!", show_alert=True)
        return
        
    await users_collection.update_one({"user_id": user_id}, {"$inc": {"balance": -data['price']}})
    await purchases_collection.insert_one({"user_id": user_id, "number_id": num_id})
    
    lang = user_doc.get("language", "ar")
    await callback.answer("⏳ جاري جلب الكود...", show_alert=False)
    otp_text = await fetch_otp_async(data["session"], data["api_id"], data["api_hash"], lang)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 طلب كود (OTP)", callback_data=f"get_otp_{num_id}")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])
    await callback.message.edit_text(f"🎉 **تم الشراء بنجاح!**\n\n📱 **الرقم:** `{data['phone']}`\n\n📥 **حالة الكود:**\n{otp_text}", reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("get_otp_"))
async def get_otp_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    num_id = callback.data.replace("get_otp_", "")
    data = await numbers_collection.find_one({"num_id": num_id})
    user_doc = await users_collection.find_one({"user_id": user_id}) or {}
    lang = user_doc.get("language", "ar")
    
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
    user_doc = await users_collection.find_one({"user_id": user_id}) or {}
    balance = user_doc.get("balance", 0.0)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]])
    await callback.message.edit_text(f"🆔 المعرف: `{user_id}`\n💵 الرصيد المتاح: `${balance:.2f}`", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "claim_bonus")
async def claim_bonus(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_doc = await users_collection.find_one({"user_id": user_id}) or {}
    last_bonus_str = user_doc.get("last_bonus")
    
    now = datetime.now()
    if last_bonus_str:
        if now - datetime.fromisoformat(last_bonus_str) < timedelta(hours=24):
            await callback.answer("❌ لقد حصلت على هديتك اليومية مسبقاً!", show_alert=True)
            return
            
    await users_collection.update_one(
        {"user_id": user_id},
        {"$inc": {"balance": BONUS_AMOUNT}, "$set": {"last_bonus": now.isoformat()}},
        upsert=True
    )
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
    user_id = callback.from_user.id
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
    sender_doc = await users_collection.find_one({"user_id": sender_id}) or {}
    sender_balance = sender_doc.get("balance", 0.0)
    
    if sender_balance < amount:
        await message.answer("❌ رصيدك الحالي لا يكفي!")
        await state.clear()
        return
        
    data = await state.get_data()
    recipient_id = data.get("recipient_id")
    recipient_doc = await users_collection.find_one({"user_id": recipient_id})
    if not recipient_doc:
        await message.answer("❌ المستخدم غير مسجل في البوت.")
        await state.clear()
        return
        
    await users_collection.update_one({"user_id": sender_id}, {"$inc": {"balance": -amount}})
    await users_collection.update_one({"user_id": recipient_id}, {"$inc": {"balance": amount}})
    await state.clear()
    await message.answer(f"✅ تم تحويل `${amount:.2f}` بنجاح إلى المستخدم `{recipient_id}`!")

@dp.callback_query(F.data == "recharge_menu")
async def recharge_menu(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    config = await config_collection.find_one({"_id": "main_config"}) or {}
    star_price = config.get("star_price", 0.01)
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
    config = await config_collection.find_one({"_id": "main_config"}) or {}
    star_price = config.get("star_price", 0.01)
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
        config = await config_collection.find_one({"_id": "main_config"}) or {}
        star_price = config.get("star_price", 0.01)
        added = stars * star_price
        user_id = message.from_user.id
        await users_collection.update_one({"user_id": user_id}, {"$inc": {"balance": added}}, upsert=True)
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
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
