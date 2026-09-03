import os
import re
import asyncio
from telebot import types
import telebot
from telethon import TelegramClient
from telethon.sessions import StringSession

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8526493972:AAEVb5f6rIcPCqMu1wVvEKop3QXvSih9YaE")
bot = telebot.TeleBot(BOT_TOKEN)

SESSION_STRING = os.environ.get("SESSION_STRING", "")
API_ID = int(os.environ.get("API_ID", 34198296))
API_HASH = os.environ.get("API_HASH", "8b007a14ebc08f01120d0ebs8ba4d595")
PHONE_NUMBER = "+13025060244"

user_purchased_numbers = {}

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

    if call.data == "buy_numbers":
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_num = types.InlineKeyboardButton("🇺🇸 أمريكا (1) - 0 نجوم ⭐", callback_data="getnum_1")
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
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_pay = types.InlineKeyboardButton("⭐ Pay 0", callback_data="pay_stars_1")
        btn_back = types.InlineKeyboardButton("🔙 رجوع", callback_data="buy_numbers")
        markup.add(btn_pay, btn_back)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="شراء رقم أمريكي مميز\n\n⚠️ تنبيه هام: لو سجلت خروج من الحساب بعد استلامه لن يتم تعويضك بأي شكل.", reply_markup=markup, parse_mode="Markdown")

    elif call.data == "pay_stars_1":
        user_purchased_numbers[user_id] = PHONE_NUMBER
        reply_text = f"✅ تم استلام الرقم بنجاح!\n\n• الرقم : `{PHONE_NUMBER}`\n\n• حاول تسجيل الدخول بالرقم في تطبيق تليجرام\nثم اضغط على زر **- طلب كود** أدناه"
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_get_code = types.InlineKeyboardButton("- طلب كود", callback_data="get_otp")
        markup.add(btn_get_code)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=reply_text, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "get_otp":
        # جلب الكود فوراً عند الضغط باستخدام الجلسة
        code_result = fetch_otp_on_demand()
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_get_code = types.InlineKeyboardButton("- طلب كود", callback_data="get_otp")
        markup.add(btn_get_code)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"📥 نتيجة جلب الكود\n\n• الرقم : `{PHONE_NUMBER}`\n• التفاصيل/الكود : `{code_result}`", reply_markup=markup, parse_mode="Markdown")

    elif call.data == "lang_en":
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_buy = types.InlineKeyboardButton("🛒 Buy Numbers with Stars ⭐", callback_data="buy_numbers_en")
        btn_lang = types.InlineKeyboardButton("🌐 تغيير إلى العربية", callback_data="main_menu")
        markup.add(btn_buy, btn_lang)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"Premium Telegram Numbers Bot\n\n• Get premium numbers using Telegram Stars ⭐\n• Instant and secure purchase\n\n🆔 ID: `{user_id}`\n\nChoose from the menu 👇", reply_markup=markup, parse_mode="Markdown")

    elif call.data == "buy_numbers_en":
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_num = types.InlineKeyboardButton("🇺🇸 USA (1) - 0 Stars ⭐", callback_data="getnum_1")
        btn_back = types.InlineKeyboardButton("🔙 Back", callback_data="lang_en")
        markup.add(btn_num, btn_back)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Select Country 🌐", reply_markup=markup, parse_mode="Markdown")

def fetch_otp_on_demand():
    """دالة تتصل لحظياً باستخدام الجلسة وتجلب أحدث رسالة من تليجرام"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def main():
            client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
            await client.connect()
            if not await client.is_user_authorized():
                await client.disconnect()
                return "الجلسة غير صالحة أو منتهية ❌"
            
            # جلب آخر الرسائل من رقم الخدمة الرسمي 777000 أو الدردشة مع تليجرام
            messages = await client.get_messages(777000, limit=1)
            if not messages:
                await client.disconnect()
                return "لم يتم العثور على رسائل بعد ⏳"
            
            latest_msg = messages[0].message
            await client.disconnect()
            
            # استخراج الكود (5 أو 6 أرقام)
            codes = re.findall(r'\b\d{5,6}\b', latest_msg)
            if codes:
                return codes[0]
            return latest_msg

        return loop.run_until_complete(main())
    except Exception as e:
        return f"خطأ بالاتصال: {str(e)}"

if __name__ == '__main__':
    bot.infinity_polling()
