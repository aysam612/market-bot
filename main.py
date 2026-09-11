import asyncio
import re
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
# 🛠️ [الإعدادات الأساسية وقاعدة البيانات الديناميكية]
# =====================================================================

BOT_TOKEN = "ضع_توكن_البوت_هنا"
DEFAULT_ADMIN_USER_ID = 8863784148  # آي دي المشرف الخاص بك

DB_FILE = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # جدول المستخدمين
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0,
            language TEXT DEFAULT 'ar',
            banned INTEGER DEFAULT 0,
            last_claim TEXT
        )
    """)
    
    # جدول الأرقام
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
    
    # جدول المشتريات
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            number_id TEXT,
            num_data TEXT
        )
    """)
    
    # جدول الإعدادات العامة (قابلة للتعديل بالكامل من لوحة التحكم)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # جدول الأزرار المخصصة الإضافية في القائمة الرئيسية
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_buttons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            url TEXT
        )
    """)

    # جدول أقسام المتجر الديناميكية
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shop_sections (
            name TEXT PRIMARY KEY
        )
    """)
    
    conn.commit()
    
    # القيم الافتراضية
    defaults = {
        "welcome_message": "👋 أهلاً بك عزيزي في متجر الأرقام المميزة 🌐!\n\n• احصل على أرقام عالمية مميزة ومفعلة لجميع الاستخدامات.\n• الشراء فوري وسريع عبر رصيد البوت أو نجوم تليجرام (Stars ⭐).\n• إمكانية طلب كود التحقق (OTP) بشكل فوري وبكل سهولة بعد الشراء.\n\nاختر ما يناسبك من القائمة 👇",
        "support_username": "aaysam",
        "required_channel": "",
        "ton_wallet": "UQAGJ8uRcdJAq-FxA7Zh_TanaT_0kn2ptxnoPSfzECS9Q2ZU",
        "star_price": "0.01",
        "ton_price": "1.35",
        "bonus_amount": "0.01"
    }
    
    for k, v in defaults.items():
        cursor.execute("INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)", (k, v))

    default_sections = ["شراء حساب جاهز", "إنشاء قديم", "احتيالي", "أرقام تليجرام عادية"]
    for sec in default_sections:
        cursor.execute("INSERT OR IGNORE INTO shop_sections (name) VALUES (?)", (sec,))
        
    conn.commit()
    conn.close()

init_db()

def get_config_val(key, default=""):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

def set_config_val(key, value):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

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
        user = {"user_id": user_id, "balance": initial_balance, "language": "ar", "banned": False, "last_claim": None}
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
    
    cursor.execute("UPDATE users SET balance = ?, language = ?, banned = ?, last_claim = ? WHERE user_id = ?", (balance, language, banned, last_claim_str, user_id))
    conn.commit()
    conn.close()

