import os import logging from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler from duckduckgo_search import DDGS from PIL import Image import pytesseract from io import BytesIO import speech_recognition as sr from pydub import AudioSegment import requests from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN") OWNER_ID = int(os.getenv("OWNER_ID")) KASPI_NAME = os.getenv("KASPI_NAME")

logging.basicConfig( format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO )

Поиск заведений через DuckDuckGo

async def search_places(query: str) -> str: results = [] with DDGS() as ddgs: for r in ddgs.text(query, region='kz-ru', safesearch='Off', max_results=5): results.append(f"🔹 <b>{r['title']}</b>\n{r['href']}\n{r['body']}") return "\n\n".join(results) if results else "😕 Ничего не найдено. Попробуйте изменить запрос."

Обработка команды /start

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text("👋 Привет! Отправь голосом или текстом, куда хочешь сходить — я подберу заведения! Также можешь отправить фото Kaspi-чека для активации доступа.")

Обработка текстового сообщения

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.message.text await update.message.reply_text("🔍 Ищу заведения...") results = await search_places(query) await update.message.reply_text(results, parse_mode="HTML")

Обработка голосового ввода

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE): file = await update.message.voice.get_file() ogg_path = "voice.ogg" wav_path = "voice.wav" await file.download_to_drive(ogg_path)

# Конвертация ogg в wav
sound = AudioSegment.from_ogg(ogg_path)
sound.export(wav_path, format="wav")

recognizer = sr.Recognizer()
with sr.AudioFile(wav_path) as source:
    audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio, language="ru-RU")
        await update.message.reply_text(f"🗣️ Вы сказали: {text}\n🔍 Ищу...")
        results = await search_places(text)
        await update.message.reply_text(results, parse_mode="HTML")
    except sr.UnknownValueError:
        await update.message.reply_text("❌ Не удалось распознать речь.")

Обработка фото Kaspi чека

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE): file = await update.message.photo[-1].get_file() img_bytes = await file.download_as_bytearray() image = Image.open(BytesIO(img_bytes)) text = pytesseract.image_to_string(image, lang='rus')

if KASPI_NAME.lower() in text.lower() and ("400" in text or "₸" in text):
    await update.message.reply_text("✅ Оплата подтверждена. Доступ активирован на 48 часов.")
else:
    await update.message.reply_text("❌ Не удалось подтвердить чек. Убедитесь, что видно имя и сумму 400₸.")

Основной запуск

if name == 'main': app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.add_handler(MessageHandler(filters.VOICE, handle_voice))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

print("KazPartyBot запущен...")
app.run_polling()

