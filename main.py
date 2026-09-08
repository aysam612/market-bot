import os
import re
import asyncio
import sqlite3
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
from pymongo import MongoClient

# توكن البوت
BOT_TOKEN = "8896024185:AAGdsd0J6iCt2ipEss3oYi18tPUwOKtobCI"

# رابط MongoDB Atlas الذي أنشأته
MONGO_URI = "mongodb+srv://aysamaysam426_db_user:MeBfCxpAl4AK2eG2@aysam.ut0hpt5.mongodb.net/?appName=aysam"

ADMIN_USERNAME = "aaysam"
ADMIN_USER_ID = 8863784148

REQUIRED_CHANNEL = "VPP8P"

USA_NUMBER_PRICE = 3.00
COLOMBIA_NUMBER_PRICE = 1.00
BONUS_AMOUNT = 0.01
STAR_PRICE_USD = 0.02

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# تهيئة اتصال MongoDB (بدلاً من sqlite3 المحلية لضمان عدم ضياع البيانات)
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["x9_store_db"]
users_collection = db["users"]
purchases_collection = db["user_purchases"]

class States(StatesGroup):
    waiting_for_stars_count = State()
    waiting_for_transfer_id = State()
    waiting_for_transfer_amount = State()

def init_db():
    # التأكد من وجود مستخدم الأدمن في قاعدة بيانات MongoDB
    if not users_collection.find_one({"user_id": ADMIN_USER_ID}):
        users_collection.insert_one({
            "user_id": ADMIN_USER_ID,
            "balance": 10000.0,
            "language": "ar"
        })

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
    user = users_collection.find_one({"user_id": user_id})
    return user.get("language", "ar") if user else "ar"

def get_main_keyboard(user_id):
    user = users_collection.find_one({"user_id": user_id})
    balance = user.get("balance", 0.0) if user else 0.0
    lang = user.get("language", "ar") if user else "ar"
    
    if lang == 'en':
        text_header = (
            "👋 **Welcome to X9 Store for Premium Numbers** 🌐!\n\n"
            "• Get premium numbers activated for all uses.\n"
            "• Instant, random, and fast purchase using Telegram Stars (⭐).\n"
            "• Ability to request the verification code (OTP) instantly and easily after purchase.\n\n"
            f"🆔 `{user_id}`\n"
            f"💵 `${balance:.2f}`\n\n"
            "Choose what suits you from the menu 👇"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Buy Numbers Store", callback_data="buy_number_menu")],
            [InlineKeyboardButton(text="⚡ My Account", callback_data="my_account"), InlineKeyboardButton(text="🎁 Daily Bonus ($0.01)", callback_data="claim_bonus")],
            [InlineKeyboardButton(text="💳 Recharge Stars", callback_data="recharge_menu")],
            [InlineKeyboardButton(text="🤝 Ref Link", callback_data="ref_menu"), InlineKeyboardButton(text="💳 Transfer", callback_data="transfer_menu")],
            [InlineKeyboardButton(text="🌐 العربية", callback_data="toggle_lang")],
            [InlineKeyboardButton(text="💬 Support", url=f"https://t.me/{ADMIN_USERNAME}")]
        ])
    else:
        text_header = (
            "👋 أهلاً بك عزيزي في متجر X9 للأرقام المميزة 🌐!\n\n"
            "• احصل على أرقام أمريكية وعالمية مميزة ومفعلة لجميع الاستخدامات.\n"
            "• الشراء فوري وسريع عبر رصيد البوت أو نجوم تليجرام (Stars ⭐).\n"
            "• إمكانية طلب كود التحقق (OTP) بشكل فوري وبكل سهولة بعد الشراء.\n\n"
            f"🆔 `{user_id}`\n"
            f"💵 `${balance:.2f}`\n\n"
            "اختر ما يناسبك من القائمة 👇"
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 متجر الأرقام", callback_data="buy_number_menu")],
            [InlineKeyboardButton(text="⚡ حسابي", callback_data="my_account"), InlineKeyboardButton(text="🎁 هدية يومية ($0.01)", callback_data="claim_bonus")],
            [InlineKeyboardButton(text="💳 شحن رصيد نجوم", callback_data="recharge_menu")],
            [InlineKeyboardButton(text="🤝 رابط إحالة", callback_data="ref_menu"), InlineKeyboardButton(text="💳 تحويل رصيد", callback_data="transfer_menu")],
            [InlineKeyboardButton(text="🌐 English", callback_data="toggle_lang")],
            [InlineKeyboardButton(text="💬 الدعم الفني", url=f"https://t.me/{ADMIN_USERNAME}")]
        ])
    return text_header, keyboard