async def check_subscription(user_id: int) -> bool:
    req_chan = get_config_val("required_channel", "")
    if not req_chan:
        return True
    try:
        member = await bot.get_chat_member(chat_id=f"@{req_chan}", user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except Exception:
        pass
    return False

# =====================================================================
# 🚀 [تهيئة البوت والحالات FSM]
# =====================================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class States(StatesGroup):
    waiting_for_stars_count = State()
    waiting_for_transfer_id = State()
    waiting_for_transfer_amount = State()
    
    waiting_for_country = State()
    waiting_for_auto_num_id = State()
    waiting_for_auto_num_price = State()
    waiting_for_auto_api_combo = State()
    waiting_for_auto_phone = State()
    waiting_for_auto_code = State()
    waiting_for_auto_password = State()

    waiting_for_btn_name = State()
    waiting_for_btn_url = State()

    waiting_for_new_section = State()
    waiting_for_edit_welcome = State()
    waiting_for_edit_support = State()
    waiting_for_edit_channel = State()
    waiting_for_edit_wallet = State()
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

async def get_main_keyboard(user_id):
    user = await get_user(user_id)
    balance = user.get("balance", 0.0)
    lang = user.get("language", "ar")
    
    keyboard_buttons = [
        [InlineKeyboardButton(text="🛒 Buy Numbers Store" if lang == 'en' else "🛒 متجر الأرقام", callback_data="buy_number_menu")],
        [InlineKeyboardButton(text="⚡ My Account" if lang == 'en' else "⚡ حسابي", callback_data="my_account"), InlineKeyboardButton(text="🎁 Daily Bonus" if lang == 'en' else "🎁 هدية يومية", callback_data="claim_bonus")],
        [InlineKeyboardButton(text="💳 Recharge Balance & Pay" if lang == 'en' else "💳 شحن الرصيد وطرق الدفع", callback_data="recharge_menu")],
        [InlineKeyboardButton(text="💳 Transfer" if lang == 'en' else "💳 تحويل رصيد", callback_data="transfer_menu")],
    ]
    
    # جلب الأزرار الخارجية المضافة ديناميكياً من لوحة التحكم
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, url FROM custom_buttons")
    custom_btns = cursor.fetchall()
    conn.close()
    
    for name, url in custom_btns:
        keyboard_buttons.append([InlineKeyboardButton(text=name, url=url)])
        
    keyboard_buttons.append([InlineKeyboardButton(text="🌐 English" if lang == 'ar' else "🌐 العربية", callback_data="toggle_lang")])
    
    if user_id == DEFAULT_ADMIN_USER_ID:
        keyboard_buttons.append([InlineKeyboardButton(text="🛠 لوحة التحكم الشاملة (Admin Panel)", callback_data="admin_panel_main")])
        
    support_user = get_config_val("support_username", "aaysam")
    keyboard_buttons.append([InlineKeyboardButton(text="💬 Support" if lang == 'en' else "💬 الدعم الفني", url=f"https://t.me/{support_user.replace('@', '')}")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    welcome_template = get_config_val("welcome_message", "أهلاً بك في المتجر")
    text_header = (
        f"{welcome_template}\n\n"
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

    req_chan = get_config_val("required_channel", "")
    if req_chan and not await check_subscription(user_id):
        sub_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 اشترك في القناة", url=f"https://t.me/{req_chan}")],
            [InlineKeyboardButton(text="🔄 تحقق من الاشتراك", callback_data="check_sub")]
        ])
        await message.answer(f"⚠️ يجب عليك الاشتراك في القناة أولاً: @{req_chan}", reply_markup=sub_keyboard)
        return

    text, keyboard = await get_main_keyboard(user_id)
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
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
    text, keyboard = await get_main_keyboard(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    except Exception:
        pass
    await callback.answer()

# =====================================================================
# 👑 [لوحة التحكم الديناميكية بالكامل]
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
            await event.answer("عذراً، هذه اللوحة للمالك فقط! ❌", show_alert=True)
        else:
            await message.answer("عذراً، هذه اللوحة للمالك فقط! ❌")
        return
        
    star_price = get_config_val("star_price", "0.01")

    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ إضافة رقم جديد", callback_data="admin_auto_add_num")],
        [InlineKeyboardButton(text="✏️ إدارة الأرقام", callback_data="admin_manage_nums"), InlineKeyboardButton(text="📁 إدارة الأقسام", callback_data="admin_manage_sections")],
        [InlineKeyboardButton(text="🔘 إدارة الأزرار الخارجية", callback_data="admin_manage_buttons")],
        [InlineKeyboardButton(text="⚙️ تعديل النصوص والروابط العامة", callback_data="admin_edit_texts_menu")],
        [InlineKeyboardButton(text="👥 إحصائيات البوت", callback_data="admin_stats"), InlineKeyboardButton(text="📢 إذاعة رسالة", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="➕ إضافة رصيد", callback_data="admin_add_balance"), InlineKeyboardButton(text="➖ خصم رصيد", callback_data="admin_deduct_balance")],
        [InlineKeyboardButton(text="🎯 تعيين رصيد", callback_data="admin_set_balance"), InlineKeyboardButton(text="🔍 بحث مستخدم", callback_data="admin_check_user")],
        [InlineKeyboardButton(text=f"⭐ تعديل سعر النجمة ({star_price})", callback_data="admin_change_star_price")],
        [InlineKeyboardButton(text="🚫 حظر مستخدم", callback_data="admin_ban_user"), InlineKeyboardButton(text="✅ رفع حظر", callback_data="admin_unban_user")],
        [InlineKeyboardButton(text="🏠 الرئيسية", callback_data="main_menu")]
    ])
    
    text = "🛠 **لوحة التحكم الشاملة والديناميكية:**\nتحكم بكل تفاصيل البوت من هنا مباشرة دون الحاجة لأي تعديل برمجي:"
    
    if isinstance(event, CallbackQuery):
        await message.edit_text(text, reply_markup=builder, parse_mode="Markdown")
        await event.answer()
    else:
        await message.answer(text, reply_markup=builder, parse_mode="Markdown")

# إدارة الأقسام
@dp.callback_query(F.data == "admin_manage_sections")
async def admin_manage_sections(callback: CallbackQuery):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM shop_sections")
    sections = cursor.fetchall()
    conn.close()

    buttons = [[InlineKeyboardButton(text="➕ إضافة قسم جديد", callback_data="admin_add_section")]]
    for sec in sections:
        buttons.append([InlineKeyboardButton(text=f"🗑 حذف قسم: {sec[0]}", callback_data=f"del_sec_{sec[0]}")])
    buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")])
    
    await callback.message.edit_text("📁 **إدارة أقسام المتجر:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data == "admin_add_section")
async def admin_add_section_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    await state.set_state(States.waiting_for_new_section)
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_manage_sections")]])
    await callback.message.edit_text("📁 أرسل اسم القسم الجديد:", reply_markup=back_kb)
    await callback.answer()

@dp.message(States.waiting_for_new_section)
async def process_new_section(message: Message, state: FSMContext):
    sec_name = message.text.strip()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO shop_sections (name) VALUES (?)", (sec_name,))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer(f"✅ تمت إضافة القسم (`{sec_name}`) بنجاح!")

@dp.callback_query(F.data.startswith("del_sec_"))
async def delete_shop_section(callback: CallbackQuery):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    sec_name = callback.data.replace("del_sec_", "")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shop_sections WHERE name = ?", (sec_name,))
    conn.commit()
    conn.close()
    await callback.answer(f"✅ تم حذف القسم ({sec_name}) بنجاح!", show_alert=True)
    await admin_manage_sections(callback)

# تعديل النصوص والروابط العامة
@dp.callback_query(F.data == "admin_edit_texts_menu")
async def admin_edit_texts_menu(callback: CallbackQuery):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ تعديل رسالة الترحيب", callback_data="edit_txt_welcome")],
        [InlineKeyboardButton(text="💬 تعديل يوزر الدعم الفني", callback_data="edit_txt_support")],
        [InlineKeyboardButton(text="📢 تعديل قناة الإجبار", callback_data="edit_txt_channel")],
        [InlineKeyboardButton(text="💎 تعديل محفظة TON", callback_data="edit_txt_wallet")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]
    ])
    await callback.message.edit_text("⚙️ **تعديل النصوص والإعدادات العامة:**", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("edit_txt_"))
