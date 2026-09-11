import os
import re
import asyncio
import sqlite3
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, 
    LabeledPrice, PreCheckoutQuery
)
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.states import State, StatesGroup
from aiogram.fsm.context import FSMContext
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

# =====================================================================
# 🛠️ [الإعدادات الأساسية وقاعدة بيانات SQLite المحلية]
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

MAIN_SECTIONS = [
    "شراء حساب جاهز",
    "إنشاء قديم",
    "احتيالي",
    "أرقام تليجرام عادية"
]

DB_FILE = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0,
            language TEXT DEFAULT 'ar',
            banned INTEGER DEFAULT 0,
            last_claim TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS numbers (
            num_id TEXT PRIMARY KEY,
            section TEXT,
            country TEXT,
            price REAL,
            phone TEXT,
            session TEXT,
            api_id INTEGER,
            api_hash TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            number_id TEXT,
            num_data TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    conn.commit()
    conn.close()

init_db()

def get_config_val(key, default):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return default
    return row[0]

def set_config_val(key, value):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

async def get_config():
    star_price = float(get_config_val("star_price", 0.01))
    ton_price = float(get_config_val("ton_price", 1.35))
    methods_str = get_config_val("payment_methods", "Telegram Stars ⭐, TON 💎")
    methods = [m.strip() for m in methods_str.split(",")]
    return {
        "star_price": star_price,
        "ton_price": ton_price,
        "payment_methods": methods
    }

async def update_config(data: dict):
    for k, v in data.items():
        if isinstance(v, list):
            set_config_val(k, ", ".join(v))
        else:
            set_config_val(k, v)

async def get_user(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, balance, language, banned, last_claim FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row:
        initial_balance = 10000.02 if user_id == DEFAULT_ADMIN_USER_ID else 0.0
        cursor.execute(
            "INSERT INTO users (user_id, balance, language, banned, last_claim) VALUES (?, ?, 'ar', 0, NULL)",
            (user_id, initial_balance)
        )
        conn.commit()
        user = {
            "user_id": user_id,
            "balance": initial_balance,
            "language": "ar",
            "banned": False,
            "last_claim": None
        }
    else:
        user = {
            "user_id": row[0],
            "balance": row[1],
            "language": row[2],
            "banned": bool(row[3]),
            "last_claim": datetime.fromisoformat(row[4]) if row[4] else None
        }
    conn.close()
    return user

async def update_user(user_id: int, data: dict):
    user = await get_user(user_id)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    balance = data.get("balance", user["balance"])
    language = data.get("language", user["language"])
    banned = 1 if data.get("banned", user["banned"]) else 0
    last_claim = data.get("last_claim", user["last_claim"])
    last_claim_str = last_claim.isoformat() if isinstance(last_claim, datetime) else last_claim
    
    cursor.execute("""
        UPDATE users SET balance = ?, language = ?, banned = ?, last_claim = ? WHERE user_id = ?
    """, (balance, language, banned, last_claim_str, user_id))
    conn.commit()
    conn.close()

# =====================================================================
# 🚀 [تهيئة البوت والحالات]
# =====================================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

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
    user = await get_user(user_id)
    balance = user.get("balance", 0.0)
    lang = user.get("language", "ar")
    
    keyboard_buttons = [
        [InlineKeyboardButton(text="🛒 Buy Numbers Store" if lang == 'en' else "🛒 متجر الأرقام", callback_data="buy_number_menu")],
        [InlineKeyboardButton(text="⚡ My Account" if lang == 'en' else "⚡ حسابي", callback_data="my_account"), InlineKeyboardButton(text="🎁 Daily Bonus" if lang == 'en' else "🎁 هدية يومية ($0.01)", callback_data="claim_bonus")],
        [InlineKeyboardButton(text="💳 Recharge Balance & Pay" if lang == 'en' else "💳 شحن الرصيد وطرق الدفع", callback_data="recharge_menu")],
        [InlineKeyboardButton(text="💳 Transfer" if lang == 'en' else "💳 تحويل رصيد", callback_data="transfer_menu")],
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
    user = await get_user(user_id)
    current_lang = user.get("language", "ar")
    new_lang = 'en' if current_lang == 'ar' else 'ar'
    await update_user(user_id, {"language": new_lang})
    text, keyboard = await get_main_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass
    await callback.answer()

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    user_doc = await get_user(user_id)
    if user_doc.get("banned", False):
        await message.answer("❌ عذراً، لقد تم حظرك من استخدام هذا البوت.")
        return

    if not await check_subscription(user_id):
        sub_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 اشترك في القناة", url=f"https://t.me/{REQUIRED_CHANNEL}")],
            [InlineKeyboardButton(text="🔄 تحقق من الاشتراك", callback_data="check_sub")]
        ])
        await message.answer(f"⚠️ يجب عليك الاشتراك في القناة أولاً: @{REQUIRED_CHANNEL}", reply_markup=sub_keyboard)
        return

    text, keyboard = await get_main_keyboard(user_id)
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_doc = await get_user(user_id)
    if user_doc.get("banned", False):
        await callback.answer("❌ أنت محظور من استخدام البوت.", show_alert=True)
        return

    if await check_subscription(user_id):
        try:
            await callback.message.delete()
        except Exception:
            pass
        text, keyboard = await get_main_keyboard(user_id)
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await callback.answer("❌ لم تقم بالاشتراك في القناة بعد!", show_alert=True)

@dp.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    user_doc = await get_user(user_id)
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
        
    config = await get_config()
    current_star_price = config.get("star_price", 0.01)

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
    config = await get_config()
    methods = ", ".join(config.get("payment_methods", []))
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
    await update_config({"payment_methods": methods})
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
    user = await get_user(user_id)
    balance = user.get("balance", 0.0)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM purchases WHERE user_id = ?", (user_id,))
    purchased_count = cursor.fetchone()[0]
    conn.close()
    
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
    user = await get_user(user_id)
    
    now = datetime.utcnow()
    last_claim = user.get("last_claim")
    if last_claim and (now - last_claim) < timedelta(hours=24):
        remaining = timedelta(hours=24) - (now - last_claim)
        hours, remainder = divmod(int(remaining.total_seconds()), 3600)
        minutes = remainder // 60
        await callback.answer(f"⏳ لقد حصلت على الهدية مسبقاً. انتظر {hours} ساعة و {minutes} دقيقة.", show_alert=True)
        return

    new_balance = user.get("balance", 0.0) + BONUS_AMOUNT
    await update_user(user_id, {"balance": new_balance, "last_claim": now})
    await callback.answer("🎁 مبروك! حصلت على هدية بقيمة $0.01 بنجاح.", show_alert=True)
    text, keyboard = await get_main_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass

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
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (target_id,))
    target_row = cursor.fetchone()
    conn.close()

    if not target_row:
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
    sender_doc = await get_user(sender_id)
    sender_balance = sender_doc.get("balance", 0.0)
    if sender_balance < amount:
        await message.answer("❌ رصيدك غير كافي لإتمام عملية التحويل هذه.")
        await state.clear()
        return
        
    data = await state.get_data()
    target_id = data["transfer_id"]
    target_doc = await get_user(target_id)
    
    await update_user(sender_id, {"balance": sender_balance - amount})
    await update_user(target_id, {"balance": target_doc.get("balance", 0.0) + amount})
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
    config = await get_config()
    star_price = config.get("star_price", 0.01)
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
    config = await get_config()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="recharge_menu")]
    ])
    text = (
        "💎 **شحن الرصيد عبر عملة TON:**\n\n"
        "قم بالتحويل إلى عنوان المحفظة أدناه، ثم تواصل مع الدعم الفني أو أرسل إيصال التحويل ليتم شحن رصيدك فوراً:\n\n"
        f"📌 **عنوان المحفظة:**\n`{TON_WALLET_ADDRESS}`\n\n"
        f"💡 **سعر التون الواحد التقريبي:** `${config.get('ton_price', 1.35)}`\n\n"
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
            config = await get_config()
            star_price = config.get("star_price", 0.01)
            added_usd = count * star_price
            user_id = message.from_user.id
            user = await get_user(user_id)
            await update_user(user_id, {"balance": user.get("balance", 0.0) + added_usd})
            await message.answer(f"✅ تم الدفع بنجاح! وإضافة `${added_usd:.2f}` إلى رصيدك.")
        except Exception:
            pass

@dp.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: CallbackQuery):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE banned = 1")
    banned_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM numbers")
    total_nums = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM purchases")
    total_purchases = cursor.fetchone()[0]
    conn.close()
    
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
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()

    sent_count = 0
    for row in users:
        try:
            await bot.send_message(row[0], broadcast_text, parse_mode="Markdown")
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
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET banned = 1 WHERE user_id = ?", (uid,))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()

    if rows_affected > 0:
        await message.answer(f"✅ تم حظر المستخدم (`{uid}`) بنجاح.")
    else:
        await message.answer("❌ المستخدم غير موجود في القاعدة.")

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
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET banned = 0 WHERE user_id = ?", (uid,))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()

    if rows_affected > 0:
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
    await update_config({"star_price": new_price})
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
    user = await get_user(uid)
    await update_user(uid, {"balance": user.get("balance", 0.0) + amount})
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
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (uid,))
    row = cursor.fetchone()
    conn.close()

    if row:
        new_bal = max(0.0, row[0] - amount)
        await update_user(uid, {"balance": new_bal})
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
    await update_user(uid, {"balance": amount})
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
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, balance, language, banned FROM users WHERE user_id = ?", (uid,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        await message.answer("❌ هذا المستخدم غير مسجل في البوت.")
        return
    
    text = (
        f"👤 **معلومات المستخدم:**\n\n"
        f"🆔 الآي دي: `{row[0]}`\n"
        f"💵 الرصيد: `${row[1]:.2f}`\n"
        f"🌐 اللغة: `{row[2]}`\n"
        f"🚫 محظور: `{'نعم' if row[3] else 'لا'}`"
    )
    await message.answer(text, parse_mode="Markdown")

