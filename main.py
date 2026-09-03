import os
import re
import asyncio
from telebot import types
import telebot
from telethon import TelegramClient
from telethon.sessions import StringSession

# إعدادات البوت الأساسية
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8526493972:AAEVb5f6rIcPCqMu1wVvEKop3QXvSih9YaE")
bot = telebot.TeleBot(BOT_TOKEN)

# ================= جدول الأرقام المتاحة (للاختبار المجاني) =================
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
# ==============================================================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_buy = types.InlineKeyboardButton("🛒 شراء أرقام بالنجوم ⭐ (تجريبي مجاني)", callback_data="buy_numbers")
    btn_lang = types.InlineKeyboardButton("🌐 Change to English", callback_data="lang_en")
    markup.add(btn_buy, btn_lang)
    bot.send_message(message.chat.id, f"بوت أرقام تليجرام المميزة (نسخة اختبارية)\n\n• احصل على أرقام مجاناً للتجربة ⭐\n\n🆔 ID: `{user_id}`\n\nاختر من القائمة 👇", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id

    if call.data == "buy_numbers":
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        available_count = 0
        for num_id, data in NUMBERS_STORE.items():
            if not data["sold"]:
                available_count += 1
                markup.add(types.InlineKeyboardButton(f"🇺🇸 رقم أمريكي ({num_id}) - 44 نجمة ⭐ (مجاني للاختبار)", callback_data=f"getnum_{num_id}"))
        
        if available_count == 0:
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="main_menu"))
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="عذراً، نفدت جميع الأرقام من المتجر حالياً 🔴", reply_markup=markup, parse_mode="Markdown")
            return

        btn_back = types.InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")
        markup.add(btn_back)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="اختر الرقم المناسب للاختبار 🌐", reply_markup=markup, parse_mode="Markdown")

    elif call.data == "main_menu":
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_buy = types.InlineKeyboardButton("🛒 شراء أرقام بالنجوم ⭐ (تجريبي مجاني)", callback_data="buy_numbers")
        btn_lang = types.InlineKeyboardButton("🌐 Change to English", callback_data="lang_en")
        markup.add(btn_buy, btn_lang)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"بوت أرقام تليجرام المميزة (نسخة اختبارية)\n\n• احصل على أرقام مجاناً للتجربة ⭐\n\n🆔 ID: `{user_id}`\n\nاختر من القائمة 👇", reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("getnum_"):
        num_id = call.data.split("_")[1]
        data = NUMBERS_STORE.get(num_id)
        
        if not data or data["sold"]:
            bot.answer_callback_query(call.id, text="عذراً، هذا الرقم تم بيعه مسبقاً!", show_alert=True)
            return

        markup = types.InlineKeyboardMarkup(row_width=1)
        # زر الشراء التجريبي (الفوري بدون دفع حقيقي)
        btn_pay = types.InlineKeyboardButton("⭐ تأكيد الشراء التجريبي (مجاني)", callback_data=f"pay_free_{num_id}")
        btn_back = types.InlineKeyboardButton("🔙 رجوع", callback_data="buy_numbers")
        markup.add(btn_pay, btn_back)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            text=f"شراء رقم أمريكي مميز #{num_id}\n\n💰 السعر: **44 نجمة ⭐ (مجاني للاختبار)**\n⚠️ تنبيه: هذه نسخة تجريبية لاخصم حقيقي فيها.", 
            reply_markup=markup, 
            parse_mode="Markdown"
        )

    elif call.data.startswith("pay_free_"):
        num_id = call.data.split("_")[2]
        data = NUMBERS_STORE.get(num_id)
        
        if not data or data["sold"]:
            bot.answer_callback_query(call.id, text="عذراً، تم بيع هذا الرقم لشخص آخر!", show_alert=True)
            return

        # حجز الرقم للمستخدم وحذفه من المتجر العام
        data["sold"] = True
        data["buyer_id"] = user_id
        
        reply_text = f"✅ تم استلام الرقم #{num_id} بنجاح (تجريبي مجاني)!\n\n• الرقم : `{data['phone']}`\n• وتم إزالة الرقم من المتجر العام ليبقى خاصاً بك وحدك.\n\n• حاول تسجيل الدخول بالرقم في تطبيق تليجرام\nثم اضغط على زر **طلب الكود** أدناه للاختبار"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_get_code = types.InlineKeyboardButton("🔄 - طلب كود (تحديث)", callback_data=f"get_otp_{num_id}")
        markup.add(btn_get_code)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            text=reply_text, 
            reply_markup=markup, 
            parse_mode="Markdown"
        )

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
                text=f"📥 نتيجة جلب الكود\n\n• الرقم : `{data['phone']}`\n• التفاصيل/الكود : `{code_result}`\n\n*(يمكنك الضغط على زر التحديث بالأسفل لجلب أي كود جديد في أي وقت)*", 
                reply_markup=markup, 
                parse_mode="Markdown"
            )
        except Exception:
            bot.answer_callback_query(call.id, text=f"الكود الحالي: {code_result}")

    elif call.data == "lang_en":
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_buy = types.InlineKeyboardButton("🛒 Buy Numbers (Free Test)", callback_data="buy_numbers_en")
        btn_lang = types.InlineKeyboardButton("🌐 تغيير إلى العربية", callback_data="main_menu")
        markup.add(btn_buy, btn_lang)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"Premium Telegram Numbers Bot (Test Version)\n\n🆔 ID: `{user_id}`\n\nChoose from the menu 👇", reply_markup=markup, parse_mode="Markdown")

    elif call.data == "buy_numbers_en":
        markup = types.InlineKeyboardMarkup(row_width=1)
        available_count = 0
        for num_id, data in NUMBERS_STORE.items():
            if not data["sold"]:
                available_count += 1
                markup.add(types.InlineKeyboardButton(f"🇺🇸 USA number ({num_id}) - Free Test", callback_data=f"getnum_{num_id}"))
        
        if available_count == 0:
            btn_back = types.InlineKeyboardButton("🔙 Back", callback_data="lang_en")
            markup.add(btn_back)
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Sorry, no numbers available right now 🔴", reply_markup=markup, parse_mode="Markdown")
            return

        btn_back = types.InlineKeyboardButton("🔙 Back", callback_data="lang_en")
        markup.add(btn_back)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Select Country 🌐", reply_markup=markup, parse_mode="Markdown")

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
    print("Starting bot in FREE TEST mode...")
    bot.remove_webhook()
    bot.infinity_polling()