async def edit_specific_text(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    action = callback.data.replace("edit_txt_", "")
    
    if action == "welcome":
        await state.set_state(States.waiting_for_edit_welcome)
        await callback.message.edit_text("✍️ أرسل نص رسالة الترحيب الجديدة:")
    elif action == "support":
        await state.set_state(States.waiting_for_edit_support)
        await callback.message.edit_text("✍️ أرسل يوزر الدعم الجديد (بدون @):")
    elif action == "channel":
        await state.set_state(States.waiting_for_edit_channel)
        await callback.message.edit_text("✍️ أرسل معرف القناة الإجبارية (أو اتركه فارغاً للإلغاء):")
    elif action == "wallet":
        await state.set_state(States.waiting_for_edit_wallet)
        await callback.message.edit_text("✍️ أرسل عنوان محفظة TON الجديد:")
    await callback.answer()

@dp.message(States.waiting_for_edit_welcome)
async def save_welcome(message: Message, state: FSMContext):
    set_config_val("welcome_message", message.text)
    await state.clear()
    await message.answer("✅ تم تحديث رسالة الترحيب بنجاح!")

@dp.message(States.waiting_for_edit_support)
async def save_support(message: Message, state: FSMContext):
    set_config_val("support_username", message.text.strip().replace("@", ""))
    await state.clear()
    await message.answer("✅ تم تحديث يوزر الدعم بنجاح!")

@dp.message(States.waiting_for_edit_channel)
async def save_channel(message: Message, state: FSMContext):
    val = message.text.strip().replace("@", "")
    if val.lower() == "none" or not val:
        val = ""
    set_config_val("required_channel", val)
    await state.clear()
    await message.answer("✅ تم تحديث قناة الاشتراك الإجباري بنجاح!")

@dp.message(States.waiting_for_edit_wallet)
async def save_wallet(message: Message, state: FSMContext):
    set_config_val("ton_wallet", message.text.strip())
    await state.clear()
    await message.answer("✅ تم تحديث محفظة TON بنجاح!")

# إدارة الأزرار الخارجية
@dp.callback_query(F.data == "admin_manage_buttons")
async def admin_manage_buttons(callback: CallbackQuery):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, url FROM custom_buttons")
    buttons_db = cursor.fetchall()
    conn.close()

    buttons = [[InlineKeyboardButton(text="➕ إضافة زر جديد", callback_data="admin_add_btn")]]
    for b_id, name, url in buttons_db:
        buttons.append([InlineKeyboardButton(text=f"🗑 حذف: {name}", callback_data=f"del_db_btn_{b_id}")])
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
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO custom_buttons (name, url) VALUES (?, ?)", (data["btn_name"], url))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer("✅ تمت إضافة الزر بنجاح إلى القائمة الرئيسية!")

@dp.callback_query(F.data.startswith("del_db_btn_"))
async def delete_custom_button(callback: CallbackQuery):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    b_id = int(callback.data.replace("del_db_btn_", ""))
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM custom_buttons WHERE id = ?", (b_id,))
    conn.commit()
    conn.close()
    await callback.answer("✅ تم حذف الزر بنجاح!", show_alert=True)
    await admin_manage_buttons(callback)

# إضافة رقم جديد
@dp.callback_query(F.data == "admin_auto_add_num")
async def admin_auto_add_num(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM shop_sections")
    sections = cursor.fetchall()
    conn.close()

    keyboard_buttons = []
    for sec in sections:
        keyboard_buttons.append([InlineKeyboardButton(text=f"📁 {sec[0]}", callback_data=f"sec_{sec[0]}")])
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")])
    
    await callback.message.edit_text("📁 اختر القسم المناسب لإضافة الرقم إليه:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("sec_"))
async def process_section_choice(callback: CallbackQuery, state: FSMContext):
    section_name = callback.data.replace("sec_", "")
    await state.update_data(num_section=section_name)
    await state.set_state(States.waiting_for_country)
    
    back_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_auto_add_num")]])
    await callback.message.edit_text(f"✅ تم اختيار القسم: `{section_name}`\n\n✍️ أرسل تفاصيل الدولة/الرقم (مثال: `هندي انشاء 2022 🇮🇳`):", reply_markup=back_kb, parse_mode="Markdown")
    await callback.answer()

@dp.message(States.waiting_for_country)
async def proc_country(message: Message, state: FSMContext):
    country_details = message.text.strip()
    await state.update_data(country=country_details)
    await state.set_state(States.waiting_for_auto_num_id)
    await message.answer(f"✅ التفاصيل: `{country_details}`\n\n🔢 أرسل معرف (ID) فريد للرقم بالإنجليزية (مثال: `num1`):", parse_mode="Markdown")

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
    await message.answer("🔑 أرسل **API_ID** و **API_HASH** معاً مفصولين بنقطتين (`API_ID:API_HASH`):")

@dp.message(States.waiting_for_auto_api_combo)
async def proc_auto_api_combo(message: Message, state: FSMContext):
    text = message.text.strip()
    if ":" not in text:
        await message.answer("❌ الصيغة غير صحيحة. أعد الإرسال بالشكل `API_ID:API_HASH`:")
        return
    parts = text.split(":", 1)
    try:
        api_id = int(parts[0].strip())
        api_hash = parts[1].strip()
    except ValueError:
        await message.answer("❌ تأكد من صحة البيانات:")
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
        await message.answer("📥 تم إرسال كود التحقق على تليجرام، أرسله الآن:")
    except Exception as e:
        await state.clear()
        await message.answer(f"❌ خطأ بالاتصال:\n`{str(e)}`")

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
        await message.answer("✅ تم إضافة الرقم وتفعيله بنجاح داخل القسم!")
    except SessionPasswordNeededError:
        await state.set_state(States.waiting_for_auto_password)
        await message.answer("🔐 الحساب محمي بكلمة مرور (تحقق بخطوتين)، أرسلها الآن:")
    except Exception as e:
        await message.answer(f"❌ خطأ: `{str(e)}`\nأعد إرسال الكود:")

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

# المتجر، الشراء، والخدمات
@dp.callback_query(F.data == "buy_number_menu")
async def buy_number_menu_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_doc = await get_user(user_id)
    if user_doc.get("banned", False):
        await callback.answer("❌ أنت محظور.", show_alert=True)
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM shop_sections")
    sections = cursor.fetchall()
    conn.close()

    keyboard_buttons = []
    for sec in sections:
        keyboard_buttons.append([InlineKeyboardButton(text=f"📁 {sec[0]}", callback_data=f"shop_sec_{sec[0]}")])
    keyboard_buttons.append([InlineKeyboardButton(text="🛍 أرقامي المشتراة", callback_data="my_purchased_numbers")])
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 القائمة الرئيسية", callback_data="main_menu")])

    text = "🛒 **اختر القسم الذي تريد تصفح أرقامه:**"
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
            keyboard_buttons.append([InlineKeyboardButton(text=f"{num[1]} — ${num[2]:.2f}", callback_data=f"buy_item_{num[0]}")])
    else:
        keyboard_buttons.append([InlineKeyboardButton(text="❌ لا توجد أرقام متاحة في هذا القسم", callback_data="buy_number_menu")])

    keyboard_buttons.append([InlineKeyboardButton(text="🔙 رجوع للأقسام", callback_data="buy_number_menu")])
    
    await callback.message.edit_text(f"📁 **القسم:** `{section_name}`\n\nاختر الرقم المناسب:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_item_"))
async def buy_item_confirmation(callback: CallbackQuery):
    num_id = callback.data.replace("buy_item_", "")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT country, price FROM numbers WHERE num_id = ?", (num_id,))
    item = cursor.fetchone()
    conn.close()

    if not item:
        await callback.answer("❌ عذراً، الرقم غير متوفر حالياً!", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تأكيد الشراء", callback_data=f"confirm_buy_{num_id}")],
        [InlineKeyboardButton(text="❌ إلغاء", callback_data="buy_number_menu")]
    ])
    await callback.message.edit_text(f"🛒 **تأكيد الشراء:**\n\n• التفاصيل: `{item[0]}`\n• السعر: `${item[1]:.2f}`", reply_markup=keyboard, parse_mode="Markdown")
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
        await callback.answer("❌ الرقم غير موجود.", show_alert=True)
        return

    price = item[3]
    user = await get_user(user_id)
    if user.get("balance", 0.0) < price:
        await callback.answer("❌ رصيدك غير كافي لإتمام الشراء!", show_alert=True)
        return

    await update_user(user_id, {"balance": user.get("balance", 0.0) - price})

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM numbers WHERE num_id = ?", (num_id,))
    num_data_json = json.dumps({"num_id": item[0], "section": item[1], "country": item[2], "price": item[3], "phone": item[4], "session": item[5], "api_id": item[6], "api_hash": item[7]})
    cursor.execute("INSERT INTO purchases (user_id, number_id, num_data) VALUES (?, ?, ?)", (user_id, num_id, num_data_json))
    conn.commit()
    conn.close()

    success_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 أرقامي المشتراة", callback_data="my_purchased_numbers")],
        [InlineKeyboardButton(text="🏠 الرئيسية", callback_data="main_menu")]
    ])
    await callback.message.edit_text(f"🎉 **تمت عملية الشراء بنجاح!**\n\n📱 الرقم: `{item[4]}`\n🌍 الدولة: `{item[2]}`\n💵 السعر: `${price:.2f}`", reply_markup=success_kb, parse_mode="Markdown")
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
        data = json.loads(row[1])
        buttons.append([InlineKeyboardButton(text=f"📱 {data['country']} ({data['phone']})", callback_data=f"manage_purchased_{row[0]}")])
    
    buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="buy_number_menu")])
    await callback.message.edit_text("📦 **سجل أرقامك المشتراة:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
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
        await callback.answer("❌ غير موجود.", show_alert=True)
        return

    data = json.loads(row[0])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 طلب كود التحقق (OTP)", callback_data=f"get_otp_{p_id}")],
        [InlineKeyboardButton(text="📋 نسخ كود الجلسة", callback_data=f"get_sess_{p_id}")],
        [InlineKeyboardButton(text="🔙 أرقامي", callback_data="my_purchased_numbers")]
    ])
    await callback.message.edit_text(f"📱 **تفاصيل الرقم:**\n• الدولة: `{data['country']}`\n• الهاتف: `{data['phone']}`", reply_markup=keyboard, parse_mode="Markdown")
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
    if row:
        data = json.loads(row[0])
        await callback.message.answer(f"📋 **كود الجلسة:**\n\n`{data['session']}`", parse_mode="Markdown")
    await callback.answer()

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
    await callback.answer("⏳ جاري جلب الرسائل...", show_alert=True)

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

        if otp_found:
            await callback.message.answer(f"✅ **كود التحقق (OTP):**\n\n`{otp_found}`", parse_mode="Markdown")
        else:
            await callback.message.answer("⚠️ لم يتم العثور على رسالة كود حالياً.")
    except Exception as e:
        await callback.message.answer(f"❌ خطأ: `{str(e)}`")

