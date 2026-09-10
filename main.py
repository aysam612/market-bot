import os
import re
import json
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

# توكن البوت
BOT_TOKEN = "8896024185:AAGdsd0J6iCt2ipEss3oYi18tPUwOKtobCI"

DEFAULT_ADMIN_USERNAME = "aaysam"
DEFAULT_ADMIN_USER_ID = 8863784148

REQUIRED_CHANNEL = "VPP8P"
BONUS_AMOUNT = 0.01

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

DB_FILE = "bot_data.json"

def load_db():
    if not os.path.exists(DB_FILE):
        default_data = {
            "config": {
                "admin_id": DEFAULT_ADMIN_USER_ID,
                "admin_username": DEFAULT_ADMIN_USERNAME,
                "star_price": 0.01  # سعر النجمة سنت واحد
            },
            "users": {
                str(DEFAULT_ADMIN_USER_ID): {
                    "user_id": DEFAULT_ADMIN_USER_ID,
                    "balance": 10000.0,
                    "language": "ar"
                }
            },
            "purchases": [],
            "buttons": [],
            "numbers": {
                "1": {
                    "country": "usa", 
                    "name": "🇺🇸 أمريكا", 
                    "price": 3.00, 
                    "phone": "+13526419211",
                    "session": "1AZWarzYBu5KAcXua9CNUuBPNtCE_7qKjZSrPCW8oTglmRjTeiqir6y6P253w6ckdo01lcaAnL1vNx0OMBxDWoCTGTG7xGWdWUor7J8Tde_bTf2Qqpcf5GFquiqcNFudvsbYm1UdvzIQwaUbByP7rFr3tnF6nlfh56QEr3Xqv9PyKBlXSDYK2hMLfSwy6Gh-F0J5CUerfi6qOArHG2XzPzx5rgN8DNC7yPDIgbQiCmU7XLAniXpYa4CPH0x89aLYRh395cRkm0mbwWyuJQo3wOnulNW-JvPB3ctEMGFkVk9LqIhv3rOKoy0k_qLJZHn6Sn5qgjadwGmicP1rVTMeW8TY5AkXnE_w=",
                    "api_id": 19812985, 
                    "api_hash": "b766d755a6934927dc09bc3abf878908"
                },
                "2": {
                    "country": "colombia", 
                    "name": "🇨🇴 كولومبيا", 
                    "price": 1.00, 
                    "phone": "+573144500501",
                    "session": "1AZWarzYBux1fG4UzALVMfes5Rm7zDo6DU75dOfYl5vVMvMSb_AG3atest_ZV-TbdURuU-GvbraP9buCthcZ0wLcZxvlIz4IrgQKxzrykNL4W2bb0VPlDo4BDlAR7zG_x4tTaBuT_29nuSgLeaJohStKc1XTFBxRHk5uPyy3xfRH667rGIuu5n1ZUoD7hsDaCO519Qjm6zD9EOT38MaIcTVXImaHDILPitFdHHNv9FRDNUNE1sr3DDvfroeN7VB5P2jkpWNmOWquW7rWUOry70CATSuSxHSCAQi3jERulu-ChZ9XyQy0DeHIgfGsTkX1IfNMpkRkw4B7RbLs78B6yQSpf6at8v-M=",
                    "api_id": 39585443, 
                    "api_hash": "ad1eb1cdc57ef6913c531da5e4163256"
                }
            }
        }
        save_db(default_data)
        return default_data
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "numbers" not in data:
                data["numbers"] = {}
            if "star_price" not in data.get("config", {}):
                if "config" not in data: data["config"] = {}
                data["config"]["star_price"] = 0.01
            return data
    except Exception:
        return {"config": {"star_price": 0.01}, "users": {}, "purchases": [], "buttons": [], "numbers": {}}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

class States(StatesGroup):
    waiting_for_stars_count = State()
    waiting_for_transfer_id = State()
    waiting_for_transfer_amount = State()
    waiting_for_new_admin_id = State()
    waiting_for_new_admin_username = State()
    waiting_for_btn_name = State()
    waiting_for_btn_url = State()
    # حالات إدارة الأرقام الجديدة
    waiting_for_num_id = State()
    waiting_for_num_name = State()
    waiting_for_num_price = State()
    waiting_for_num_phone = State()
    waiting_for_num_session = State()
    waiting_for_num_api_id = State()
    waiting_for_num_api_hash = State()
    # حالة تعديل السعر
    waiting_for_new_price = State()
    # حالة تعديل سعر النجمة
    waiting_for_star_price = State()