@dp.callback_query(F.data == "toggle_lang")
async def toggle_lang_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    current_lang = get_user_language(user_id)
    new_lang = 'en' if current_lang == 'ar' else 'ar'
    
    users_collection.update_one({"user_id": user_id}, {"$set": {"language": new_lang}}, upsert=True)
    
    text, keyboard = get_main_keyboard(user_id)
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

    existing_user = users_collection.find_one({"user_id": user_id})
    if not existing_user:
        initial_balance = 10000.0 if user_id == ADMIN_USER_ID else 0.0
        users_collection.insert_one({
            "user_id": user_id,
            "balance": initial_balance,
            "referred_by": referred_by,
            "language": "ar"
        })
        if referred_by and user_id != ADMIN_USER_ID:
            users_collection.update_one({"user_id": referred_by}, {"$inc": {"balance": BONUS_AMOUNT}})

        if ADMIN_USER_ID and user_id != ADMIN_USER_ID:
            try:
                notif = f"🚨 مستخدم جديد دخل البوت!\n🆔 ID: `{user_id}`\n👤 الاسم: {user.full_name}"
                await bot.send_message(chat_id=ADMIN_USER_ID, text=notif, parse_mode="Markdown")
            except Exception:
                pass

    text, keyboard = get_main_keyboard(user_id)
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery, state: FSMContext):
    user = callback.from_user
    user_id = user.id
    if await check_subscription(user_id):
        try:
            await callback.message.delete()
        except Exception:
            pass
            
        existing_user = users_collection.find_one({"user_id": user_id})
        if not existing_user:
            initial_balance = 10000.0 if user_id == ADMIN_USER_ID else 0.0
            users_collection.insert_one({
                "user_id": user_id,
                "balance": initial_balance,
                "language": "ar"
            })

        text, keyboard = get_main_keyboard(user_id)
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await callback.answer("❌ لم تقم بالاشتراك في القناة بعد!", show_alert=True)

@dp.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    text, keyboard = get_main_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass
    await callback.answer()

@dp.callback_query(F.data == "buy_number_menu")
async def buy_number_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    
    buttons = []
    for num_id, data in NUMBERS_STORE.items():
        purchased = purchases_collection.find_one({"user_id": user_id, "number_id": num_id})
        if not purchased:
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
    
    already_purchased = purchases_collection.find_one({"user_id": user_id, "number_id": num_id})
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
        await callback.message.edit_text(f"Country: {data['name']}\nPrice: **${data['price']:.2f}**\n\n⚠️ Note: No compensation under any circumstances (including logout).\n\nDo you want to confirm the purchase?", reply_markup=keyboard, parse_mode="Markdown")
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"تأكيد الشراء مقابل ${data['price']:.2f}", callback_data=f"buy_balance_{num_id}")],
            [InlineKeyboardButton(text="🔙 رجوع", callback_data="buy_number_menu")]
        ])
        await callback.message.edit_text(f"الدولة: {data['name']}\nالسعر: **${data['price']:.2f}**\n\n⚠️ ملاحظة: لا يوجد تعويض بأي شكل (بما في ذلك تسجيل الخروج).\n\nهل تريد تأكيد الشراء؟", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_balance_"))
async def buy_with_balance(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    num_id = callback.data.replace("buy_balance_", "")
    data = NUMBERS_STORE.get(num_id)
    
    user_doc = users_collection.find_one({"user_id": user_id})
    balance = user_doc.get("balance", 0.0) if user_doc else 0.0
    
    if balance < data['price']:
        msg = "❌ Insufficient balance!" if lang == 'en' else "❌ رصيدك غير كافي!"
        await callback.answer(msg, show_alert=True)
        return
        
    users_collection.update_one({"user_id": user_id}, {"$inc": {"balance": -data['price']}})
    purchases_collection.insert_one({"user_id": user_id, "number_id": num_id})
    
    wait_msg = "⏳ Fetching code..." if lang == 'en' else "⏳ جاري جلب الكود..."
    await callback.answer(wait_msg, show_alert=False)
    otp_text = await fetch_otp_async(data["session"], data["api_id"], data["api_hash"], lang)
    
    if lang == 'en':
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Request Code (OTP)", callback_data=f"get_otp_{num_id}")],
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
        ])
        await callback.message.edit_text(
            f"🎉 **Successfully Purchased!**\n\n"
            f"📱 **Number:** `{data['phone']}`\n\n"
            f"📥 **Code Status:**\n{otp_text}", 
            reply_markup=keyboard, 
            parse_mode="Markdown"
        )
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 طلب كود (OTP)", callback_data=f"get_otp_{num_id}")],
            [InlineKeyboardButton(text="🏠 القائمة الرئيسية", callback_data="main_menu")]
        ])
        await callback.message.edit_text(
            f"🎉 **تم الشراء بنجاح!**\n\n"
            f"📱 **الرقم:** `{data['phone']}`\n\n"
            f"📥 **حالة الكود:**\n{otp_text}", 
            reply_markup=keyboard, 
            parse_mode="Markdown"
        )