# حسابي والهدية والتحويل والشحن
@dp.callback_query(F.data == "my_account")
async def my_account_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = await get_user(user_id)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM purchases WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]])
    await callback.message.edit_text(f"⚡ **حسابك:**\n🆔 المعرف: `{user_id}`\n💵 الرصيد: `${user.get('balance', 0.0):.2f}`\n🛒 المشتريات: `{count}`", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "claim_bonus")
async def claim_bonus_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = await get_user(user_id)
    now = datetime.utcnow()
    last_claim = user.get("last_claim")
    if last_claim and (now - last_claim) < timedelta(hours=24):
        await callback.answer("⏳ لقد حصلت على الهدية اليومية مسبقاً.", show_alert=True)
        return

    bonus = float(get_config_val("bonus_amount", "0.01"))
    await update_user(user_id, {"balance": user.get("balance", 0.0) + bonus, "last_claim": now})
    await callback.answer(f"🎁 مبروك! حصلت على هدية بقيمة ${bonus}.", show_alert=True)
    await main_menu_callback(callback, None)

@dp.callback_query(F.data == "recharge_menu")
async def recharge_menu_handler(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ شحن عبر نجوم تليجرام", callback_data="recharge_stars_flow")],
        [InlineKeyboardButton(text="💎 شحن عبر عملة TON", callback_data="recharge_ton_flow")],
        [InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]
    ])
    await callback.message.edit_text("💳 **طرق شحن الرصيد:**", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "recharge_stars_flow")