async def get_current_admin():
    db = load_db()
    config = db.get("config", {})
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

def get_user_language(user_id: int) -> str:
    db = load_db()
    users = db.get("users", {})
    user = users.get(str(user_id))
    return user.get("language", "ar") if user else "ar"

async def get_main_keyboard(user_id):
    admin_id, _ = await get_current_admin()
    db = load_db()
    users = db.get("users", {})
    user = users.get(str(user_id), {})
    balance = user.get("balance", 0.0)
    lang = user.get("language", "ar")
    
    custom_buttons = db.get("buttons", [])
    
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
    db = load_db()
    current_lang = get_user_language(user_id)
    new_lang = 'en' if current_lang == 'ar' else 'ar'
    if str(user_id) in db["users"]:
        db["users"][str(user_id)]["language"] = new_lang
        save_db(db)
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

    db = load_db()
    if str(user_id) not in db["users"]:
        initial_balance = 10000.0 if user_id == admin_id else 0.0
        db["users"][str(user_id)] = {
            "user_id": user_id,
            "balance": initial_balance,
            "referred_by": referred_by,
            "language": "ar"
        }
        if referred_by and user_id != admin_id and str(referred_by) in db["users"]:
            db["users"][str(referred_by)]["balance"] += BONUS_AMOUNT
        save_db(db)

    text, keyboard = await get_main_keyboard(user_id)
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery, state: FSMContext):
    user = callback.from_user
    user_id = user.id
    admin_id, _ = await get_current_admin()
    if await check_subscription(user_id):
        try:
            await callback.message.delete()
        except Exception:
            pass
        db = load_db()
        if str(user_id) not in db["users"]:
            initial_balance = 10000.0 if user_id == admin_id else 0.0
            db["users"][str(user_id)] = {"user_id": user_id, "balance": initial_balance, "language": "ar"}
            save_db(db)
        text, keyboard = await get_main_keyboard(user_id)
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await callback.answer("❌ لم تقم بالاشتراك في القناة بعد!", show_alert=True)

@dp.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    text, keyboard = await get_main_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass
    await callback.answer()

# --- لوحة التحكم الشاملة للآدمن ---
@dp.callback_query(F.data == "admin_panel_main")
@dp.message(Command("admin"))
async def admin_panel_handler(event):
    if isinstance(event, CallbackQuery):
        user_id = event.from_user.id
        message = event.message
    else:
        user_id = event.from_user.id
        message = event
        
    admin_id, admin_username = await get_current_admin()
    if user_id != admin_id:
        if isinstance(event, CallbackQuery):
            await event.answer("عذراً، هذه اللوحة مخصصة لمالك البوت فقط! ❌", show_alert=True)
        else:
            await message.answer("عذراً، هذه اللوحة مخصصة لمالك البوت فقط! ❌")
        return
        
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ إضافة رقم جديد للمتجر", callback_data="admin_add_num")],
        [InlineKeyboardButton(text="✏️ تعديل سعر أو حذف رقم", callback_data="admin_manage_nums")],
        [InlineKeyboardButton(text="⭐ تعديل سعر النجمة (1 سنت حالياً)", callback_data="admin_change_star_price")],
        [InlineKeyboardButton(text="➕ إضافة زر مخصص", callback_data="admin_add_btn"), InlineKeyboardButton(text="🗑 حذف زر مخصص", callback_data="admin_del_btn")],
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

# --- إدارة سعر النجمة ---
@dp.callback_query(F.data == "admin_change_star_price")
async def admin_change_star_price(callback: CallbackQuery, state: FSMContext):
    admin_id, _ = await get_current_admin()
    if callback.from_user.id != admin_id:
        return
    db = load_db()
    current_price = db.get("config", {}).get("star_price", 0.01)
    await state.set_state(States.waiting_for_star_price)
    await callback.message.edit_text(f"⭐ السعر الحالي للنجمة الواحدة هو: `${current_price}`\n\nأرسل السعر الجديد للنجمة الواحدة بالدولار (مثال: `0.01` أو `0.02`):")
    await callback.answer()