@dp.callback_query(F.data.startswith("get_otp_"))
async def get_otp_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    num_id = callback.data.replace("get_otp_", "")
    data = NUMBERS_STORE.get(num_id)
    
    wait_msg = "⏳ Fetching code..." if lang == 'en' else "⏳ جاري جلب الكود..."
    await callback.answer(wait_msg, show_alert=False)
    otp_text = await fetch_otp_async(data["session"], data["api_id"], data["api_hash"], lang)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Request Code (OTP)" if lang=='en' else "🔄 طلب كود (OTP)", callback_data=f"get_otp_{num_id}")],
        [InlineKeyboardButton(text="🏠 Main Menu" if lang=='en' else "🏠 القائمة الرئيسية", callback_data="main_menu")]
    ])
    text_content = (
        f"📱 **Number:** `{data['phone']}`\n\n" if lang=='en' else f"📱 **الرقم:** `{data['phone']}`\n\n"
    ) + (f"📥 **Code Status:**\n{otp_text}" if lang=='en' else f"📥 **حالة الكود:**\n{otp_text}")

    try:
        await callback.message.edit_text(text_content, reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data == "my_account")
async def my_account(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    
    user_doc = users_collection.find_one({"user_id": user_id})
    balance = user_doc.get("balance", 0.0) if user_doc else 0.0
    
    back_text = "🔙 Back" if lang == 'en' else "🔙 رجوع"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=back_text, callback_data="main_menu")]])
    text_content = f"🆔 ID: `{user_id}`\n💵 Available Balance: `${balance:.2f}`" if lang == 'en' else f"🆔 المعرف: `{user_id}`\n💵 الرصيد المتاح: `${balance:.2f}`"
    await callback.message.edit_text(text_content, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "claim_bonus")
