import os
from dotenv import load_dotenv
load_dotenv()

import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request
from threading import Thread

# === Настройки ===
TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))
KASPI_NAME = os.getenv("KASPI_NAME", "Имя владельца Kaspi")

user_access = {}
free_trial_used = set()

# === Логгирование ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Flask сервер для Render (чтобы бот не засыпал) ===
flask_app = Flask('')

@flask_app.route('/')
def home():
    return "KazPartyBot is running!"

def run_flask():
    flask_app.run(host="0.0.0.0", port=8080)

Thread(target=run_flask).start()

# === Команды ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == OWNER_ID:
        user_access[user_id] = True
        await update.message.reply_text("👑 Привет, админ! Доступ активирован навсегда.")
        return

    if user_access.get(user_id):
        await update.message.reply_text("✅ У вас активен доступ. Можете писать запрос.")
    elif user_id not in free_trial_used:
        free_trial_used.add(user_id)
        user_access[user_id] = True
        await update.message.reply_text("🎁 Бесплатный пробный запрос активирован! Напишите, куда хотите пойти.")
    else:
        await update.message.reply_text(
            "❌ У вас нет доступа.\n\n💸 Стоимость доступа на 48 часов:\n"
            "• 400₸ (Kaspi)\n• $2 (PayPal)\n\n"
            "📎 Kaspi Pay: https://pay.kaspi.kz/pay/sav8emzy\n"
            "После оплаты отправьте скрин чека боту для активации."
        )

# === Обработка фото чеков ===
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == OWNER_ID:
        user_access[user_id] = True
        await update.message.reply_text("✅ Админ — доступ всегда есть.")
        return

    if not update.message.photo:
        return

    await update.message.reply_text("🕵️ Проверяю чек...")
    # Здесь будет ИИ-распознавание чека (Kaspi)
    # Пока эмуляция
    user_access[user_id] = True
    await update.message.reply_text("✅ Доступ активирован на 48 часов. Пишите, что хотите найти.")

# === ИИ-подбор заведений (заглушка) ===
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_access.get(user_id) and user_id != OWNER_ID:
        await update.message.reply_text("❌ У вас нет доступа. Нажмите /start")
        return

    user_text = update.message.text
    await update.message.reply_text(f"🤖 Ищу заведения по запросу:\n«{user_text}»...\n\n(Эта часть скоро будет работать через ИИ!)")

# === Главная ===
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    application.run_polling()

if __name__ == "__main__":
    main()

