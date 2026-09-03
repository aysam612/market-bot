import os
import re
import asyncio
from telebot import types
import telebot
from telethon import TelegramClient
from telethon.sessions import StringSession

# إعدادات البوت والسيشن
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8526493972:AAEVb5f6rIcPCqMu1wVvEKop3QXvSih9YaE")
bot = telebot.TeleBot(BOT_TOKEN)

SESSION_STRING = os.environ.get("SESSION_STRING", "1AZWarzYBu4DsJhY23nLFER2qDvE9lqCBXrQ27HVWKLqXChIJflm3zoBMhdsya9NdpEfChtBNOBW7PLtdyciAT5rXmZKBC7ky85O3NzH_DWwHs-K_Jrqal9vPyPawIjgq0S3wEumn2ntGrXL3sZObdteRHVh5M-1mdnW7_vIa7W3DQk00P_k7e595JFTtY0kvbC5CeI4yTswQ0ZFxBDgMtH099iKenqtEB6K3-somzxxNiZaPTMl_XYJCNmaBfOA_f-tIb_I1jjekQ-hVeKLh9d5hP2b-05rH1cuqb92EZGWMNm6Wy3KW86nGC7ShF3Cum5yoYlwbj-By4R8XlI3otfuyOvFz5Io=")
API_ID = int(os.environ.get("API_ID", 34198296))
API_HASH = os.environ.get("API_HASH", "8b007a14ebc08f01120d0ebs8ba4d595")
PHONE_NUMBER = "+13025060244"