async def recharge_stars_flow(callback: CallbackQuery, state: FSMContext):
    await state.set_state(States.waiting_for_stars_count)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="recharge_menu")]])
    await callback.message.edit_text("⭐ أرسل عدد النجوم التي تريد شحنها:", reply_markup=keyboard)
    await callback.answer()

@dp.message(States.waiting_for_stars_count)
async def process_stars_invoice(message: Message, state: FSMContext):
    try:
        count = int(message.text.strip())
    except ValueError:
        await message.answer("❌ أدخل رقماً صحيحاً:")
        return
    await state.clear()
    star_price = float(get_config_val("star_price", "0.01"))
    total_cents = max(1, int(count * star_price * 100))
    prices = [LabeledPrice(label=f"{count} Stars", amount=total_cents)]
    await message.bot.send_invoice(
        chat_id=message.chat.id, title="شحن رصيد", description=f"شحن {count} نجمة",
        payload=f"stars_pay_{count}", currency="XTR", prices=prices
    )

@dp.callback_query(F.data == "recharge_ton_flow")
async def recharge_ton_flow(callback: CallbackQuery, state: FSMContext):
    wallet = get_config_val("ton_wallet", "")
    ton_pr = get_config_val("ton_price", "1.35")
    support = get_config_val("support_username", "aaysam")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="recharge_menu")]])
    await callback.message.edit_text(f"💎 **شحن عبر TON:**\nمحفظة التحويل:\n`{wallet}`\nسعر التون: `${ton_pr}`\nراسل الدعم للتأكيد: @{support}", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    payload = message.successful_payment.invoice_payload
    if payload.startswith("stars_pay_"):
        count = int(payload.replace("stars_pay_", ""))
        star_price = float(get_config_val("star_price", "0.01"))
        added = count * star_price
        user_id = message.from_user.id
        user = await get_user(user_id)
        await update_user(user_id, {"balance": user.get("balance", 0.0) + added})
        await message.answer(f"✅ تم الشحن بنجاح وإضافة `${added:.2f}` لرصيدك.")

@dp.callback_query(F.data == "transfer_menu")
async def transfer_menu_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(States.waiting_for_transfer_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="main_menu")]])
    await callback.message.edit_text("💳 أرسل آي دي (ID) المستخدم المراد التحويل إليه:", reply_markup=keyboard)
    await callback.answer()

