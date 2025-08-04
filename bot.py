import os
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

# Загрузка переменных из .env
load_dotenv()

TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))
KASPI_NAME = os.getenv("KASPI_NAME", "Имя Kaspi")

# Словари доступа
user_access = {}
free_trial_used = set()

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask-сервер для Render
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "KazPartyBot is alive!"

def run_flask():
    flask_app.run(host="0.0.0.0", port=8080)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == OWNER_ID:
        user_access[user_id] = True
        await update.message.reply_text("👑 Привет, админ! Доступ активирован навсегда.")
        return

    if user_access.get(user_id):
        await update.message.reply_text("✅ У вас уже есть доступ.")
    elif user_id not in free_trial_used:
        free_trial_used.add(user_id)
        user_access[user_id] = True
        await update.message.reply_text("🎁 Бесплатный доступ активирован! Напишите запрос.")
    else:
        await update.message.reply_text(
            "❌ У вас нет доступа.\n\n💸 Оплата за 48 часов:\n"
            "• 400₸ Kaspi Pay\n• $2 PayPal\n\n"
            "📎 Kaspi: https://pay.kaspi.kz/pay/sav8emzy\n"
            "После оплаты пришлите чек сюда."
        )

# Обработка фото чека
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not update.message.photo:
        return

    await update.message.reply_text("🕵️ Проверяю чек...")

    # Пока просто активируем доступ вручную
    user_access[user_id] = True
    await update.message.reply_text("✅ Доступ активирован. Пишите, что ищем!")

# Обработка текста
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_access.get(user_id) and user_id != OWNER_ID:
        await update.message.reply_text("❌ Нет доступа. Нажмите /start")
        return

    await update.message.reply_text(f"🤖 Поиск по запросу:\n«{update.message.text}»...")

# Запуск Flask и Telegram бота
def main():
    # Flask в отдельном потоке
    Thread(target=run_flask).start()

    import asyncio
    async def run_bot():
        application = Application.builder().token(TOKEN).post_init(lambda app: None).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        await application.updater.wait_until_shutdown()
        await application.stop()
        await application.shutdown()

    asyncio.run(run_bot())

if __name__ == "__main__":
    main()

