import os
import re
import asyncio
import threading
from telebot import types
import telebot
from telethon import TelegramClient, events
from telethon.sessions import StringSession

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8526493972:AAEVb5f6rIcPCqMu1wVvEKop3QXvSih9YaE")
bot = telebot.TeleBot(BOT_TOKEN)

SESSION_STRING = os.environ.get("SESSION_STRING", "")
API_ID = int(os.environ.get("API_ID", 33650280))
API_HASH = os.environ.get("API_HASH", "0d2eeef5980251c6cce7389fc3b0f5d2")
PHONE_NUMBER = "+16576954958"

active_otps = {}
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
        code = active_otps.get(PHONE_NUMBER, "لم يتم العثور على كود بعد . ⏳")
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_get_code = types.InlineKeyboardButton("- طلب كود", callback_data="get_otp")
        markup.add(btn_get_code)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"📥 تم جلب كود جديد\n\n• الرقم : `{PHONE_NUMBER}`\n• الكود : `{code}`", reply_markup=markup, parse_mode="Markdown")

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

def start_telegram_listener():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

    @client.on(events.NewMessage(chats=('Telegram', 777000)))
    async def otp_listener(event):
        msg_text = event.message.message
        codes = re.findall(r'\b\d{5,6}\b', msg_text)
        if codes:
            active_otps[PHONE_NUMBER] = codes[0]
        else:
            active_otps[PHONE_NUMBER] = msg_text

    try:
        client.start(phone=PHONE_NUMBER)
        client.run_until_disconnected()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    t = threading.Thread(target=start_telegram_listener)
    t.daemon = True
    t.start()
    bot.infinity_polling()
