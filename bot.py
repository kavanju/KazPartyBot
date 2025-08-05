import os
import logging
import asyncio
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from duckduckgo_search import DDGS
from dotenv import load_dotenv
import pytesseract
from PIL import Image
import speech_recognition as sr
from pydub import AudioSegment

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TOKEN")
KASPI_NAME = os.getenv("KASPI_NAME", "").lower()
OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Access management
user_access = {}

def has_access(user_id):
    if user_id in user_access:
        return user_access[user_id] > asyncio.get_event_loop().time()
    return False

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[KeyboardButton("🎤 Голосом"), KeyboardButton("📸 Отправить чек")]]
    await update.message.reply_text(
        "Привет! Я помогу найти заведение. Напиши или скажи, куда хочешь пойти:",
        reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
    )

# Text handler
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not has_access(user_id):
        await update.message.reply_text("🔒 У вас нет доступа. Отправьте Kaspi чек для разблокировки.")
        return

    query = update.message.text
    with DDGS() as ddgs:
        results = list(ddgs.text(query + " site:2gis.kz", max_results=3))
    if not results:
        await update.message.reply_text("Ничего не найдено 😕")
        return
    for r in results:
        await update.message.reply_text(f"🏙️ {r['title']}\n📍 {r['body']}\n🔗 {r['href']}")

# Photo (check) handler
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    photo = await update.message.photo[-1].get_file()
    path = f"/tmp/{user_id}.jpg"
    await photo.download_to_drive(path)

    text = pytesseract.image_to_string(Image.open(path)).lower()
    if KASPI_NAME in text and any(sum in text for sum in ["400", "200", "300"]):
        user_access[user_id] = asyncio.get_event_loop().time() + 172800  # 48h
        await update.message.reply_text("✅ Оплата подтверждена. Доступ открыт на 48 часов.")
    else:
        await update.message.reply_text("❌ Не удалось подтвердить оплату. Попробуйте снова.")

# Voice handler
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not has_access(user_id):
        await update.message.reply_text("🔒 У вас нет доступа. Отправьте Kaspi чек для разблокировки.")
        return

    voice = await update.message.voice.get_file()
    ogg_path = f"/tmp/{user_id}.ogg"
    wav_path = f"/tmp/{user_id}.wav"
    await voice.download_to_drive(ogg_path)

    try:
        AudioSegment.from_ogg(ogg_path).export(wav_path, format="wav")
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio, language="ru-RU")
        update.message.text = text
        await handle_text(update, context)
    except Exception as e:
        logger.error(f"Speech recognition failed: {e}")
        await update.message.reply_text("❌ Не удалось распознать голосовое сообщение.")

# Entry point
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.run_polling()