# =====================================================================
# 📱 [خطوات إضافة الرقم وتحديد القسم والتفاصيل]
# =====================================================================

@dp.callback_query(F.data == "admin_auto_add_num")
async def admin_auto_add_num(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    
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
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO numbers (num_id, section, country, price, phone, session, api_id, api_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (num_id, data["num_section"], data["country"], data["num_price"], data["phone"], final_session, data["api_id"], data["api_hash"]))
        conn.commit()
        conn.close()

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
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO numbers (num_id, section, country, price, phone, session, api_id, api_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (num_id, data["num_section"], data["country"], data["num_price"], data["phone"], final_session, data["api_id"], data["api_hash"]))
        conn.commit()
        conn.close()

        await state.clear()
        await message.answer("✅ تم تفعيل الرقم وحفظه بنجاح!")
    except Exception as e:
        await state.clear()
        await message.answer(f"❌ خطأ: `{str(e)}`")

@dp.callback_query(F.data == "admin_manage_nums")
async def admin_manage_nums_handler(callback: CallbackQuery):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT num_id, section, country FROM numbers")
    numbers_list = cursor.fetchall()
    conn.close()
    
    if not numbers_list:
        back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
        await callback.message.edit_text("📭 لا توجد أرقام مضافة حالياً.", reply_markup=back_kb)
        await callback.answer()
        return

    buttons = []
    for num in numbers_list:
        num_id, sec, cntry = num[0], num[1], num[2]
        buttons.append([
            InlineKeyboardButton(text=f"🗑 [{sec}] {cntry}", callback_data=f"del_num_{num_id}"),
            InlineKeyboardButton(text="✏️ تعديل", callback_data=f"edit_num_{num_id}")
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
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE numbers SET country = ?, price = ? WHERE num_id = ?", (new_country, new_price, num_id))
    conn.commit()
    conn.close()
            
    await state.clear()
    await message.answer("✅ تم تعديل بيانات الرقم بنجاح!")

@dp.callback_query(F.data.startswith("del_num_"))
async def delete_number_handler(callback: CallbackQuery):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    num_id = callback.data.replace("del_num_", "")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM numbers WHERE num_id = ?", (num_id,))
    conn.commit()
    
    cursor.execute("SELECT num_id, section, country FROM numbers")
    numbers_list = cursor.fetchall()
    conn.close()
    
    await callback.answer("✅ تم حذف الرقم بنجاح!", show_alert=True)
    
    buttons = []
    if numbers_list:
        for num in numbers_list:
            buttons.append([
                InlineKeyboardButton(text=f"🗑 [{num[1]}] {num[2]}", callback_data=f"del_num_{num[0]}"),
                InlineKeyboardButton(text="✏️ تعديل", callback_data=f"edit_num_{num[0]}")
            ])
    buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")])
    await callback.message.edit_text("⚙️ **إدارة الأرقام:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# =====================================================================
# 🛒 [قسم متجر الأرقام والشراء الفوري وجلب الـ OTP]
# =====================================================================

@dp.callback_query(F.data == "buy_number_menu")
async def buy_number_menu_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_doc = await get_user(user_id)
    if user_doc.get("banned", False):
        await callback.answer("❌ أنت محظور.", show_alert=True)
        return

    keyboard_buttons = []
    for sec in MAIN_SECTIONS:
        keyboard_buttons.append([InlineKeyboardButton(text=f"📁 {sec}", callback_data=f"shop_sec_{sec}")])
    keyboard_buttons.append([InlineKeyboardButton(text="🛍 أرقامي المشتراة", callback_data="my_purchased_numbers")])
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 القائمة الرئيسية", callback_data="main_menu")])

    text = "🛒 **اختر القسم الذي تريد شراء الأرقام منه:**"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("shop_sec_"))
async def shop_section_handler(callback: CallbackQuery):
    section_name = callback.data.replace("shop_sec_", "")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT num_id, country, price FROM numbers WHERE section = ?", (section_name,))
    nums = cursor.fetchall()
    conn.close()

    keyboard_buttons = []
    if nums:
        for num in nums:
            num_id, country, price = num[0], num[1], num[2]
            keyboard_buttons.append([InlineKeyboardButton(text=f"{country} — ${price:.2f}", callback_data=f"buy_item_{num_id}")])
    else:
        keyboard_buttons.append([InlineKeyboardButton(text="❌ لا توجد أرقام متاحة حالياً في هذا القسم", callback_data="buy_number_menu")])

    keyboard_buttons.append([InlineKeyboardButton(text="🔙 رجوع للأقسام", callback_data="buy_number_menu")])
    
    await callback.message.edit_text(f"📁 **القسم:** `{section_name}`\n\nاختر الرقم المناسب للشراء:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_item_"))
async def buy_item_confirmation(callback: CallbackQuery):
    num_id = callback.data.replace("buy_item_", "")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT num_id, section, country, price, phone FROM numbers WHERE num_id = ?", (num_id,))
    item = cursor.fetchone()
    conn.close()

    if not item:
        await callback.answer("❌ عذراً، هذا الرقم تم بيعه أو لم يعد متوفراً!", show_alert=True)
        return

    country, price = item[2], item[3]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تأكيد الشراء", callback_data=f"confirm_buy_{num_id}")],
        [InlineKeyboardButton(text="❌ إلغاء", callback_data="buy_number_menu")]
    ])
    
    text = (
        f"🛒 **تأكيد عملية الشراء:**\n\n"
        f"• الدولة والتفاصيل: `{country}`\n"
        f"• السعر المطلوب: `${price:.2f}`\n\n"
        f"هل أنت متأكد من رغبتك في إتمام عملية الشراء؟"
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("confirm_buy_"))
async def execute_purchase(callback: CallbackQuery):
    user_id = callback.from_user.id
    num_id = callback.data.replace("confirm_buy_", "")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT num_id, section, country, price, phone, session, api_id, api_hash FROM numbers WHERE num_id = ?", (num_id,))
    item = cursor.fetchone()
    conn.close()

    if not item:
        await callback.answer("❌ عذراً، الرقم غير متوفر.", show_alert=True)
        return

    price = item[3]
    user = await get_user(user_id)
    balance = user.get("balance", 0.0)

    if balance < price:
        await callback.answer("❌ رصيدك غير كافي لإتمام عملية الشراء. قم بشحن رصيدك أولاً!", show_alert=True)
        return

    new_balance = balance - price
    await update_user(user_id, {"balance": new_balance})

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM numbers WHERE num_id = ?", (num_id,))
    num_data_json = json.dumps({
        "num_id": item[0],
        "section": item[1],
        "country": item[2],
        "price": item[3],
        "phone": item[4],
        "session": item[5],
        "api_id": item[6],
        "api_hash": item[7]
    })
    cursor.execute("INSERT INTO purchases (user_id, number_id, num_data) VALUES (?, ?, ?)", (user_id, num_id, num_data_json))
    conn.commit()
    conn.close()

    success_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 أرقامي المشتراة", callback_data="my_purchased_numbers")],
        [InlineKeyboardButton(text="🏠 الرئيسية", callback_data="main_menu")]
    ])
    
    text = (
        f"🎉 **تمت عملية الشراء بنجاح!**\n\n"
        f"📱 الرقم: `{item[4]}`\n"
        f"🌍 الدولة: `{item[2]}`\n"
        f"💵 السعر المدفوع: `${price:.2f}`\n\n"
        f"يمكنك الانتقال إلى قسم (أرقامي المشتراة) لعرض الجلسة أو طلب كود التحقق (OTP) في أي وقت."
    )
    await callback.message.edit_text(text, reply_markup=success_kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "my_purchased_numbers")