@dp.message(States.waiting_for_transfer_id)
async def process_transfer_id(message: Message, state: FSMContext):
    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ آي دي غير صحيح:")
        return
    await state.update_data(transfer_id=target_id)
    await state.set_state(States.waiting_for_transfer_amount)
    await message.answer("💵 أرسل المبلغ المراد تحويله:")

@dp.message(States.waiting_for_transfer_amount)
async def process_transfer_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace("$", ""))
    except ValueError:
        await message.answer("❌ مبلغ غير صحيح:")
        return
    sender_id = message.from_user.id
    sender = await get_user(sender_id)
    if sender.get("balance", 0.0) < amount:
        await message.answer("❌ رصيدك غير كافي:")
        await state.clear()
        return
    data = await state.get_data()
    target_id = data["transfer_id"]
    target = await get_user(target_id)
    
    await update_user(sender_id, {"balance": sender.get("balance", 0.0) - amount})
    await update_user(target_id, {"balance": target.get("balance", 0.0) + amount})
    await state.clear()
    await message.answer(f"✅ تم تحويل `${amount:.2f}` بنجاح!")

# إدارة الأرقام والحظر والإذاعة
@dp.callback_query(F.data == "admin_manage_nums")
async def admin_manage_nums_handler(callback: CallbackQuery):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT num_id, section, country FROM numbers")
    nums = cursor.fetchall()
    conn.close()

    if not nums:
        back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
        await callback.message.edit_text("📭 لا توجد أرقام مضافة.", reply_markup=back)
        await callback.answer()
        return

    buttons = []
    for num in nums:
        buttons.append([InlineKeyboardButton(text=f"🗑 [{num[1]}] {num[2]}", callback_data=f"del_num_{num[0]}")])
    buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")])
    await callback.message.edit_text("⚙️ **إدارة وحذف الأرقام:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("del_num_"))
async def delete_number_handler(callback: CallbackQuery):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    num_id = callback.data.replace("del_num_", "")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM numbers WHERE num_id = ?", (num_id,))
    conn.commit()
    conn.close()
    await callback.answer("✅ تم حذف الرقم بنجاح!", show_alert=True)
    await admin_manage_nums_handler(callback)

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    u_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM numbers")
    n_count = cursor.fetchone()[0]
    conn.close()
    back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
    await callback.message.edit_text(f"📊 **إحصائيات البوت:**\n👥 المستخدمين: `{u_count}`\n📱 الأرقام المتاحة: `{n_count}`", reply_markup=back, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    await state.set_state(States.waiting_for_broadcast_msg)
    back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 رجوع", callback_data="admin_panel_main")]])
    await callback.message.edit_text("📢 أرسل رسالة الإذاعة:", reply_markup=back)
    await callback.answer()

@dp.message(States.waiting_for_broadcast_msg)
async def execute_broadcast(message: Message, state: FSMContext):
    txt = message.text
    await state.clear()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    count = 0
    for u in users:
        try:
            await bot.send_message(u[0], txt)
            count += 1
            await asyncio.sleep(0.02)
        except Exception:
            pass
    await message.answer(f"✅ تمت الإذاعة إلى `{count}` مستخدم.")

@dp.callback_query(F.data == "admin_ban_user")
async def ban_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    await state.set_state(States.waiting_for_ban_id)
    await callback.message.edit_text("🚫 أرسل آي دي (ID) المستخدم للحظر:")
    await callback.answer()

@dp.message(States.waiting_for_ban_id)
async def ban_exec(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        return await message.answer("آي دي خطأ:")
    await state.clear()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET banned = 1 WHERE user_id = ?", (uid,))
    conn.commit()
    conn.close()
    await message.answer(f"✅ تم حظر المستخدم (`{uid}`).")

@dp.callback_query(F.data == "admin_unban_user")
async def unban_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    await state.set_state(States.waiting_for_unban_id)
    await callback.message.edit_text("✅ أرسل آي دي (ID) المستخدم لرفع الحظر:")
    await callback.answer()

@dp.message(States.waiting_for_unban_id)
async def unban_exec(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        return await message.answer("آي دي خطأ:")
    await state.clear()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET banned = 0 WHERE user_id = ?", (uid,))
    conn.commit()
    conn.close()
    await message.answer(f"✅ تم رفع الحظر عن المستخدم (`{uid}`).")

@dp.callback_query(F.data == "admin_change_star_price")
async def star_price_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != DEFAULT_ADMIN_USER_ID:
        return
    await state.set_state(States.waiting_for_star_price)
    await callback.message.edit_text("⭐ أرسل السعر الجديد للنجمة الواحدة بالدولار (مثال: `0.02`):")
    await callback.answer()

@dp.message(States.waiting_for_star_price)
async def star_price_exec(message: Message, state: FSMContext):
    try:
        val = float(message.text.strip().replace("$", ""))
    except ValueError:
        return await message.answer("قيمة خطأ:")
    set_config_val("star_price", val)
    await state.clear()
    await message.answer(f"✅ تم تحديث سعر النجمة إلى: `{val}`")

# =====================================================================
# 🏁 [تشغيل البوت]
# =====================================================================

async def main():
    print("🚀 Bot is running completely dynamic...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
