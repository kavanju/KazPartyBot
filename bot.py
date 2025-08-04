import os
import logging
from telegram import Update
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
from flask import Flask, request
from threading import Thread
from dotenv import load_dotenv
from duckduckgo_search import DDGS
import speech_recognition as sr
from pydub import AudioSegment
from io import BytesIO
from PIL import Image
import pytesseract

# Загрузка .env
load_dotenv()
TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))
KASPI_NAME = os.getenv("KASPI_NAME", "Имя Kaspi")

# Логи
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Доступ
user_access = {}
free_trial_used = set()
saved_places = {}

# Flask app
flask_app = Flask(__name__)
telegram_app = None  # будет позже присвоено


@flask_app.route('/')
def index():
    return 'KazPartyBot is running!'


@flask_app.route(f'/{TOKEN}', methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    telegram_app.update_queue.put(update)
    return "OK", 200

# Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    saved_places.setdefault(user_id, [])

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

# Распознавание чека
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo = update.message.photo[-1]
    file = await photo.get_file()
    img_bytes = await file.download_as_bytearray()
    img = Image.open(BytesIO(img_bytes))
    text = pytesseract.image_to_string(img, lang='rus')

    if KASPI_NAME.lower() in text.lower():
        user_access[user_id] = True
        await update.message.reply_text("✅ Чек подтверждён. Доступ активирован!")
    else:
        await update.message.reply_text("❌ Не удалось распознать имя. Попробуйте снова.")

# Голос
async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_access.get(user_id) and user_id != OWNER_ID:
        await update.message.reply_text("❌ Нет доступа. Нажмите /start")
        return

    voice = update.message.voice
    file = await voice.get_file()
    audio_bytes = await file.download_as_bytearray()
    audio = AudioSegment.from_ogg(BytesIO(audio_bytes))
    wav_io = BytesIO()
    audio.export(wav_io, format="wav")
    recognizer = sr.Recognizer()

    with sr.AudioFile(wav_io) as source:
        data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(data, language="ru-RU")
            await update.message.reply_text(f"🗣️ Вы сказали: {text}")
            await search_places(update, text)
        except sr.UnknownValueError:
            await update.message.reply_text("❌ Не удалось распознать голос.")

# Сохранённые
async def my_places(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    places = saved_places.get(user_id, [])
    if not places:
        await update.message.reply_text("📂 У вас пока нет сохранённых мест.")
        return

    text = "\n\n".join(places)
    await update.message.reply_text(f"📚 Ваши сохранённые места:\n\n{text}")

# Поиск
async def search_places(update: Update, query: str):
    user_id = update.effective_user.id
    await update.message.reply_text("🔍 Ищу подходящие места...")

    results = DDGS().text(query + " site:2gis.kz", max_results=5)
    msg = ""
    for i, r in enumerate(results, 1):
        title = r.get("title")
        href = r.get("href")
        if title and href:
            msg += f"{i}. [{title}]({href})\n"
            saved_places[user_id].append(f"{title} — {href}")

    if msg:
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        await update.message.reply_text("😕 Ничего не найдено.")

# Текст
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if text == "📚 Мои сохранённые места":
        await my_places(update, context)
        return

    if not user_access.get(user_id) and user_id != OWNER_ID:
        await update.message.reply_text("❌ Нет доступа. Нажмите /start")
        return

    await search_places(update, text)

# Запуск
async def main():
    global telegram_app
    telegram_app = ApplicationBuilder().token(TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    telegram_app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    await telegram_app.bot.set_webhook(url=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}")
    telegram_app.run_webhook(
        listen="0.0.0.0",
        port=8080,
        webhook_path=_
