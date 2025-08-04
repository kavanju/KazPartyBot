import os
import logging
import requests
import speech_recognition as sr
from pydub import AudioSegment
from dotenv import load_dotenv
from flask import Flask, request
from threading import Thread
from io import BytesIO
from PIL import Image
import pytesseract

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

load_dotenv()

# Настройки
TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
KASPI_NAME = os.getenv("KASPI_NAME", "").lower()
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

user_access = {}
free_trial_used = set()

# --- Flask для Webhook ---
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "ok"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# --- Команды и сообщения ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    access = user_access.get(user_id, False)
    if not access and user_id not in free_trial_used:
        free_trial_used.add(user_id)
        user_access[user_id] = True
        await update.message.reply_text("Добро пожаловать! У вас 1 бесплатный запрос.")
    elif not access:
        await update.message.reply_text("У вас нет доступа. Оплатите 400₸ по ссылке: https://pay.kaspi.kz/pay/sav8emzy")
    else:
        await update.message.reply_text("Вы уже активировали доступ. Введите ваш запрос или отправьте фото/голос.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_access.get(user_id, False):
        await update.message.reply_text("У вас нет доступа. Оплатите по ссылке: https://pay.kaspi.kz/pay/sav8emzy")
        return

    query = update.message.text
    # AI-запрос через DuckDuckGo
    from duckduckgo_search import DDGS
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=3):
            results.append(f"{r['title']}\n{r['href']}")

    reply = "\n\n".join(results) if results else "Ничего не найдено 😕"
    await update.message.reply_text(reply)

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not update.message.photo:
        return

    file = await update.message.photo[-1].get_file()
    image_stream = BytesIO()
    await file.download_to_memory(out=image_stream)
    image_stream.seek(0)

    img = Image.open(image_stream)
    text = pytesseract.image_to_string(img).lower()

    logging.info(f"OCR: {text}")
    if KASPI_NAME.lower() in text and "тг" in text or "тг." in text:
        user_access[user_id] = True
        await update.message.reply_text("✅ Оплата подтверждена! Доступ активирован на 48 часов.")
    else:
        await update.message.reply_text("❌ Не удалось распознать чек. Убедитесь, что имя и сумма видны.")

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_access.get(user_id, False):
        await update.message.reply_text("Сначала оплатите доступ: https://pay.kaspi.kz/pay/sav8emzy")
        return

    voice = await update.message.voice.get_file()
    audio = BytesIO()
    await voice.download_to_memory(out=audio)
    audio.seek(0)

    # Конвертация .ogg -> .wav
    ogg = AudioSegment.from_ogg(audio)
    wav_io = BytesIO()
    ogg.export(wav_io, format="wav")
    wav_io.seek(0)

    # Распознавание речи
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_io) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data, language="ru-RU")
            await update.message.reply_text(f"Вы сказали: {text}")
            update.message.text = text
            await handle_text(update, context)
        except Exception as e:
            logging.error(e)
            await update.message.reply_text("❌ Не удалось распознать голос.")

# --- Запуск ---
application = ApplicationBuilder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
application.add_handler(MessageHandler(filters.PHOTO, photo_handler))
application.add_handler(MessageHandler(filters.VOICE, voice_handler))

import asyncio

    def run_flask():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    flask_app.run(host="0.0.0.0", port=8080)

def main():
    # Запуск Flask в отдельном потоке
    Thread(target=run_flask).start()

    # Запуск Telegram-бота асинхронно
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()


