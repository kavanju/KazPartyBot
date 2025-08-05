import os
import logging
import asyncio
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from duckduckgo_search import DDGS
from dotenv import load_dotenv
import pytesseract
from PIL import Image
import speech_recognition as sr
from pydub import AudioSegment

# Load .env
load_dotenv()
TOKEN = os.getenv("TOKEN")
KASPI_NAME = os.getenv("KASPI_NAME", "")
OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Доступ (1 бесплатный запрос)
user_access = {}

def has_access(user_id):
    if user_id in user_access:
        return user_access[user_id] > asyncio.get_event_loop().time()
    return False

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[KeyboardButton("🎤 Голосом"), KeyboardButton("📸 Отправить чек")]]
    await update.message.reply_text("Привет! Я помогу найти заведение. Опиши, куда хочешь пойти:",
                                    reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

# Обработка текста
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not has_access(user_id):
        await update.message.reply_text("🔒 У вас нет доступа. 1 бесплатный запрос. Потом отправьте Kaspi чек.")
        user_access[user_id] = asyncio.get_event_loop().time() + 60  # 1 минута доступа
    query = update.message.text
    with DDGS() as ddgs:
        results = list(ddgs.text(query + " site:2gis.kz", max_results=3))
    for r in results:
        await update.message.reply_text(f"🏙️ {r['title']}\n📍 {r['body']}\n🔗 {r['href']}")

# Фото чека
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = await update.message.photo[-1].get_file()
    path = f"/tmp/{update.message.from_user.id}.jpg"
    await photo.download_to_drive(path)
    text = pytesseract.image_to_string(Image.open(path))
    if KASPI_NAME in text and ("400" in text or "200" in text):
        user_access[update.message.from_user.id] = asyncio.get_event_loop().time() + 172800
        await update.message.reply_text("✅ Доступ активирован на 48 часов")
    else:
        await update.message.reply_text("❌ Не удалось подтвердить оплату")

# Голос
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = await update.message.voice.get_file()
    path = f"/tmp/{update.message.from_user.id}.ogg"
    await voice.download_to_drive(path)
    try:
        wav_path = path.replace(".ogg", ".wav")
        AudioSegment.from_ogg(path).export(wav_path, format="wav")
        r = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = r.record(source)
            text = r.recognize_google(audio, language="ru-RU")
            update.message.text = text
            await handle_text(update, context)
    except Exception as e:
        await update.message.reply_text("❌ Ошибка распознавания речи")

# Основной запуск
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.run_polling()