async def claim_bonus(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    
    user_doc = users_collection.find_one({"user_id": user_id})
    last_bonus_str = user_doc.get("last_bonus") if user_doc else None
    
    now = datetime.now()
    if last_bonus_str:
        if now - datetime.fromisoformat(last_bonus_str) < timedelta(hours=24):
            msg = "❌ You have already claimed your daily bonus!" if lang == 'en' else "❌ لقد حصلت على هديتك اليومية مسبقاً!"
            await callback.answer(msg, show_alert=True)
            return
            
    users_collection.update_one(
        {"user_id": user_id}, 
        {"$inc": {"balance": BONUS_AMOUNT}, "$set": {"last_bonus": now.isoformat()}}
    )
    
    msg_success = f"🎉 Successfully added ${BONUS_AMOUNT:.2f}!" if lang == 'en' else f"🎉 تم إضافة ${BONUS_AMOUNT:.2f} بنجاح!"
    await callback.answer(msg_success, show_alert=True)
    text, keyboard = get_main_keyboard(user_id)
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
    if lang == 'en':
        text_content = f"🤝 **Your Referral Link:**\n`{ref_link}`\n\nGet **${BONUS_AMOUNT:.2f}** for every person who registers through your link!"
    else:
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
    text_content = "💳 Send the User ID of the person you want to transfer balance to:" if lang == 'en' else "💳 أرسل آيدي (User ID) الشخص المراد تحويل الرصيد له:"
    await callback.message.edit_text(text_content, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.message(States.waiting_for_transfer_id)
async def process_transfer_id(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Please enter a valid ID / يرجى إدخال ID صحيح:")
        return
    await state.update_data(recipient_id=int(message.text.strip()))
    await state.set_state(States.waiting_for_transfer_amount)
    await message.answer("✍️ Send the amount to transfer (e.g. `0.02`):")

@dp.message(States.waiting_for_transfer_amount)
async def process_transfer_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace("$", ""))
    except ValueError:
        await message.answer("❌ Please enter a valid amount / أدخل مبلغاً صحيحاً:")
        return
        
    sender_id = message.from_user.id
    sender_doc = users_collection.find_one({"user_id": sender_id})
    sender_balance = sender_doc.get("balance", 0.0) if sender_doc else 0.0
    
    if sender_balance < amount:
        await message.answer("❌ Your current balance is not enough! / رصيدك الحالي لا يكفي!")
        await state.clear()
        return
        
    data = await state.get_data()
    recipient_id = data.get("recipient_id")
    
    recipient_doc = users_collection.find_one({"user_id": recipient_id})
    if not recipient_doc:
        await message.answer("❌ User not registered. / المستخدم غير مسجل.")
        await state.clear()
        return
        
    users_collection.update_one({"user_id": sender_id}, {"$inc": {"balance": -amount}})
    users_collection.update_one({"user_id": recipient_id}, {"$inc": {"balance": amount}})
    
    await state.clear()
    await message.answer(f"✅ Successfully transferred `${amount:.2f}` to user `{recipient_id}`!", parse_mode="Markdown")

@dp.callback_query(F.data == "recharge_menu")
async def recharge_menu(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    await state.set_state(States.waiting_for_stars_count)
    back_text = "🔙 Back" if lang == 'en' else "🔙 رجوع"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=back_text, callback_data="main_menu")]])
    if lang == 'en':
        text_content = "Send the number of stars you want to recharge (Each star = $0.02):\nExample: `50` means $1"
    else:
        text_content = "أرسل عدد النجوم التي تريد شحنها (كل نجمة = 0.02 دولار):\nمثال: `50` تعني 1 دولار"
    await callback.message.edit_text(text_content, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.message(States.waiting_for_stars_count)
async def process_stars(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Enter valid numbers only / أدخل أرقام صحيحة فقط:")
        return
    stars_count = int(message.text.strip())
    added = stars_count * STAR_PRICE_USD
    await state.clear()
    await bot.send_invoice(
        chat_id=message.chat.id,
        title=f"Recharge {stars_count} Stars" if get_user_language(message.from_user.id) == 'en' else f"شحن {stars_count} نجمة",
        description=f"Get ${added:.2f} balance (Each star = $0.02)",
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
    lang = get_user_language(message.from_user.id)
    payload = message.successful_payment.invoice_payload
    if payload.startswith("recharge_"):
        stars = int(payload.replace("recharge_", ""))
        added = stars * STAR_PRICE_USD
        
        users_collection.update_one({"user_id": message.from_user.id}, {"$inc": {"balance": added}})
        
        msg = f"🎉 Successfully recharged `${added:.2f}` to your balance!" if lang == 'en' else f"🎉 تم شحن `${added:.2f}` بنجاح إلى رصيدك!"
        await message.answer(msg)

async def fetch_otp_async(session_str, api_id, api_hash, lang='ar'):
    if not session_str or "ضع_جلسة" in session_str:
        return "❌ Session is not configured yet!" if lang == 'en' else "❌ الجلسة غير مُعدة بعد!"
    try:
        client = TelegramClient(StringSession(session_str), api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return "❌ Session has expired." if lang == 'en' else "❌ الجلسة منتهية الصلاحية."
        messages = await client.get_messages(777000, limit=5)
        await client.disconnect()
        if not messages:
            return "⏳ Code has not arrived yet, click the request code button again." if lang == 'en' else "⏳ لم يصل الكود بعد، اضغط على زر طلب كود مجدداً."
        for msg in messages:
            if msg.text:
                otp_match = re.search(r'\b\d{5,6}\b', msg.text)
                if otp_match:
                    return f"🔑 **Verification Code:** `{otp_match.group(0)}`" if lang == 'en' else f"🔑 **كود التحقق:** `{otp_match.group(0)}`"
        return "⏳ No new activation code has arrived yet, click 'Request Code' to update status." if lang == 'en' else "⏳ لم يصل كود تفعيل جديد بعد، اضغط على زر 'طلب كود' لتحديث الحالة."
    except Exception as e:
        return f"❌ Connection Error: {str(e)}"

async def main():
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