@dp.message(States.waiting_for_star_price)
async def process_star_price(message: Message, state: FSMContext):
    try:
        new_price = float(message.text.strip().replace("$", ""))
    except ValueError:
        await message.answer("❌ يرجى إدخال رقم صحيح:")
        return
    db = load_db()
    db["config"]["star_price"] = new_price
    save_db(db)
    await state.clear()
    await message.answer(f"✅ **تم تحديث سعر النجمة بنجاح ليصبح:** `${new_price}`", parse_mode="Markdown")

# --- إضافة رقم جديد عبر الفويس/الخطوات المتتالية ---
@dp.callback_query(F.data == "admin_add_num")
async def admin_add_num(callback: CallbackQuery, state: FSMContext):
    admin_id, _ = await get_current_admin()
    if callback.from_user.id != admin_id:
        return
    await state.set_state(States.waiting_for_num_id)
    await callback.message.edit_text("🔢 أرسل **معرف الرقم (ID)** كرقُم فريد (مثال: `3` أو `usa2`):")
    await callback.answer()

@dp.message(States.waiting_for_num_id)
async def proc_num_id(message: Message, state: FSMContext):
    await state.update_data(num_id=message.text.strip())
    await state.set_state(States.waiting_for_num_name)
    await message.answer("🏷 أرسل اسم الدولة مع العلم (مثال: `🇫🇷 فرنسا`):")

@dp.message(States.waiting_for_num_name)
async def proc_num_name(message: Message, state: FSMContext):
    await state.update_data(num_name=message.text.strip())
    await state.set_state(States.waiting_for_num_price)
    await message.answer("💵 أرسل سعر الرقم بالدولار (مثال: `2.50`):")

@dp.message(States.waiting_for_num_price)
async def proc_num_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip().replace("$", ""))
    except ValueError:
        await message.answer("❌ أدخل سعراً صحيحاً:")
        return
    await state.update_data(num_price=price)
    await state.set_state(States.waiting_for_num_phone)
    await message.answer("📱 أرسل رقم الهاتف مع مفتاح الدولة (مثال: `+33123456789`):")

@dp.message(States.waiting_for_num_phone)
async def proc_num_phone(message: Message, state: FSMContext):
    await state.update_data(num_phone=message.text.strip())
    await state.set_state(States.waiting_for_num_session)
    await message.answer("🔑 أرسل **جلسة التليثون (StringSession)** الخاصة بالحساب:")

@dp.message(States.waiting_for_num_session)
async def proc_num_session(message: Message, state: FSMContext):
    await state.update_data(num_session=message.text.strip())
    await state.set_state(States.waiting_for_num_api_id)
    await message.answer("🆔 أرسل **API_ID** الخاص بالتطبيق (أرقام فقط):")

