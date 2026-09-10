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

USA_NUMBER_PRICE = 3.00
COLOMBIA_NUMBER_PRICE = 1.00
BONUS_AMOUNT = 0.01
STAR_PRICE_USD = 0.02

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# نظام قاعدة البيانات المحلية (JSON)
DB_FILE = "bot_data.json"

def load_db():
    if not os.path.exists(DB_FILE):
        default_data = {
            "config": {
                "admin_id": DEFAULT_ADMIN_USER_ID,
                "admin_username": DEFAULT_ADMIN_USERNAME
            },
            "users": {
                str(DEFAULT_ADMIN_USER_ID): {
                    "user_id": DEFAULT_ADMIN_USER_ID,
                    "balance": 10000.0,
                    "language": "ar"
                }
            },
            "purchases": [],
            "buttons": []
        }
        save_db(default_data)
        return default_data
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"config": {}, "users": {}, "purchases": [], "buttons": []}

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

async def get_current_admin():
    db = load_db()
    config = db.get("config", {})
    return config.get("admin_id", DEFAULT_ADMIN_USER_ID), config.get("admin_username", DEFAULT_ADMIN_USERNAME)

NUMBERS_STORE = {
    "1": {
        "country": "usa", 
        "name": "🇺🇸 أمريكا", 
        "price": USA_NUMBER_PRICE, 
        "phone": "+13526419211",
        "session": "1AZWarzYBu5KAcXua9CNUuBPNtCE_7qKjZSrPCW8oTglmRjTeiqir6y6P253w6ckdo01lcaAnL1vNx0OMBxDWoCTGTG7xGWdWUor7J8Tde_bTf2Qqpcf5GFquiqcNFudvsbYm1UdvzIQwaUbByP7rFr3tnF6nlfh56QEr3Xqv9PyKBlXSDYK2hMLfSwy6Gh-F0J5CUerfi6qOArHG2XzPzx5rgN8DNC7yPDIgbQiCmU7XLAniXpYa4CPH0x89aLYRh395cRkm0mbwWyuJQo3wOnulNW-JvPB3ctEMGFkVk9LqIhv3rOKoy0k_qLJZHn6Sn5qgjadwGmicP1rVTMeW8TY5AkXnE_w=",
        "api_id": 19812985, 
        "api_hash": "b766d755a6934927dc09bc3abf878908"
    },
    "2": {
        "country": "colombia", 
        "name": "🇨🇴 كولومبيا", 
        "price": COLOMBIA_NUMBER_PRICE, 
        "phone": "+573144500501",
        "session": "1AZWarzYBux1fG4UzALVMfes5Rm7zDo6DU75dOfYl5vVMvMSb_AG3atest_ZV-TbdURuU-GvbraP9buCthcZ0wLcZxvlIz4IrgQKxzrykNL4W2bb0VPlDo4BDlAR7zG_x4tTaBuT_29nuSgLeaJohStKc1XTFBxRHk5uPyy3xfRH667rGIuu5n1ZUoD7hsDaCO519Qjm6zD9EOT38MaIcTVXImaHDILPitFdHHNv9FRDNUNE1sr3DDvfroeN7VB5P2jkpWNmOWquW7rWUOry70CATSuSxHSCAQi3jERulu-ChZ9XyQy0DeHIgfGsTkX1IfNMpkRkw4B7RbLs78B6yQSpf6at8v-M=",
        "api_id": 39585443, 
        "api_hash": "ad1eb1cdc57ef6913c531da5e4163256"
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

        if admin_id and user_id != admin_id:
            try:
                notif = f"🚨 مستخدم جديد دخل البوت!\n🆔 ID: `{user_id}`\n👤 الاسم: {user.full_name}"
                await bot.send_message(chat_id=admin_id, text=notif, parse_mode="Markdown")
            except Exception:
                pass

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
            db["users"][str(user_id)] = {
                "user_id": user_id,
                "balance": initial_balance,
                "language": "ar"
            }
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
        [InlineKeyboardButton(text="➕ إضافة زر جديد للبوت", callback_data="admin_add_btn")],
        [InlineKeyboardButton(text="🗑 حذف زر مخصص", callback_data="admin_del_btn")],
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
    await message.answer("👤 ممتاز. الآن أرسل **اليوزر (Username)** الجديد للمالك (مثال: `@username` أو بدون @):")

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
    await message.answer("🔗 ممتاز. الآن أرسل **رابط (URL)** هذا الزر (مثال: `https://t.me/...`):")

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

@dp.callback_query(F.data == "buy_number_menu")
async def buy_number_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    db = load_db()
    purchases = db.get("purchases", [])
    
    buttons = []
    for num_id, data in NUMBERS_STORE.items():
        already_bought = any(p["user_id"] == user_id and p["number_id"] == num_id for p in purchases)
        if not already_bought:
            buttons.append([InlineKeyboardButton(text=f"{data['name']} - ${data['price']:.2f}", callback_data=f"buy_country_{num_id}")])
    
    if lang == 'en':
        buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="main_menu")])
        text_msg = "🌍 Choose a country to buy a number:\n\n⚠️ **Important Notice:** There is **no compensation under any circumstances** if you log out of the account, or if the number is banned, pulled, or locked after purchase."
    else:
        buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")])
        text_msg = "🌍 اختر الدولة لشراء الرقم:\n\n⚠️ **تنبيه هام:** **لا يوجد تعويض بأي شكل من الأشكال** في حال تم تسجيل الخروج من الحساب، أو في حال تم سحب، قفل، أو حظر الرقم بعد إتمام الشراء."

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text_msg, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_country_"))
async def buy_country_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    num_id = callback.data.replace("buy_country_", "")
    
    db = load_db()
    already_purchased = any(p["user_id"] == user_id and p["number_id"] == num_id for p in db.get("purchases", []))
    if already_purchased:
        msg = "❌ You have already purchased this number!" if lang == 'en' else "❌ لقد اشتريت هذا الرقم مسبقاً!"
        await callback.answer(msg, show_alert=True)
        return
        
    data = NUMBERS_STORE.get(num_id)
    if not data:
        msg = "❌ Number not available." if lang == 'en' else "❌ الرقم غير متوفر."
        await callback.answer(msg, show_alert=True)
        return
    
    if lang == 'en':
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Confirm Purchase for ${data['price']:.2f}", callback_data=f"buy_balance_{num_id}")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="buy_number_menu")]
        ])
        await callback.message.edit_text(f"Country: {data['name']}\nPrice: **${data['price']:.2f}**\n\nDo you want to confirm the purchase?", reply_markup=keyboard, parse_mode="Markdown")
    else:
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
    data = NUMBERS_STORE.get(num_id)
    
    db = load_db()
    user_doc = db["users"].get(str(user_id), {})
    balance = user_doc.get("balance", 0.0)
    
    if balance < data['price']:
        msg = "❌ Insufficient balance!" if lang == 'en' else "❌ رصيدك غير كافي!"
        await callback.answer(msg, show_alert=True)
        return
        
    db["users"][str(user_id)]["balance"] -= data['price']
    db["purchases"].append({"user_id": user_id, "number_id": num_id})
    save_db(db)
    
    wait_msg = "⏳ Fetching code..." if lang == 'en' else "⏳ جاري جلب الكود..."
    await callback.answer(wait_msg, show_alert=False)
    otp_text = await fetch_otp_async(data["session"], data["api_id"], data["api_hash"], lang)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Request Code (OTP)" if lang=='en' else "🔄 طلب كود (OTP)", callback_data=f"get_otp_{num_id}")],
        [InlineKeyboardButton(text="🏠 Main Menu" if lang=='en' else "🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])
    text_content = (
        f"🎉 **Successfully Purchased!**\n\n📱 **Number:** `{data['phone']}`\n\n📥 **Code Status:**\n{otp_text}"
        if lang == 'en' else
        f"🎉 **تم الشراء بنجاح!**\n\n📱 **الرقم:** `{data['phone']}`\n\n📥 **حالة الكود:**\n{otp_text}"
    )
    await callback.message.edit_text(text_content, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("get_otp_"))
async def get_otp_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    num_id = callback.data.replace("get_otp_", "")
    data = NUMBERS_STORE.get(num_id)
    
    await callback.answer("⏳ جاري جلب الكود...", show_alert=False)
    otp_text = await fetch_otp_async(data["session"], data["api_id"], data["api_hash"], lang)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Request Code (OTP)" if lang=='en' else "🔄 طلب كود (OTP)", callback_data=f"get_otp_{num_id}")],
        [InlineKeyboardButton(text="🏠 Main Menu" if lang=='en' else "🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])
    text_content = f"📱 **Number:** `{data['phone']}`\n\n📥 **Code Status:**\n{otp_text}" if lang=='en' else f"📱 **الرقم:** `{data['phone']}`\n\n📥 **حالة الكود:**\n{otp_text}"
    try:
        await callback.message.edit_text(text_content, reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data == "my_account")
async def my_account(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    db = load_db()
    user_doc = db["users"].get(str(user_id), {})
    balance = user_doc.get("balance", 0.0)
    
    back_text = "🔙 Back" if lang == 'en' else "🔙 رجوع"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=back_text, callback_data="main_menu")]])
    text_content = f"🆔 ID: `{user_id}`\n💵 Available Balance: `${balance:.2f}`" if lang == 'en' else f"🆔 المعرف: `{user_id}`\n💵 الرصيد المتاح: `${balance:.2f}`"
    await callback.message.edit_text(text_content, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "claim_bonus")
async def claim_bonus(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    db = load_db()
    user_doc = db["users"].get(str(user_id), {})
    last_bonus_str = user_doc.get("last_bonus")
    
    now = datetime.now()
    if last_bonus_str:
        if now - datetime.fromisoformat(last_bonus_str) < timedelta(hours=24):
            msg = "❌ You have already claimed your daily bonus!" if lang == 'en' else "❌ لقد حصلت على هديتك اليومية مسبقاً!"
            await callback.answer(msg, show_alert=True)
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
    lang = get_user_language(user_id)
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    back_text = "🔙 Back" if lang == 'en' else "🔙 رجوع"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=back_text, callback_data="main_menu")]])
    text_content = f"🤝 **رابط الإحالة الخاص بك:**\n`{ref_link}`\n\nاحصل على **${BONUS_AMOUNT:.2f}** لكل شخص يسجل من رابطك!"
    await callback.message.edit_text(text_content, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "transfer_menu")
async def transfer_menu_handler(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    await state.set_state(States.waiting_for_transfer_id)
    back_text = "🔙 Back" if lang == 'en' else "🔙 رجوع"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=back_text, callback_data="main_menu")]])
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
    sender_doc = db["users"].get(str(sender_id), {})
    sender_balance = sender_doc.get("balance", 0.0)
    
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
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    await state.set_state(States.waiting_for_stars_count)
    back_text = "🔙 Back" if lang == 'en' else "🔙 رجوع"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=back_text, callback_data="main_menu")]])
    text_content = "أرسل عدد النجوم التي تريد شحنها (كل نجمة = 0.02 دولار):\nمثال: `50` تعني 1 دولار"
    await callback.message.edit_text(text_content, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.message(States.waiting_for_stars_count)
async def process_stars(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("أدخل أرقام صحيحة فقط:")
        return
    stars_count = int(message.text.strip())
    added = stars_count * STAR_PRICE_USD
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
        added = stars * STAR_PRICE_USD
        user_id = message.from_user.id
        
        db = load_db()
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
