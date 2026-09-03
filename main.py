import os
import re
import random
import asyncio
from telebot import types
import telebot
from telethon import TelegramClient
from telethon.sessions import StringSession

# إعدادات البوت الأساسية
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8526493972:AAEVb5f6rIcPCqMu1wVvEKop3QXvSih9YaE")
bot = telebot.TeleBot(BOT_TOKEN)

# رابط قناتك الرسمية على تليجرام
CHANNEL_URL = "https://t.me/VPP8P"

# ================= جدول الأرقام المتاحة (رقمين بسعر 44 نجمة حقيقية لكل رقم) =================
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

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_buy = types.InlineKeyboardButton("🇺🇸 🛒 شراء رقم أمريكي فوري (عشوائي) - 44 ⭐", callback_data="buy_random_number")
    btn_channel = types.InlineKeyboardButton("📢 قناة المتجر (X9)", url=CHANNEL_URL)
    btn_lang = types.InlineKeyboardButton("🌐 Change to English", callback_data="lang_en")
    markup.add(btn_buy, btn_channel, btn_lang)
    
    welcome_text = (
        "👋 أهلاً بك عزيزي في **متجر X9** للأرقام المميزة 🌐!\n\n"
        "• احصل على أرقام أمريكية مميزة ومفعلة لجميع الاستخدامات.\n"
        "• الشراء فوري وعشوائي وسريع عبر **نجوم تليجرام (Stars ⭐)**.\n"
        "• إمكانية طلب كود التحقق (OTP) بشكل فوري وبكل سهولة بعد الشراء.\n\n"
        f"🆔 معرفك الشخصي: `{user_id}`\n\n"
        "اختر ما يناسبك من القائمة 👇"
    )
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id

    if call.data == "buy_random_number":
        available_numbers = [num_id for num_id, data in NUMBERS_STORE.items() if not data["sold"]]
        
        if not available_numbers:
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton("📢 قناة المتجر (X9)", url=CHANNEL_URL))
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"))
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="عذراً، نفدت جميع الأرقام الأمريكية من متجر X9 حالياً 🔴", reply_markup=markup, parse_mode="Markdown")
            return

        chosen_num_id = random.choice(available_numbers)

        try:
            prices = [types.LabeledPrice(label=f"USA Number #{chosen_num_id}", amount=44)]
            bot.send_invoice(
                chat_id=call.message.chat.id,
                title=f"🇺🇸 شراء رقم أمريكي مميز - متجر X9",
                description="رقم أمريكي لاستخدام تليجرام (اختيار عشوائي) + جلسة خاصة بك وحدك مع إمكانية طلب الكود فوري.",
                invoice_payload=f"buy_usa_number_{chosen_num_id}",
                provider_token="",  # فارغ لنجوم تليجرام (XTR)
                currency="XTR",     # عملة نجوم تليجرام
                prices=prices,
                start_parameter=f"buy-number-{chosen_num_id}"
            )
        except Exception as e:
            bot.answer_callback_query(call.id, text=f"خطأ في إنشاء الفاتورة: {str(e)}", show_alert=True)

    elif call.data == "main_menu":
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_buy = types.InlineKeyboardButton("🇺🇸 🛒 شراء رقم أمريكي فوري (عشوائي) - 44 ⭐", callback_data="buy_random_number")
        btn_channel = types.InlineKeyboardButton("📢 قناة المتجر (X9)", url=CHANNEL_URL)
        btn_lang = types.InlineKeyboardButton("🌐 Change to English", callback_data="lang_en")
        markup.add(btn_buy, btn_channel, btn_lang)
        
        welcome_text = (
            "👋 أهلاً بك عزيزي في **متجر X9** للأرقام المميزة 🌐!\n\n"
            "• احصل على أرقام أمريكية مميزة ومفعلة لجميع الاستخدامات.\n"
            "• الشراء فوري وعشوائي وسريع عبر **نجوم تليجرام (Stars ⭐)**.\n"
            "• إمكانية طلب كود التحقق (OTP) بشكل فوري وبكل سهولة بعد الشراء.\n\n"
            f"🆔 معرفك الشخصي: `{user_id}`\n\n"
            "اختر ما يناسبك من القائمة 👇"
        )
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=welcome_text, reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("get_otp_"):
        num_id = call.data.split("_")[2]
        data = NUMBERS_STORE.get(num_id)
        
        if not data or data["buyer_id"] != user_id:
            bot.answer_callback_query(call.id, text="هذا الرقم ليس ملكاً لك!", show_alert=True)
            return

        code_result = fetch_otp_on_demand(data["session"], data["api_id"], data["api_hash"])
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_get_code = types.InlineKeyboardButton("🔄 - طلب كود (تحديث)", callback_data=f"get_otp_{num_id}")
        markup.add(btn_get_code)
        
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id, 
                message_id=call.message.message_id, 
                text=(
                    f"📥 **متجر X9** - نتيجة جلب الكود\n\n"
                    f"• كود التحقق / الرسالة : `{code_result}`\n\n"
                    f"⚠️ **تنبيه هام جداً:**\n"
                    f"• إياك ثم إياك عمل (تسجيل خروج / Logout) من الحساب داخل تطبيق تليجرام!\n"
                    f"• في حال قمت بتسجيل الخروج أو فقدان الحساب، **لا يوجد تعويض نهائياً** ولا يتحمل متجر X9 أي مسؤولية بعد استلام الرقم.\n\n"
                    f"*(قم بإدخال الكود، واضغط على زر التحديث بالأسفل لجلب أي كود جديد)*"
                ), 
                reply_markup=markup, 
                parse_mode="Markdown"
            )
        except Exception:
            bot.answer_callback_query(call.id, text=f"الكود الحالي: {code_result}")

    elif call.data == "lang_en":
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_buy = types.InlineKeyboardButton("🇺🇸 🛒 Buy USA Number (Random) - 44 ⭐", callback_data="buy_random_number_en")
        btn_channel = types.InlineKeyboardButton("📢 X9 Channel", url=CHANNEL_URL)
        btn_lang = types.InlineKeyboardButton("🌐 تغيير إلى العربية", callback_data="main_menu")
        markup.add(btn_buy, btn_channel, btn_lang)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"Welcome to X9 Store 🌐\n\n• Get USA numbers using Telegram Stars ⭐\n• Instant and secure purchase\n\n🆔 ID: `{user_id}`\n\nChoose from the menu 👇", reply_markup=markup, parse_mode="Markdown")

    elif call.data == "buy_random_number_en":
        available_numbers = [num_id for num_id, data in NUMBERS_STORE.items() if not data["sold"]]
        
        if not available_numbers:
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton("📢 X9 Channel", url=CHANNEL_URL))
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="lang_en"))
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Sorry, no USA numbers available right now in X9 🔴", reply_markup=markup, parse_mode="Markdown")
            return

        chosen_num_id = random.choice(available_numbers)

        try:
            prices = [types.LabeledPrice(label=f"USA Number #{chosen_num_id}", amount=44)]
            bot.send_invoice(
                chat_id=call.message.chat.id,
                title=f"🇺🇸 Buy USA Number - X9 Store",
                description="Random USA number for Telegram + private session with instant OTP.",
                invoice_payload=f"buy_usa_number_{chosen_num_id}",
                provider_token="",
                currency="XTR",
                prices=prices,
                start_parameter=f"buy-number-{chosen_num_id}"
            )
        except Exception as e:
            bot.answer_callback_query(call.id, text=f"Error: {str(e)}", show_alert=True)

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    payload = pre_checkout_query.invoice_payload
    num_id = payload.split("_")[-1]
    data = NUMBERS_STORE.get(num_id)
    
    if not data or data["sold"]:
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False, error_message="عذراً، هذا الرقم تم بيعه للتو لشخص آخر!")
    else:
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload
    num_id = payload.split("_")[-1]
    
    data = NUMBERS_STORE.get(num_id)
    if not data:
        return

    data["sold"] = True
    data["buyer_id"] = user_id
    
    reply_text = (
        f"🇺🇸 ✅ تم دفع 44 نجمة بنجاح عبر **متجر X9** واستلام رقم أمريكي بنجاح!\n\n"
        f"• تم إزالة الرقم من المتجر العام ليبقى خاصاً بك وحدك.\n\n"
        f"⚠️ **تنبيه هــــــــام جداً:**\n"
        f"• بمجرد استلامك للرقم، **تحمل المسؤولية كاملة**.\n"
        f"• ممنوع نهائياً عمل (تسجيل خروج / Logout) من الحساب، وفي حال خرجت أو فقدت الحساب **لا يوجد أي تعويض نهائياً** من قِبل متجر X9!\n\n"
        f"• الآن اضغط على زر **طلب الكود** أدناه لمعرفة كود التحقق (OTP)."
    )
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_get_code = types.InlineKeyboardButton("🔄 - طلب كود (تحديث)", callback_data=f"get_otp_{num_id}")
    markup.add(btn_get_code)
    
    bot.send_message(message.chat.id, reply_text, reply_markup=markup, parse_mode="Markdown")