@dp.message(States.waiting_for_num_api_id)
async def proc_num_api_id(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ يجب أن يكون API_ID أرقاماً فقط:")
        return
    await state.update_data(num_api_id=int(message.text.strip()))
    await state.set_state(States.waiting_for_num_api_hash)
    await message.answer("🔒 أرسل **API_HASH** الخاص بالتطبيق:")

@dp.message(States.waiting_for_num_api_hash)
async def proc_num_api_hash(message: Message, state: FSMContext):
    data = await state.get_data()
    num_id = data["num_id"]
    
    db = load_db()
    db["numbers"][num_id] = {
        "country": "custom",
        "name": data["num_name"],
        "price": data["num_price"],
        "phone": data["num_phone"],
        "session": data["num_session"],
        "api_id": data["num_api_id"],
        "api_hash": message.text.strip()
    }
    save_db(db)
    await state.clear()
    await message.answer(f"✅ **تمت إضافة الرقم ودولته بنجاح إلى المتجر!**", parse_mode="Markdown")

# --- تعديل أو حذف الأرقام ---
@dp.callback_query(F.data == "admin_manage_nums")
async def admin_manage_nums(callback: CallbackQuery):
    admin_id, _ = await get_current_admin()
    if callback.from_user.id != admin_id:
        return
    db = load_db()
    numbers = db.get("numbers", {})
    if not numbers:
        await callback.answer("❌ لا توجد أرقام مضافة في المتجر حالياً.", show_alert=True)
        return
        
    buttons = []
    for num_id, data in numbers.items():
        buttons.append([
            InlineKeyboardButton(text=f"✏️ تعديل سعر: {data['name']} (${data['price']})", callback_data=f"edit_num_{num_id}"),
            InlineKeyboardButton(text=f"🗑 حذف", callback_data=f"del_num_{num_id}")
        ])
    buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")])
    await callback.message.edit_text("⚙️ اختر الرقم الذي تريد تعديل سعره أو حذفه:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("del_num_"))
async def process_del_num(callback: CallbackQuery):
    num_id = callback.data.replace("del_num_", "")
    db = load_db()
    if num_id in db.get("numbers", {}):
        del db["numbers"][num_id]
        save_db(db)
    await callback.answer("✅ تم حذف الرقم بنجاح!", show_alert=True)
    await admin_manage_nums(callback)

@dp.callback_query(F.data.startswith("edit_num_"))
async def process_edit_num_price(callback: CallbackQuery, state: FSMContext):
    num_id = callback.data.replace("edit_num_", "")
    await state.set_state(States.waiting_for_new_price)
    await state.update_data(edit_num_id=num_id)
    await callback.message.edit_text("💵 أرسل السعر الجديد لهذا الرقم بالدولار (مثال: `2.00`):")
    await callback.answer()

@dp.message(States.waiting_for_new_price)
async def save_new_num_price(message: Message, state: FSMContext):
    try:
        new_price = float(message.text.strip().replace("$", ""))
    except ValueError:
        await message.answer("❌ أدخل سعراً صحيحاً:")
        return
    data = await state.get_data()
    num_id = data["edit_num_id"]
    
    db = load_db()
    if num_id in db.get("numbers", {}):
        db["numbers"][num_id]["price"] = new_price
        save_db(db)
    await state.clear()
    await message.answer(f"✅ **تم تحديث سعر الرقم بنجاح إلى `${new_price}`**", parse_mode="Markdown")

# --- إعدادات المالك والزر المخصص ---
@dp.callback_query(F.data == "admin_change_settings")
async def admin_change_settings(callback: CallbackQuery, state: FSMContext):
    admin_id, _ = await get_current_admin()
    if callback.from_user.id != admin_id:
        return
    await state.set_state(States.waiting_for_new_admin_id)
    await callback.message.edit_text("⚙️ أرسل الآن **الآي دي (ID)** الجديد للمالك (أرقام فقط):")
    await callback.answer()

@dp.message(States.waiting_for_new_admin_id)
async def process_new_admin_id(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ يرجى إدخال آي دي صحيح مكون من أرقام فقط:")
        return
    await state.update_data(new_admin_id=int(message.text.strip()))
    await state.set_state(States.waiting_for_new_admin_username)
    await message.answer("👤 ممتاز. الآن أرسل **اليوزر (Username)** الجديد للمالك:")

@dp.message(States.waiting_for_new_admin_username)
async def process_new_admin_username(message: Message, state: FSMContext):
    data = await state.get_data()
    new_id = data.get("new_admin_id")
    new_uname = message.text.strip()
    if not new_uname.startswith("@"):
        new_uname = "@" + new_uname
    db = load_db()
    db["config"]["admin_id"] = new_id
    db["config"]["admin_username"] = new_uname
    save_db(db)
    await state.clear()
    await message.answer(f"✅ **تم تحديث بيانات المالك بنجاح محلياً!**\n\n👤 اليوزر: {new_uname}\n🆔 الآي دي: `{new_id}`", parse_mode="Markdown")

@dp.callback_query(F.data == "admin_add_btn")
async def admin_add_btn(callback: CallbackQuery, state: FSMContext):
    admin_id, _ = await get_current_admin()
    if callback.from_user.id != admin_id:
        return
    await state.set_state(States.waiting_for_btn_name)
    await callback.message.edit_text("🏷 أرسل الآن **اسم الزر** الجديد الذي سيظهر للمستخدمين بالأسفل:")
    await callback.answer()

@dp.message(States.waiting_for_btn_name)
async def process_btn_name(message: Message, state: FSMContext):
    await state.update_data(btn_name=message.text.strip())
    await state.set_state(States.waiting_for_btn_url)
    await message.answer("🔗 ممتاز. الآن أرسل **رابط (URL)** هذا الزر:")

@dp.message(States.waiting_for_btn_url)
async def process_btn_url(message: Message, state: FSMContext):
    data = await state.get_data()
    btn_name = data.get("btn_name")
    btn_url = message.text.strip()
    db = load_db()
    db["buttons"].append({"name": btn_name, "url": btn_url})
    save_db(db)
    await state.clear()
    await message.answer(f"✅ **تمت إضافة الزر بنجاح وسيظهر فوراً في واجهة البوت!**\n\n🏷 الاسم: {btn_name}\n🔗 الرابط: {btn_url}", parse_mode="Markdown")

@dp.callback_query(F.data == "admin_del_btn")
async def admin_del_btn(callback: CallbackQuery):
    admin_id, _ = await get_current_admin()
    if callback.from_user.id != admin_id:
        return
    db = load_db()
    custom_buttons = db.get("buttons", [])
    if not custom_buttons:
        await callback.answer("❌ لا توجد أزرار مخصصة لحذفها.", show_alert=True)
        return
    buttons_list = []
    for index, btn in enumerate(custom_buttons):
        buttons_list.append([InlineKeyboardButton(text=f"🗑 حذف: {btn['name']}", callback_data=f"del_btn_{index}")])
    buttons_list.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")])
    await callback.message.edit_text("🗑 اختر الزر الذي تريد حذفه:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons_list))
    await callback.answer()

@dp.callback_query(F.data.startswith("del_btn_"))
async def process_delete_btn(callback: CallbackQuery):
    index = int(callback.data.replace("del_btn_", ""))
    db = load_db()
    if "buttons" in db and len(db["buttons"]) > index:
        db["buttons"].pop(index)
        save_db(db)
    await callback.answer("✅ تم حذف الزر بنجاح!", show_alert=True)
    await admin_panel_handler(callback)

# --- متجر الأرقام والشراء ---
@dp.callback_query(F.data == "buy_number_menu")
async def buy_number_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    db = load_db()
    purchases = db.get("purchases", [])
    numbers_store = db.get("numbers", {})
    
    buttons = []
    for num_id, data in numbers_store.items():
        already_bought = any(p["user_id"] == user_id and p["number_id"] == num_id for p in purchases)
        if not already_bought:
            buttons.append([InlineKeyboardButton(text=f"{data['name']} - ${data['price']:.2f}", callback_data=f"buy_country_{num_id}")])
    
    if lang == 'en':
        buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="main_menu")])
        text_msg = "🌍 Choose a country to buy a number:\n\n⚠️ **Important Notice:** There is **no compensation** if you log out or if the number gets banned."
    else:
        buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")])
        text_msg = "🌍 اختر الدولة لشراء الرقم:\n\n⚠️ **تنبيه هام:** **لا يوجد تعويض بأي شكل من الأشكال** في حال تم تسجيل الخروج من الحساب أو حظره."

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text_msg, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_country_"))
async def buy_country_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    num_id = callback.data.replace("buy_country_", "")
    db = load_db()
    numbers_store = db.get("numbers", {})
    
    already_purchased = any(p["user_id"] == user_id and p["number_id"] == num_id for p in db.get("purchases", []))
    if already_purchased:
        await callback.answer("❌ لقد اشتريت هذا الرقم مسبقاً!", show_alert=True)
        return
        
    data = numbers_store.get(num_id)
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
    lang = get_user_language(user_id)
    num_id = callback.data.replace("buy_balance_", "")
    db = load_db()
    data = db.get("numbers", {}).get(num_id)
    
    user_doc = db["users"].get(str(user_id), {})
    balance = user_doc.get("balance", 0.0)
    
    if balance < data['price']:
        await callback.answer("❌ رصيدك غير كافي!", show_alert=True)
        return
        
    db["users"][str(user_id)]["balance"] -= data['price']
    db["purchases"].append({"user_id": user_id, "number_id": num_id})
    save_db(db)
    
    await callback.answer("⏳ جاري جلب الكود...", show_alert=False)
    otp_text = await fetch_otp_async(data["session"], data["api_id"], data["api_hash"], lang)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 طلب كود (OTP)", callback_data=f"get_otp_{num_id}")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])
    text_content = f"🎉 **تم الشراء بنجاح!**\n\n📱 **الرقم:** `{data['phone']}`\n\n📥 **حالة الكود:**\n{otp_text}"
    await callback.message.edit_text(text_content, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("get_otp_"))
async def get_otp_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    num_id = callback.data.replace("get_otp_", "")
    db = load_db()
    data = db.get("numbers", {}).get(num_id)
    
    await callback.answer("⏳ جاري جلب الكود...", show_alert=False)
    otp_text = await fetch_otp_async(data["session"], data["api_id"], data["api_hash"], lang)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 طلب كود (OTP)", callback_data=f"get_otp_{num_id}")],
        [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])
    text_content = f"📱 **الرقم:** `{data['phone']}`\n\n📥 **حالة الكود:**\n{otp_text}"
    try:
        await callback.message.edit_text(text_content, reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data == "my_account")