async def my_purchased_numbers_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, num_data FROM purchases WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="buy_number_menu")]])
        await callback.message.edit_text("📭 لم تقم بشراء أي أرقام بعد.", reply_markup=back_kb)
        await callback.answer()
        return

    buttons = []
    for row in rows:
        p_id = row[0]
        data = json.loads(row[1])
        buttons.append([InlineKeyboardButton(text=f"📱 {data['country']} ({data['phone']})", callback_data=f"manage_purchased_{p_id}")])
    
    buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="buy_number_menu")])
    await callback.message.edit_text("📦 **سجل أرقامك المشتراة:**\n\nاختر الرقم لعرض تفاصيله أو طلب كود التحقق:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("manage_purchased_"))
async def manage_purchased_item(callback: CallbackQuery):
    user_id = callback.from_user.id
    p_id = int(callback.data.replace("manage_purchased_", ""))

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT num_data FROM purchases WHERE id = ? AND user_id = ?", (p_id, user_id))
    row = cursor.fetchone()
    conn.close()

    if not row:
        await callback.answer("❌ الرقم غير موجود أو لا تملكه.", show_alert=True)
        return

    data = json.loads(row[0])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 طلب كود التحقق (OTP)", callback_data=f"get_otp_{p_id}")],
        [InlineKeyboardButton(text="📋 نسخ كود الجلسة (StringSession)", callback_data=f"get_sess_{p_id}")],
        [InlineKeyboardButton(text="🔙 أرقامي المشتراة", callback_data="my_purchased_numbers")]
    ])

    text = (
        f"📱 **تفاصيل الرقم المشتراة:**\n\n"
        f"• الدولة: `{data['country']}`\n"
        f"• الهاتف: `{data['phone']}`\n"
        f"• API ID: `{data['api_id']}`\n"
        f"• API Hash: `{data['api_hash']}`"
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("get_sess_"))
async def get_session_string(callback: CallbackQuery):
    user_id = callback.from_user.id
    p_id = int(callback.data.replace("get_sess_", ""))

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT num_data FROM purchases WHERE id = ? AND user_id = ?", (p_id, user_id))
    row = cursor.fetchone()
    conn.close()

    if not row:
        await callback.answer("❌ خطأ.", show_alert=True)
        return

    data = json.loads(row[0])
    session_str = data['session']
    await callback.message.answer(f"📋 **كود الجلسة (StringSession) الخاص بك:**\n\n`{session_str}`", parse_mode="Markdown")
    await callback.answer("تم إرسال كود الجلسة في رسالة منفصلة!")