def fetch_otp_on_demand(session_str, api_id, api_hash):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def main():
            if not session_str:
                return "خطأ: لم يتم ضبط السيشن بشكل صحيح ❌"
                
            client = TelegramClient(StringSession(session_str), api_id, api_hash)
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
    print("Starting X9 Bot with @VPP8P Channel and Random USA Numbers...")
    bot.remove_webhook()
    bot.infinity_polling()
import os
import re
import random
import asyncio
from telebot import types
import telebot
from telethon import TelegramClient
from telethon.sessions import StringSession

# إعدادات البوت الأساسية
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8526493972:AAEVb5f6rIcPCqMu1wVvEKop3QXvSih9YaE")
bot = telebot.TeleBot(BOT_TOKEN)

# رابط قناتك الرسمية على تليجرام
CHANNEL_URL = "https://t.me/VPP8P"

# ================= جدول الأرقام المتاحة (رقمين بسعر 44 نجمة حقيقية لكل رقم) =================
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

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_buy = types.InlineKeyboardButton("🇺🇸 🛒 شراء رقم أمريكي فوري (عشوائي) - 44 ⭐", callback_data="buy_random_number")
    btn_channel = types.InlineKeyboardButton("📢 قناة المتجر (X9)", url=CHANNEL_URL)
    btn_lang = types.InlineKeyboardButton("🌐 Change to English", callback_data="lang_en")
    markup.add(btn_buy, btn_channel, btn_lang)
    
    welcome_text = (
        "👋 أهلاً بك عزيزي في **متجر X9** للأرقام المميزة 🌐!\n\n"
        "• احصل على أرقام أمريكية مميزة ومفعلة لجميع الاستخدامات.\n"
        "• الشراء فوري وعشوائي وسريع عبر **نجوم تليجرام (Stars ⭐)**.\n"
        "• إمكانية طلب كود التحقق (OTP) بشكل فوري وبكل سهولة بعد الشراء.\n\n"
        f"🆔 معرفك الشخصي: `{user_id}`\n\n"
        "اختر ما يناسبك من القائمة 👇"
    )
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id

    if call.data == "buy_random_number":
        available_numbers = [num_id for num_id, data in NUMBERS_STORE.items() if not data["sold"]]
        
        if not available_numbers:
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton("📢 قناة المتجر (X9)", url=CHANNEL_URL))
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"))
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="عذراً، نفدت جميع الأرقام الأمريكية من متجر X9 حالياً 🔴", reply_markup=markup, parse_mode="Markdown")
            return

        chosen_num_id = random.choice(available_numbers)

        try:
            prices = [types.LabeledPrice(label=f"USA Number #{chosen_num_id}", amount=44)]
            bot.send_invoice(
                chat_id=call.message.chat.id,
                title=f"🇺🇸 شراء رقم أمريكي مميز - متجر X9",
                description="رقم أمريكي لاستخدام تليجرام (اختيار عشوائي) + جلسة خاصة بك وحدك مع إمكانية طلب الكود فوري.",
                invoice_payload=f"buy_usa_number_{chosen_num_id}",
                provider_token="",  # فارغ لنجوم تليجرام (XTR)
                currency="XTR",     # عملة نجوم تليجرام
                prices=prices,
                start_parameter=f"buy-number-{chosen_num_id}"
            )
        except Exception as e:
            bot.answer_callback_query(call.id, text=f"خطأ في إنشاء الفاتورة: {str(e)}", show_alert=True)

    elif call.data == "main_menu":
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_buy = types.InlineKeyboardButton("🇺🇸 🛒 شراء رقم أمريكي فوري (عشوائي) - 44 ⭐", callback_data="buy_random_number")
        btn_channel = types.InlineKeyboardButton("📢 قناة المتجر (X9)", url=CHANNEL_URL)
        btn_lang = types.InlineKeyboardButton("🌐 Change to English", callback_data="lang_en")
        markup.add(btn_buy, btn_channel, btn_lang)
        
        welcome_text = (
            "👋 أهلاً بك عزيزي في **متجر X9** للأرقام المميزة 🌐!\n\n"
            "• احصل على أرقام أمريكية مميزة ومفعلة لجميع الاستخدامات.\n"
            "• الشراء فوري وعشوائي وسريع عبر **نجوم تليجرام (Stars ⭐)**.\n"
            "• إمكانية طلب كود التحقق (OTP) بشكل فوري وبكل سهولة بعد الشراء.\n\n"
            f"🆔 معرفك الشخصي: `{user_id}`\n\n"
            "اختر ما يناسبك من القائمة 👇"
        )
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=welcome_text, reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("get_otp_"):
        num_id = call.data.split("_")[2]
        data = NUMBERS_STORE.get(num_id)
        
        if not data or data["buyer_id"] != user_id:
            bot.answer_callback_query(call.id, text="هذا الرقم ليس ملكاً لك!", show_alert=True)
            return

        code_result = fetch_otp_on_demand(data["session"], data["api_id"], data["api_hash"])
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_get_code = types.InlineKeyboardButton("🔄 - طلب كود (تحديث)", callback_data=f"get_otp_{num_id}")
        markup.add(btn_get_code)
        
        try:
            bot.edit_message_text(
                chat_id=call.message.chat.id, 
                message_id=call.message.message_id, 
                text=(
                    f"📥 **متجر X9** - نتيجة جلب الكود\n\n"
                    f"• كود التحقق / الرسالة : `{code_result}`\n\n"
                    f"⚠️ **تنبيه هام جداً:**\n"
                    f"• إياك ثم إياك عمل (تسجيل خروج / Logout) من الحساب داخل تطبيق تليجرام!\n"
                    f"• في حال قمت بتسجيل الخروج أو فقدان الحساب، **لا يوجد تعويض نهائياً** ولا يتحمل متجر X9 أي مسؤولية بعد استلام الرقم.\n\n"
                    f"*(قم بإدخال الكود، واضغط على زر التحديث بالأسفل لجلب أي كود جديد)*"
                ), 
                reply_markup=markup, 
                parse_mode="Markdown"
            )
        except Exception:
            bot.answer_callback_query(call.id, text=f"الكود الحالي: {code_result}")

    elif call.data == "lang_en":
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_buy = types.InlineKeyboardButton("🇺🇸 🛒 Buy USA Number (Random) - 44 ⭐", callback_data="buy_random_number_en")
        btn_channel = types.InlineKeyboardButton("📢 X9 Channel", url=CHANNEL_URL)
        btn_lang = types.InlineKeyboardButton("🌐 تغيير إلى العربية", callback_data="main_menu")
        markup.add(btn_buy, btn_channel, btn_lang)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"Welcome to X9 Store 🌐\n\n• Get USA numbers using Telegram Stars ⭐\n• Instant and secure purchase\n\n🆔 ID: `{user_id}`\n\nChoose from the menu 👇", reply_markup=markup, parse_mode="Markdown")

    elif call.data == "buy_random_number_en":
        available_numbers = [num_id for num_id, data in NUMBERS_STORE.items() if not data["sold"]]
        
        if not available_numbers:
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton("📢 X9 Channel", url=CHANNEL_URL))
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="lang_en"))
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Sorry, no USA numbers available right now in X9 🔴", reply_markup=markup, parse_mode="Markdown")
            return

        chosen_num_id = random.choice(available_numbers)

        try:
            prices = [types.LabeledPrice(label=f"USA Number #{chosen_num_id}", amount=44)]
            bot.send_invoice(
                chat_id=call.message.chat.id,
                title=f"🇺🇸 Buy USA Number - X9 Store",
                description="Random USA number for Telegram + private session with instant OTP.",
                invoice_payload=f"buy_usa_number_{chosen_num_id}",
                provider_token="",
                currency="XTR",
                prices=prices,
                start_parameter=f"buy-number-{chosen_num_id}"
            )
        except Exception as e:
            bot.answer_callback_query(call.id, text=f"Error: {str(e)}", show_alert=True)

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    payload = pre_checkout_query.invoice_payload
    num_id = payload.split("_")[-1]
    data = NUMBERS_STORE.get(num_id)
    
    if not data or data["sold"]:
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False, error_message="عذراً، هذا الرقم تم بيعه للتو لشخص آخر!")
    else:
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload
    num_id = payload.split("_")[-1]
    
    data = NUMBERS_STORE.get(num_id)
    if not data:
        return

    data["sold"] = True
    data["buyer_id"] = user_id
    
    reply_text = (
        f"🇺🇸 ✅ تم دفع 44 نجمة بنجاح عبر **متجر X9** واستلام رقم أمريكي بنجاح!\n\n"
        f"• تم إزالة الرقم من المتجر العام ليبقى خاصاً بك وحدك.\n\n"
        f"⚠️ **تنبيه هــــــــام جداً:**\n"
        f"• بمجرد استلامك للرقم، **تحمل المسؤولية كاملة**.\n"
        f"• ممنوع نهائياً عمل (تسجيل خروج / Logout) من الحساب، وفي حال خرجت أو فقدت الحساب **لا يوجد أي تعويض نهائياً** من قِبل متجر X9!\n\n"
        f"• الآن اضغط على زر **طلب الكود** أدناه لمعرفة كود التحقق (OTP)."
    )
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_get_code = types.InlineKeyboardButton("🔄 - طلب كود (تحديث)", callback_data=f"get_otp_{num_id}")
    markup.add(btn_get_code)
    
    bot.send_message(message.chat.id, reply_text, reply_markup=markup, parse_mode="Markdown")

def fetch_otp_on_demand(session_str, api_id, api_hash):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def main():
            if not session_str:
                return "خطأ: لم يتم ضبط السيشن بشكل صحيح ❌"
                
            client = TelegramClient(StringSession(session_str), api_id, api_hash)
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
    print("Starting X9 Bot with @VPP8P Channel and Random USA Numbers...")
    bot.remove_webhook()
    bot.infinity_polling()
