import os
import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from keep_alive import keep_alive
from dotenv import load_dotenv
import datetime

# Загрузка переменных окружения
load_dotenv()

TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
KASPI_NAME = os.getenv("KASPI_NAME")
KASPI_LINK = os.getenv("KASPI_LINK")
PAYPAL_EMAIL = os.getenv("PAYPAL_EMAIL")
PAYPAL_PRICE_USD = os.getenv("PAYPAL_PRICE_USD", "2")
ACCESS_DURATION_HOURS = int(os.getenv("ACCESS_DURATION_HOURS", "48"))

user_access = {}
free_used = set()

# Языки
LANGS = {
    'ru': {
        'welcome': "👋 Привет! Я помогу тебе найти, где отдохнуть: бары, клубы, караоке, рестораны и многое другое.",
        'free_used': "⚠️ Бесплатный запрос уже использован. Оплатите доступ:",
        'choose_lang': "Выберите язык / Тілді таңдаңыз / Choose language",
        'pay': "💳 Оплатите 400₸ Kaspi или $2 через PayPal, чтобы получить доступ на 48 часов:",
        'kaspi': "📲 Kaspi Pay:",
        'paypal': "🌍 PayPal:",
        'access_granted': "✅ Доступ активирован!",
        'send_request': "✍️ Опиши, куда хочешь пойти (например: 'где потанцевать в Астане с музыкой 2000-х')",
    },
    'kk': {
        'welcome': "👋 Сәлем! Мен сізге баруға болатын орындарды табуға көмектесемін: барлар, клубтар, караоке, мейрамханалар және т.б.",
        'free_used': "⚠️ Тегін сұраныс пайдаланылды. Қолжетімділікті сатып алыңыз:",
        'choose_lang': "Выберите язык / Тілді таңдаңыз / Choose language",
        'pay': "💳 400₸ Kaspi немесе $2 PayPal арқылы төлеңіз (48 сағатқа қолжетімділік):",
        'kaspi': "📲 Kaspi төлемі:",
        'paypal': "🌍 PayPal:",
        'access_granted': "✅ Қолжетімділік берілді!",
        'send_request': "✍️ Қайда барғыңыз келетінін жазыңыз (мысалы: 'Астанада би билейтін жер')",
    },
    'en': {
        'welcome': "👋 Hi! I’ll help you find places to relax: bars, clubs, karaoke, restaurants, and more.",
        'free_used': "⚠️ Free request used. Please pay for access:",
        'choose_lang': "Выберите язык / Тілді таңдаңыз / Choose language",
        'pay': "💳 Pay 400₸ via Kaspi or $2 via PayPal to get 48-hour access:",
        'kaspi': "📲 Kaspi Pay:",
        'paypal': "🌍 PayPal:",
        'access_granted': "✅ Access granted!",
        'send_request': "✍️ Describe where you want to go (e.g., 'Where to dance in Berlin with techno')",
    }
}

user_lang = {}

def get_lang_text(user_id, key):
    lang = user_lang.get(user_id, os.getenv("DEFAULT_LANG", "ru"))
    return LANGS.get(lang, LANGS["ru"])[key]

def check_access(user_id):
    if user_id in user_access:
        if datetime.datetime.now() < user_access[user_id]:
            return True
        else:
            del user_access[user_id]
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [KeyboardButton("Русский 🇷🇺"), KeyboardButton("Қазақша 🇰🇿"), KeyboardButton("English 🇬🇧")]
    ]
    await update.message.reply_text(get_lang_text(user.id, "choose_lang"),
                                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    # Выбор языка
    if text == "Русский 🇷🇺":
        user_lang[user.id] = "ru"
        await update.message.reply_text(LANGS["ru"]["welcome"] + "\n\n" + LANGS["ru"]["send_request"])
        return
    elif text == "Қазақша 🇰🇿":
        user_lang[user.id] = "kk"
        await update.message.reply_text(LANGS["kk"]["welcome"] + "\n\n" + LANGS["kk"]["send_request"])
        return
    elif text == "English 🇬🇧":
        user_lang[user.id] = "en"
        await update.message.reply_text(LANGS["en"]["welcome"] + "\n\n" + LANGS["en"]["send_request"])
        return

    # Проверка доступа
    if check_access(user.id):
        await update.message.reply_text("🤖 [Идёт подбор места… в реальности тут будет ИИ и фото, отзывы, карта...]")
        return

    if user.id not in free_used:
        free_used.add(user.id)
        await update.message.reply_text("🎁 Бесплатный пробный запрос принят! Следующий будет платный.")
        await update.message.reply_text("🤖 [Тестовый подбор места: например 'Бар в Алматы с живой музыкой']")
        return

    # Нет доступа
    lang_msg = get_lang_text(user.id, "free_used") + "\n\n" + \
               f"{get_lang_text(user.id, 'pay')}\n\n" + \
               f"{get_lang_text(user.id, 'kaspi')} {KASPI_LINK}\n👤 {KASPI_NAME}\n\n" + \
               f"{get_lang_text(user.id, 'paypal')} paypal.me/{PAYPAL_EMAIL} (${PAYPAL_PRICE_USD})"
    await update.message.reply_text(lang_msg)

async def access_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == OWNER_ID and context.args:
        try:
            target_id = int(context.args[0])
            user_access[target_id] = datetime.datetime.now() + datetime.timedelta(hours=ACCESS_DURATION_HOURS)
            await update.message.reply_text(f"✅ Доступ выдан пользователю {target_id}")
        except:
            await update.message.reply_text("❌ Ошибка выдачи доступа.")
    else:
        await update.message.reply_text("❌ Недостаточно прав.")

if __name__ == '__main__':
    keep_alive()
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("access", access_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    app.run_polling()
