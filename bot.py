import os
from flask import Flask
from threading import Thread
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))

# Flask-приложение
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "KazPartyBot is running!"

# Telegram Bot Logic
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! Я KazPartyBot. Напиши, куда хочешь сходить 🕺🍸"
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    await update.message.reply_text(f"Ты написал: {user_input}\nСкоро подберу тебе заведения!")

def run_telegram_bot():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

def run_flask_and_bot():
    # Запускаем телеграм-бота в отдельном потоке
    Thread(target=run_telegram_bot).start()
    # Запускаем Flask
    flask_app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    run_flask_and_bot()
