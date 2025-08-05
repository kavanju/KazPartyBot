import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from keep_alive import keep_alive
from dotenv import load_dotenv
import datetime

load_dotenv()

TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
KASPI_NAME = os.getenv("KASPI_NAME")
MOBILE_PAY_URL = os.getenv("MOBILE_PAY_URL")

logging.basicConfig(level=logging.INFO)

USERS = {}
FREE_TRIAL_USED = set()


def get_language_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["🇷🇺 Русский", "🇰🇿 Қазақша", "🇬🇧 English"]
        ],
        resize_keyboard=True
    )


def get_main_menu(lang="🇷🇺 Русский"):
    if "Қ" in lang:
        return ReplyKeyboardMarkup(
            [["Іздеу", "Сақталған орындар"]], resize_keyboard=True
        )
    elif "En" in lang or "🇬🇧" in lang:
        return ReplyKeyboardMarkup(
            [["Search", "Saved places"]], resize_keyboard=True
        )
    else:
        return ReplyKeyboardMarkup(
            [["Поиск", "Сохранённые места"]], resize_keyboard=True
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    await update.message.reply_text(
        "Выберите язык / Тілді таңдаңыз / Choose language:",
        reply_markup=get_language_keyboard()
    )


async def handle_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = update.message.text

    USERS[user_id] = {"lang": lang, "access_until": None, "saved": []}

    await update.message.reply_text(
        "Добро пожаловать! Напишите, куда хотите сходить (например: тихий бар с живой музыкой в Берлине)." if "🇷🇺" in lang else
        "Қош келдіңіз! Қайда барғыңыз келетінін жазыңыз (мысалы: Алматыда тыныш кафе)." if "🇰🇿" in lang else
        "Welcome! Tell me where you'd like to go (e.g., chill bar with live music in Berlin).",
        reply_markup=get_main_menu(lang)
    )


async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in USERS:
        await update.message.reply_text("Сначала введите /start.")
        return

    user = USERS[user_id]
    lang = user.get("lang", "🇷🇺")

    now = datetime.datetime.utcnow()
    access_until = user.get("access_until")

    if access_until and now < access_until:
        await update.message.reply_text("🔍 Ищу заведения по вашему описанию...")
        # Здесь должен быть реальный ИИ-поиск + бесплатные API
        await update.message.reply_text("✅ Пример найденного места: Бар 'Berlin Lounge' — средний чек 15€, работает до 2:00 ночи.")
        user["saved"].append("Berlin Lounge")
    elif user_id not in FREE_TRIAL_USED:
        FREE_TRIAL_USED.add(user_id)
        await update.message.reply_text(
            "🎁 Пробный запрос активирован!\n\n🔍 Ищу заведения..."
        )
        await update.message.reply_text("✅ Пример места: Клуб 'Astana Night' — музыка 90х, вход свободный.")
        user["saved"].append("Astana Night")
    else:
        await update.message.reply_text(
            f"🔒 Ваш доступ закончился.\n\nОплатите 400₸ (48ч): {MOBILE_PAY_URL}\n\n"
            "После оплаты пришлите чек (фото)."
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_path = f"check_{user_id}.jpg"
    await file.download_to_drive(file_path)

    # Имитация распознавания чека
    fake_kaspi_name = KASPI_NAME
    fake_amount = "400"

    # Симулируем успешную проверку
    now = datetime.datetime.utcnow()
    USERS[user_id]["access_until"] = now + datetime.timedelta(hours=48)

    await update.message.reply_text("✅ Оплата подтверждена! Доступ на 48 часов активирован.")


async def show_saved_places(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    saved = USERS.get(user_id, {}).get("saved", [])
    if not saved:
        await update.message.reply_text("📂 Нет сохранённых мест.")
    else:
        await update.message.reply_text("📌 Сохранённые места:\n" + "\n".join(saved))


def main():
    keep_alive()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Regex("^(Поиск|Іздеу|Search)$"), process_message))
    app.add_handler(MessageHandler(filters.Regex("^(Сохранённые места|Сақталған орындар|Saved places)$"), show_saved_places))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_language))

    app.run_polling()


if __name__ == "__main__":
    main()
