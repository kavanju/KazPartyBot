import os
import logging
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import speech_recognition as sr
from pydub import AudioSegment
from duckduckgo_search import DDGS
import aiohttp

# === Загрузка конфигурации ===
load_dotenv()
TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))

# === Логирование ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# === Хранилище доступа ===
user_access = {}

# === Проверка доступа ===
def has_access(user_id: int) -> bool:
    if user_id in user_access:
        return datetime.now() < user_access[user_id]
    return False

# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я помогу найти лучшие места для отдыха, еды и веселья в твоём городе.\n\n"
        "🔓 Чтобы начать, введи /pay и получи доступ на 48 часов."
    )

# === Оплата /pay ===
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    keyboard = [[InlineKeyboardButton("💳 Оплатить 400₸ через Kaspi", url="https://pay.kaspi.kz/pay/sav8emzy")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🔒 Чтобы получить доступ к боту на 48 часов, оплатите 400₸ по кнопке ниже.\n\n"
        "❗ После оплаты, пожалуйста, напишите 'Оплатил', чтобы мы могли быстрее активировать доступ.\n"
        "⏳ Или просто подождите — доступ будет выдан через 1 минуту автоматически.",
        reply_markup=reply_markup
    )

    await asyncio.sleep(60)
    if not has_access(user_id):
        user_access[user_id] = datetime.now() + timedelta(hours=48)
        await context.bot.send_message(chat_id=user_id, text="✅ Спасибо! Доступ активирован на 48 часов 🎉")

# === Голосовые сообщения ===
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not has_access(user_id):
        await update.message.reply_text("🚫 Доступ ограничен. Введите /pay для активации.")
        return

    voice = await update.message.voice.get_file()
    ogg_path = f"voice_{user_id}.ogg"
    wav_path = f"voice_{user_id}.wav"
    await voice.download_to_drive(ogg_path)

    sound = AudioSegment.from_ogg(ogg_path)
    sound.export(wav_path, format="wav")

    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio, language="ru-RU")
        await update.message.reply_text(f"🗣️ Вы сказали: {text}")
        await search_places(text, update, context)
    except Exception as e:
        await update.message.reply_text("❌ Не удалось распознать речь. Попробуйте снова.")

    os.remove(ogg_path)
    os.remove(wav_path)

# === Поиск заведений через DuckDuckGo ===
async def search_places(query: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not has_access(user_id):
        await update.message.reply_text("🚫 У вас нет доступа. Введите /pay.")
        return

    await update.message.reply_text("🔍 Ищу подходящие места...")
    results = []
    async with aiohttp.ClientSession() as session:
        async with DDGS(session=session) as ddgs:
            async for r in ddgs.text(query + " заведения Казахстан", region="kz-ru", safesearch="off", max_results=3):
                results.append(r)

    if results:
        for res in results:
            msg = f"🏙️ {res['title']}\n{res['href']}\n\n{res.get('body', '')}"
            await update.message.reply_text(msg)
    else:
        await update.message.reply_text("😔 Не удалось найти подходящие заведения.")

# === Обработка текста ===
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text.lower() in ["оплатил", "я оплатил", "готово"]:
        user_access[user_id] = datetime.now() + timedelta(hours=48)
        await update.message.reply_text("✅ Спасибо! Доступ активирован на 48 часов.")
    else:
        await search_places(text, update, context)

# === Основной запуск ===
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 Бот запущен")
    app.run_polling()
