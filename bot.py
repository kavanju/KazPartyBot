import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from keep_alive import keep_alive
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
KASPI_NAME = os.getenv("KASPI_NAME")
OWNER_ID = int(os.getenv("OWNER_ID"))

PAYMENT_LINK_KASPI = "https://pay.kaspi.kz/pay/sav8emzy"

# Приветствие
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я ИИ-помощник по отдыху.\n\n"
        "1 бесплатный запрос. Дальше — доступ за 400₸ / 48 часов.\n"
        f"Оплатить: {PAYMENT_LINK_KASPI}\n\n"
        "Напиши, куда хочешь сходить — я подберу варианты!"
    )

# Обработка текста запроса
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # Простая логика — позже заменим на ИИ и интернет-поиск
    if "выпить" in text.lower():
        await update.message.reply_text("🍷 Попробуй бар 'Cheers Bar' в центре. Атмосфера 🔥!")
    elif "поесть" in text.lower():
        await update.message.reply_text("🍽 Советую 'ГастроПапа' — вкусно и уютно.")
    else:
        await update.message.reply_text("🤖 Обрабатываю твой запрос... Подбор скоро будет совершеннее!")

# Команда /pay — показать оплату
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🔒 Доступ платный: 400₸ за 48 часов\n\nСсылка: {PAYMENT_LINK_KASPI}\nФИО получателя: {KASPI_NAME}")

# Главный запуск
def main():
    keep_alive()
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