@dp.callback_query(F.data.startswith("get_otp_"))
async def get_otp_code(callback: CallbackQuery):
    user_id = callback.from_user.id
    p_id = int(callback.data.replace("get_otp_", ""))

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT num_data FROM purchases WHERE id = ? AND user_id = ?", (p_id, user_id))
    row = cursor.fetchone()
    conn.close()

    if not row:
        await callback.answer("❌ خطأ.", show_alert=True)
        return

    data = json.loads(row[0])
    await callback.answer("⏳ جاري فحص الرسائل الأخيرة لتليجرام واستخراج كود التحقق...", show_alert=True)

    try:
        client = TelegramClient(StringSession(data['session']), data['api_id'], data['api_hash'])
        await client.connect()
        
        messages = await client.get_messages(777000, limit=3)
        await client.disconnect()

        otp_found = None
        for msg in messages:
            match = re.search(r'\b(\d{5})\b', msg.message)
            if match:
                otp_found = match.group(1)
                break
            match_alt = re.search(r'code[:\s]+(\d+)', msg.message, re.IGNORECASE)
            if match_alt:
                otp_found = match_alt.group(1)
                break

        if otp_found:
            await callback.message.answer(f"✅ **كود التحقق (OTP) الأخير للرقم `{data['phone']}` هو:**\n\n`{otp_found}`", parse_mode="Markdown")
        else:
            client2 = TelegramClient(StringSession(data['session']), data['api_id'], data['api_hash'])
            await client2.connect()
            dialogs = await client2.get_dialogs(limit=5)
            latest_msg_text = ""
            for d in dialogs:
                msgs = await client2.get_messages(d.entity, limit=1)
                if msgs:
                    latest_msg_text += f"\n- من ({d.name}): {msgs[0].message[:100]}"
            await client2.disconnect()
            
            await callback.message.answer(
                f"⚠️ لم يتم العثور على رسالة كود صريحة من تليجرام.\n"
                f"آخر النشاطات في الحساب:{latest_msg_text}"
            )
    except Exception as e:
        await callback.message.answer(f"❌ حدث خطأ أثناء الاتصال بالجلسة وجلب الكود:\n`{str(e)}`")

# =====================================================================
# 🏁 [تشغيل البوت الأساسي]
# =====================================================================

async def main():
    print("🚀 Bot is starting and running successfully with SQLite DB...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