# تخزين الأرقام المباعة ومؤشر نفاد الرقم من المتجر العام
user_purchased_numbers = {}
sold_out_status = False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_buy = types.InlineKeyboardButton("🛒 شراء أرقام بالنجوم ⭐", callback_data="buy_numbers")
    btn_lang = types.InlineKeyboardButton("🌐 Change to English", callback_data="lang_en")
    markup.add(btn_buy, btn_lang)
    bot.send_message(message.chat.id, f"بوت أرقام تليجرام المميزة\n\n• احصل على أرقام مميزة عبر نجوم تليجرام ⭐\n• الشراء فوري وأمن بالنجوم\n\n🆔 ID: `{user_id}`\n\nاختر من القائمة 👇", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    global sold_out_status

    if call.data == "buy_numbers":
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        # إذا تم بيع الرقم، يتم إخفائه من المتجر العام
        if sold_out_status:
            btn_back = types.InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
            markup.add(btn_back)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="عذراً، لا توجد أرقام متاحة في المتجر حالياً 🔴\nتم بيع الرقم الوحيد.", reply_markup=markup, parse_mode="Markdown")
            return

        btn_num = types.InlineKeyboardButton("🇺🇸 أمريكا (1) - 44 نجمة ⭐", callback_data="getnum_1")
        btn_back = types.InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
        markup.add(btn_num, btn_back)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="اختر الدولة 🌐 (الشراء بالنجوم)", reply_markup=markup, parse_mode="Markdown")

    elif call.data == "main_menu":
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_buy = types.InlineKeyboardButton("🛒 شراء أرقام بالنجوم ⭐", callback_data="buy_numbers")
        btn_lang = types.InlineKeyboardButton("🌐 Change to English", callback_data="lang_en")
        markup.add(btn_buy, btn_lang)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"بوت أرقام تليجرام المميزة\n\n• احصل على أرقام مميزة عبر نجوم تليجرام ⭐\n• الشراء فوري وأمن بالنجوم\n\n🆔 ID: `{user_id}`\n\nاختر من القائمة 👇", reply_markup=markup, parse_mode="Markdown")

    elif call.data == "getnum_1":
        if sold_out_status:
            bot.answer_callback_query(call.id, text="عذراً، تم بيع هذا الرقم مسبقاً!", show_alert=True)
            return

        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_pay = types.InlineKeyboardButton("⭐ Pay 44 Stars", callback_data="pay_stars_1")
        btn_back = types.InlineKeyboardButton("🔙 رجوع", callback_data="buy_numbers")
        markup.add(btn_pay, btn_back)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="شراء رقم أمريكي مميز\n\n💰 السعر: **44 نجمة ⭐**\n⚠️ تنبيه هام: لو سجلت خروج من الحساب بعد استلامه لن يتم تعويضك بأي شكل.", reply_markup=markup, parse_mode="Markdown")

    elif call.data == "pay_stars_1":
        # بيع الرقم، حجزه للمستخدم، وحذفه من المتجر العام
        sold_out_status = True
        user_purchased_numbers[user_id] = PHONE_NUMBER
        
        reply_text = f"✅ تم استلام الرقم بنجاح!\n\n• الرقم : `{PHONE_NUMBER}`\n• وتم إزالة الرقم من المتجر العام ليبقى خاصاً بك وحدك.\n\n• حاول تسجيل الدخول بالرقم في تطبيق تليجرام\nثم اضغط على زر **طلب الكود** أدناه (يمكنك التحديث في أي وقت)"
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_get_code = types.InlineKeyboardButton("🔄 - طلب كود (تحديث)", callback_data="get_otp")
        markup.add(btn_get_code)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=reply_text, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "get_otp":
        code_result = fetch_otp_on_demand()
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_get_code = types.InlineKeyboardButton("🔄 - طلب كود (تحديث)", callback_data="get_otp")
        markup.add(btn_get_code)
        
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id, 
                message_id=call.message.message_id, 
                text=f"📥 نتيجة جلب الكود\n\n• الرقم : `{PHONE_NUMBER}`\n• التفاصيل/الكود : `{code_result}`\n\n*(يمكنك الضغط على زر التحديث بالأسفل لجلب أي كود جديد في أي وقت)*", 
                reply_markup=markup, 
                parse_mode="Markdown"
            )
        except Exception:
            bot.answer_callback_query(call.id, text=f"الكود الحالي: {code_result}")

    elif call.data == "lang_en":
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_buy = types.InlineKeyboardButton("🛒 Buy Numbers with Stars ⭐", callback_data="buy_numbers_en")
        btn_lang = types.InlineKeyboardButton("🌐 تغيير إلى العربية", callback_data="main_menu")
        markup.add(btn_buy, btn_lang)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"Premium Telegram Numbers Bot\n\n• Get premium numbers using Telegram Stars ⭐\n• Instant and secure purchase\n\n🆔 ID: `{user_id}`\n\nChoose from the menu 👇", reply_markup=markup, parse_mode="Markdown")

    elif call.data == "buy_numbers_en":
        markup = types.InlineKeyboardMarkup(row_width=1)
        if sold_out_status:
            btn_back = types.InlineKeyboardButton("🔙 Back", callback_data="lang_en")
            markup.add(btn_back)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Sorry, no numbers available right now 🔴", reply_markup=markup, parse_mode="Markdown")
            return

        btn_num = types.InlineKeyboardButton("🇺🇸 USA (1) - 44 Stars ⭐", callback_data="getnum_1")
        btn_back = types.InlineKeyboardButton("🔙 Back", callback_data="lang_en")
        markup.add(btn_num, btn_back)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Select Country 🌐", reply_markup=markup, parse_mode="Markdown")

def fetch_otp_on_demand():
    """دالة تتصل لحظياً باستخدام الجلسة المحفوظة وتجلب أحدث رسالة من تليجرام"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def main():
            if not SESSION_STRING:
                return "خطأ: لم يتم ضبط السيشن بشكل صحيح ❌"
                
            client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
            await client.connect()
            if not await client.is_user_authorized():
                await client.disconnect()
                return "الجلسة غير صالحة أو منتهية ❌"
            
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
    print("Starting bot...")
    bot.remove_webhook()
    bot.infinity_polling()
