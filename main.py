import os
import re
import random
import asyncio
import sqlite3
from datetime import datetime, timedelta
from telebot import types
import telebot
from telethon import TelegramClient
from telethon.sessions import StringSession

# إعدادات البوت الأساسية مع التوكن الخاص بك
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8526493972:AAEVb5f6rIcPCqMu1wVvEKop3QXvSih9YaE")
bot = telebot.TeleBot(BOT_TOKEN)

# رابط قناتك الرسمية على تليجرام
CHANNEL_URL = "https://t.me/VPP8P"

# ================= إعداد قاعدة البيانات SQLite للإحالات والرصيد =================
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    last_bonus TEXT,
    referred_by INTEGER
)
""")
conn.commit()

# ================= جدول الأرقام المتاحة =================
NUMBERS_STORE = {
    "1": {
        "phone": "+13025060244",
        "session": "1AZWarzYBu4DsJhY23nLFER2qDvE9lqCBXrQ27HVWKLqXChIJflm3zoBMhdsya9NdpEfChtBNOBW7PLtdyciAT5rXmZKBC7ky85O3NzH_DWwHs-K_Jrqal9vPyPawIjgq0S3wEumn2ntGrXL3sZObdteRHVh5M-1mdnW7_vIa7W3DQk00P_k7e595JFTtY0kvbC5CeI4yTswQ0ZFxBDgMtH099iKenqtEB6K3-somzxxNiZaPTMl_XYJCNmaBfOA_f-tIb_I1jjekQ-hVeKLh9d5hP2b-05rH1cuqb92EZGWMNm6Wy3KW86nGC7ShF3Cum5yoYlwbj-By4R8XlI3otfuyOvFz5Io=",
        "api_id": 34198296,
        "api_hash": "8b007a14ebc08f01120d0ebs8ba4d595",
        "sold": False,
        "buyer_id": None
    },
    "2": {
        "phone": "+13649004531",
        "session": "1AZWarzYBu2uAspmH_zOu7qW53ONrFQw6vhIypDVm5N9LMiUAmBhkON--qPfBcT83HDjTJUeBWNJQ0UELHaLo0xnDnVi3MTm9ZyaGlIO-h5P2LH7OB1jghSFqD_ysUgbUagvN6p8BElr4gmVNO2L5I5sOL52rzHHwbcRCKB-DQvrXH3D7X7yBUXT7UZ8kKs0Ve_926fUoLoUzI1UBvGmdP5Gd8cYHmZJiDjUxFkALKNHlexdJToWLiY-svegkzXGq1ICBjaGGNCMAk__P1-W-HvRv2NbTfX3SDaPFzitNJzqRfxFDf8tysezYXHnzRbBz4cvqEQqcSVrTwvwI6kW7h5uA8Pz2zk0=",
        "api_id": 34198296,
        "api_hash": "8b007a14ebc08f01120d0ebs8ba4d595",
        "sold": False,
        "buyer_id": None
    }
}
# ==============================================================================================

# القائمة الرئيسية
def get_main_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_buy = types.InlineKeyboardButton("🛒 شراء رقم (80 سنت أو 44 نجمة)", callback_data="buy_number_menu")
    btn_ref = types.InlineKeyboardButton("🎁 تجميع النقاط والهدية اليومية", callback_data="ref_menu")
    btn_recharge = types.InlineKeyboardButton("⭐ شحن الرصيد المخصص بالنجوم", callback_data="recharge_menu")
    btn_channel = types.InlineKeyboardButton("📢 قناة المتجر (X9)", url=CHANNEL_URL)
    markup.add(btn_buy, btn_ref, btn_recharge, btn_channel)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    args = message.text.split()
    
    cursor.execute("SELECT balance, last_bonus FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        ref_id = None
        if len(args) > 1 and args[1].startswith("ref_"):
            try:
                potential_ref = int(args[1].replace("ref_", ""))
                if potential_ref != user_id:
                    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (potential_ref,))
                    if cursor.fetchone():
                        ref_id = potential_ref
            except ValueError:
                pass
            
        cursor.execute("INSERT INTO users (user_id, balance, referred_by) VALUES (?, 0, ?)", (user_id, ref_id))
        conn.commit()
        
        if ref_id:
            cursor.execute("UPDATE users SET balance = balance + 1 WHERE user_id = ?", (ref_id,))
            conn.commit()
            try:
                bot.send_message(ref_id, "🎉 مبروك! دخل شخص جديد عبر رابط إحالتك وحصلت على **1 سنت** إضافي!", parse_mode="Markdown")
            except Exception:
                pass

    welcome_text = (
        "أهلاً بك عزيزي في متجر X9 للأرقام والخدمات 🌐!\n\n"
        "• احصل على أرقام أمريكية مميزة ومفعلة.\n"
        "• اجمع النقاط عبر الإحالات أو اشحن رصيدك بالنجوم.\n\n"
        f"🆔 معرفك: `{user_id}`\n"
        "👑 المالك: @diddy0\n\n"
        "اختر ما يناسبك من القائمة 👇"
    )
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_markup(user_id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id

    if call.data == "main_menu":
        bot.edit_message_text(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            text="🏠 القائمة الرئيسية:", 
            reply_markup=get_main_markup(user_id), 
            parse_mode="Markdown"
        )

    elif call.data == "buy_number_menu":
        markup = types.InlineKeyboardMarkup(row_width=1)
        available_count = sum(1 for data in NUMBERS_STORE.values() if not data["sold"])
        btn_stars = types.InlineKeyboardButton(f"⭐ شراء بالنجوم (متاح: {available_count}) - 44 نجمة", callback_data="buy_random_usa")
        btn_balance = types.InlineKeyboardButton("💰 شراء برصيد النقاط (80 سنت)", callback_data="buy_with_balance")
        btn_back = types.InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
        markup.add(btn_stars, btn_balance, btn_back)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            text="🛍️ **اختر طريقة شراء الرقم:**", 
            reply_markup=markup, 
            parse_mode="Markdown"
        )

    elif call.data == "buy_with_balance":
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        balance = cursor.fetchone()[0]
        
        if balance < 80:
            bot.answer_callback_query(call.id, text=f"❌ رصيدك ({balance} سنت) لا يكفي! يلزمك 80 سنت.", show_alert=True)
            return
        
        # اختيار رقم عشوائي متاح لإعطائه مقابل الرصيد
        available_numbers = [num_id for num_id, data in NUMBERS_STORE.items() if not data["sold"]]
        if not available_numbers:
            bot.answer_callback_query(call.id, text="عذراً، نفدت الأرقام حالياً!", show_alert=True)
            return
            
        chosen_num_id = random.choice(available_numbers)
        data = NUMBERS_STORE[chosen_num_id]
        
        data["sold"] = True
        data["buyer_id"] = user_id
        cursor.execute("UPDATE users SET balance = balance - 80 WHERE user_id = ?", (user_id,))
        conn.commit()
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🔄 - طلب كود (تحديث)", callback_data=f"get_otp_{chosen_num_id}"))
        markup.add(types.InlineKeyboardButton("🔙 عودة للقائمة", callback_data="main_menu"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=(
                f"✅ **تم الشراء برصيد النقاط بنجاح!**\n\n"
                f"📱 **رقمك هو:** `{data['phone']}`\n\n"
                f"⚠️ **تنبيه:** لا تسجل خروج من الحساب.\n"
                f"اضغط على زر طلب الكود أدناه لمعرفة الـ OTP."
            ),
            reply_markup=markup,
            parse_mode="Markdown"
        )

    elif call.data == "ref_menu":
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        balance = row[0] if row else 0
        
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🎁 استلام الهدية اليومية (1 سنت)", callback_data="claim_bonus"))
        markup.add(types.InlineKeyboardButton("🔙 عودة للقائمة الرئيسية", callback_data="main_menu"))
        
        text = (
            "🎁 **نظام تجميع النقاط والإحالات**\n\n"
            f"💰 رصيدك الحالي: **{balance} سنت**\n\n"
            "📌 **رابط الإحالة الخاص بك:**\n"
            f"`{ref_link}`\n\n"
            "🔗 شارك الرابط، وكل شخص يدخل تحصل على **1 سنت**!\n"
            "⏰ وتحصل على **1 سنت** مجاني يومياً."
        )
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "claim_bonus":
        now = datetime.now()
        cursor.execute("SELECT last_bonus FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        last_bonus_str = row[0] if row else None
        
        if last_bonus_str:
            last_bonus_time = datetime.fromisoformat(last_bonus_str)
            if now - last_bonus_time < timedelta(hours=24):
                remaining = timedelta(hours=24) - (now - last_bonus_time)
                hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                bot.answer_callback_query(call.id, text=f"⏳ استلمت هديتك مسبقاً. انتظر: {hours}س و {minutes}د.", show_alert=True)
                return

        cursor.execute("UPDATE users SET balance = balance + 1, last_bonus = ? WHERE user_id = ?", (now.isoformat(), user_id))
        conn.commit()
        
        bot.answer_callback_query(call.id, text="🎉 مبروك! تمت إضافة 1 سنت لهديتك اليومية.", show_alert=True)
        
        # تحديث لوحة الإحالات
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        balance = cursor.fetchone()[0]
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🎁 استلام الهدية اليومية (1 سنت)", callback_data="claim_bonus"))
        markup.add(types.InlineKeyboardButton("🔙 عودة للقائمة الرئيسية", callback_data="main_menu"))
        
        text = (
            "🎁 **نظام تجميع النقاط والإحالات**\n\n"
            f"💰 رصيدك الحالي: **{balance} سنت**\n\n"
            f"📌 **رابط الإحالة الخاص بك:**\n`{ref_link}`"
        )
        try:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass

    elif call.data == "recharge_menu":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("⭐ شحن 10 نجوم (20 سنت)", callback_data="recharge_10"))
        markup.add(types.InlineKeyboardButton("⭐ شحن 50 نجمة (100 سنت)", callback_data="recharge_50"))
        markup.add(types.InlineKeyboardButton("🔙 عودة للقائمة الرئيسية", callback_data="main_menu"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="⭐ **شحن الرصيد الداخلي عبر نجوم تليجرام:**\nاختر باقة الشحن المناسبة:",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    elif call.data.startswith("recharge_"):
        stars = int(call.data.split("_")[1])
        cents = stars * 2
        try:
            prices = [types.LabeledPrice(label=f"Recharge {cents} Cents", amount=stars)]
            bot.send_invoice(
                chat_id=call.message.chat.id,
                title=f"شحن {cents} سنت داخلي",
                description=f"إضافة {cents} سنت إلى رصيدك البوت مقابل {stars} نجمة تليجرام",
                invoice_payload=f"recharge_custom_{stars}",
                provider_token="",
                currency="XTR",
                prices=prices,
                start_parameter=f"recharge-{stars}"
            )
        except Exception as e:
            bot.answer_callback_query(call.id, text=f"خطأ: {str(e)}", show_alert=True)

    elif call.data == "buy_random_usa":
        available_numbers = [num_id for num_id, data in NUMBERS_STORE.items() if not data["sold"]]
        
        if not available_numbers:
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="buy_number_menu"))
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="عذراً، نفدت جميع الأرقام حالياً 🔴", reply_markup=markup, parse_mode="Markdown")
            return

        chosen_num_id = random.choice(available_numbers)

        try:
            prices = [types.LabeledPrice(label=f"USA Number #{chosen_num_id}", amount=44)]
            bot.send_invoice(
                chat_id=call.message.chat.id,
                title="شراء رقم أمريكي مميز - X9",
                description="⚠️ تنبيه: لو سجلت خروج من الحساب لن يتم تعويضك.",
                invoice_payload=f"buy_usa_number_{chosen_num_id}",
                provider_token="",  
                currency="XTR",     
                prices=prices,
                start_parameter=f"buy-number-{chosen_num_id}"
            )
        except Exception as e:
            bot.answer_callback_query(call.id, text=f"خطأ: {str(e)}", show_alert=True)

    elif call.data.startswith("get_otp_"):
        num_id = call.data.split("_")[2]
        data = NUMBERS_STORE.get(num_id)
        
        if not data or data["buyer_id"] != user_id:
            bot.answer_callback_query(call.id, text="هذا الرقم ليس ملكاً لك!", show_alert=True)
            return

        bot.answer_callback_query(call.id, text="🔄 جاري جلب الكود...")

        code_result = fetch_otp_on_demand(data["session"], data["api_id"], data["api_hash"])
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🔄 - طلب كود (تحديث)", callback_data=f"get_otp_{num_id}"))
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
        
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id, 
                message_id=call.message.message_id, 
                text=(
                    f"📥 **متجر X9** - نتيجة جلب الكود للرقم\n\n"
                    f"• كود التحقق / الرسالة : `{code_result}`\n\n"
                    f"⚠️ **تنبيه:** لا تسجل خروج من الحساب نهائياً."
                ), 
                reply_markup=markup, 
                parse_mode="Markdown"
            )
        except Exception:
            pass

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    payload = pre_checkout_query.invoice_payload
    if payload.startswith("buy_usa_number_"):
        num_id = payload.split("_")[-1]
        data = NUMBERS_STORE.get(num_id)
        if not data or data["sold"]:
            bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False, error_message="عذراً، هذا الرقم تم بيعه لشخص آخر!")
            return
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload
    
    if payload.startswith("buy_usa_number_"):
        num_id = payload.split("_")[-1]
        data = NUMBERS_STORE.get(num_id)
        if not data:
            return

        data["sold"] = True
        data["buyer_id"] = user_id
        
        reply_text = (
            f"✅ **تم دفع 44 نجمة بنجاح واستلام الرقم!**\n\n"
            f"📱 **رقمك هو:** `{data['phone']}`\n\n"
            f"⚠️ **تنبيه:** لا تسجل خروج من الحساب بعد استلامه.\n"
            f"اضغط على زر **طلب الكود** أدناه لجلب الـ OTP."
        )
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🔄 - طلب كود (تحديث)", callback_data=f"get_otp_{num_id}"))
        markup.add(types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu"))
        
        bot.send_message(message.chat.id, reply_text, reply_markup=markup, parse_mode="Markdown")

    elif payload.startswith("recharge_custom_"):
        stars = int(payload.split("_")[-1])
        cents = stars * 2
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (cents, user_id))
        conn.commit()
        
        bot.send_message(
            message.chat.id,
            f"⭐ تم شحن رصيدك بنجاح بـ **{cents} سنت** مقابل {stars} نجمة!",
            reply_markup=get_main_markup(user_id),
            parse_mode="Markdown"
        )

def fetch_otp_on_demand(session_str, api_id, api_hash):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def main():
            if not session_str:
                return "خطأ: السيشن غير صالح ❌"
                
            client = TelegramClient(StringSession(session_str), api_id, api_hash)
            await client.connect()
            if not await client.is_user_authorized():
                await client.disconnect()
                return "الجلسة منتهية أو غير صالحة ❌"
            
            messages = await client.get_messages(777000, limit=1)
            if not messages:
                await client.disconnect()
                return "لم يتم العثور على رسائل بعد ⏳"
            
            latest_msg = messages[0].message
            await client.disconnect()
            
            codes = re.findall(r'\b\d{5,6}\b', latest_msg)
            if codes:
                return codes[0]
            return latest_msg

        return loop.run_until_complete(main())
    except Exception as e:
        return f"خطأ بالاتصال: {str(e)}"

if __name__ == '__main__':
    print("Starting X9 Full Bot (Referrals + Stars Recharge + Telethon Sessions)...")
    bot.remove_webhook()
    bot.infinity_polling()
