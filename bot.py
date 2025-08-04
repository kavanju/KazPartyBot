import os
import logging
import sqlite3
import requests
import asyncio
import pytesseract
import speech_recognition as sr
from PIL import Image
from flask import Flask
from threading import Thread
from telegram import (Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, InputFile)
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler)
from duckduckgo_search import DDGS
from dotenv import load_dotenv

# Load env vars
load_dotenv()
TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))
KASPI_NAME = os.getenv("KASPI_NAME", "")
PAYPAL_LINK = os.getenv("PAYPAL_LINK", "")

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask для рендера
flask_app = Flask(__name__)
@flask_app.route('/')
def home():
    return 'Bot is running!'

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)

# DB init
conn = sqlite3.connect("data.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, access_until INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS places (user_id INTEGER, name TEXT, address TEXT, photo_url TEXT)''')
conn.commit()

# Проверка доступа
def has_access(user_id):
    c.execute("SELECT access_until FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    if row:
        return row[0] > int(asyncio.time.time())
    return False

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[KeyboardButton("🎤 Голосом"), KeyboardButton("📸 Отправить чек")],
          [KeyboardButton("📚 Мои сохранённые места")]]
    await update.message.reply_text("Привет! Я помогу найти заведение. Опиши, куда хочешь пойти:",
                                    reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

# Обработка текста запроса
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not has_access(user_id):
        await update.message.reply_text("🔒 У вас нет доступа. 1 бесплатный запрос. Потом оплата 400₸/48ч. Отправьте чек Kaspi или оплатите: https://pay.kaspi.kz/pay/sav8emzy")
    query = update.message.text
    places = []
    with DDGS() as ddgs:
        for r in ddgs.text(query + " site:2gis.kz", max_results=3):
            places.append(r)
    for place in places:
        name = place['title']
        link = place['href']
        snippet = place['body']
        await update.message.reply_text(f"🏙️ {name}\n📍 {snippet}\n🔗 {link}")
        c.execute("INSERT INTO places (user_id, name, address, photo_url) VALUES (?, ?, ?, ?)",
                  (user_id, name, snippet, link))
    conn.commit()

# Обработка чеков (фото)
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = await update.message.photo[-1].get_file()
    path = f"/tmp/{update.message.from_user.id}.jpg"
    await photo.download_to_drive(path)
    text = pytesseract.image_to_string(Image.open(path))
    if KASPI_NAME in text and ("400" in text or "200" in text):
        c.execute("REPLACE INTO users (id, access_until) VALUES (?, ?)", (update.message.from_user.id, int(asyncio.time.time()) + 172800))
        conn.commit()
        await update.message.reply_text("✅ Доступ активирован на 48 часов")
    else:
        await update.message.reply_text("❌ Не удалось подтвердить оплату. Проверьте, чтобы на чеке было имя и сумма")

# Обработка голосовых сообщений
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = await update.message.voice.get_file()
    path = f"/tmp/{update.message.from_user.id}.ogg"
    await voice.download_to_drive(path)
    try:
        from pydub import AudioSegment
        AudioSegment.from_ogg(path).export(path.replace(".ogg", ".wav"), format="wav")
        recognizer = sr.Recognizer()
        with sr.AudioFile(path.replace(".ogg", ".wav")) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="ru-RU")
            update.message.text = text
            await handle_text(update, context)
    except Exception as e:
        await update.message.reply_text("❌ Ошибка распознавания речи")

# Мои сохранённые места
async def saved_places(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    c.execute("SELECT name, address, photo_url FROM places WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    if not rows:
        await update.message.reply_text("У вас пока нет сохранённых мест.")
    for name, addr, url in rows:
        await update.message.reply_text(f"🏙️ {name}\n📍 {addr}\n🔗 {url}")

# Основной запуск
if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.Regex("📚 Мои сохранённые места"), saved_places))

    Thread(target=run_flask).start()
    application.run_polling()