async def my_account(callback: CallbackQuery):
    user_id = callback.from_user.id
    db = load_db()
    user_doc = db["users"].get(str(user_id), {})
    balance = user_doc.get("balance", 0.0)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]])
    await callback.message.edit_text(f"🆔 المعرف: `{user_id}`\n💵 الرصيد المتاح: `${balance:.2f}`", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "claim_bonus")
async def claim_bonus(callback: CallbackQuery):
    user_id = callback.from_user.id
    db = load_db()
    user_doc = db["users"].get(str(user_id), {})
    last_bonus_str = user_doc.get("last_bonus")
    
    now = datetime.now()
    if last_bonus_str:
        if now - datetime.fromisoformat(last_bonus_str) < timedelta(hours=24):
            await callback.answer("❌ لقد حصلت على هديتك اليومية مسبقاً!", show_alert=True)
            return
            
    db["users"][str(user_id)]["balance"] += BONUS_AMOUNT
    db["users"][str(user_id)]["last_bonus"] = now.isoformat()
    save_db(db)
    
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
    db = load_db()
    sender_balance = db["users"].get(str(sender_id), {}).get("balance", 0.0)
    
    if sender_balance < amount:
        await message.answer("❌ رصيدك الحالي لا يكفي!")
        await state.clear()
        return
        
    data = await state.get_data()
    recipient_id = data.get("recipient_id")
    if str(recipient_id) not in db["users"]:
        await message.answer("❌ المستخدم غير مسجل في البوت.")
        await state.clear()
        return
        
    db["users"][str(sender_id)]["balance"] -= amount
    db["users"][str(recipient_id)]["balance"] += amount
    save_db(db)
    await state.clear()
    await message.answer(f"✅ تم تحويل `${amount:.2f}` بنجاح إلى المستخدم `{recipient_id}`!", parse_mode="Markdown")

@dp.callback_query(F.data == "recharge_menu")
async def recharge_menu(callback: CallbackQuery, state: FSMContext):
    db = load_db()
    star_price = db.get("config", {}).get("star_price", 0.01)
    await state.set_state(States.waiting_for_stars_count)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]])
    await callback.message.edit_text(f"أرسل عدد النجوم التي تريد شحنها (النجمة الواحدة = ${star_price}):\nمثال: `100` تعني 1 دولار (إذا كان السعر 1 سنت)", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.message(States.waiting_for_stars_count)
async def process_stars(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("أدخل أرقام صحيحة فقط:")
        return
    stars_count = int(message.text.strip())
    db = load_db()
    star_price = db.get("config", {}).get("star_price", 0.01)
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
        db = load_db()
        star_price = db.get("config", {}).get("star_price", 0.01)
        added = stars * star_price
        user_id = message.from_user.id
        if str(user_id) in db["users"]:
            db["users"][str(user_id)]["balance"] += added
            save_db(db)
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
        return f"❌ خطأ في الاتصال: {str(e)}"

async def main():
    load_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
