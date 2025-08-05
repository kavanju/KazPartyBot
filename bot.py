import os import logging import asyncio import speech_recognition as sr from pydub import AudioSegment from telegram import Update, KeyboardButton, ReplyKeyboardMarkup from telegram.ext import ( ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes ) from duckduckgo_search import DDGS from dotenv import load_dotenv from PIL import Image import pytesseract import datetime

load_dotenv()

TOKEN = os.getenv("TOKEN") KASPI_NAME = os.getenv("KASPI_NAME", "Имя получателя")

logging.basicConfig(level=logging.INFO) logger = logging.getLogger(name)

users_access = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): buttons = [[KeyboardButton("🎹 Голосовой ввод")]] keyboard = ReplyKeyboardMarkup(buttons, resize_keyboard=True) await update.message.reply_text( "👋 Привет! Опиши, куда хочешь пойти (бар, клуб, кафе и т.д.) — я подберу лучшие места!\n\n" "📸 Отправь фото чека Kaspi после оплаты по ссылке: https://pay.kaspi.kz/pay/sav8emzy\n\n" "💬 Или используй кнопку ниже для голосового ввода.", reply_markup=keyboard )

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): file = await update.message.voice.get_file() file_path = "/tmp/audio.ogg" wav_path = "/tmp/audio.wav" await file.download_to_drive(file_path)

AudioSegment.from_ogg(file_path).export(wav_path, format="wav")

recognizer = sr.Recognizer()
with sr.AudioFile(wav_path) as source:
    audio = recognizer.record(source)

try:
    text = recognizer.recognize_google(audio, language="ru-RU")
    await search_places(update, context, text)
except sr.UnknownValueError:
    await update.message.reply_text("Не удалось распознать речь.")
except Exception as e:
    await update.message.reply_text("Произошла ошибка при распознавании.")

async def search_places(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str = None): if query is None: query = update.message.text

await update.message.reply_text("🔍 Ищу подходящие места, подожди немного...")

results = []
with DDGS() as ddgs:
    for r in ddgs.text(f"{query} сайт:2gis.kz", max_results=3):
        results.append(f"{r['title']}\n{r['href']}\n")

if results:
    await update.message.reply_text("\u0412от что я нашёл:\n\n" + "\n\n".join(results))
else:
    await update.message.reply_text("Не удалось найти заведения по описанию.")

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = update.message.from_user.id photo_file = await update.message.photo[-1].get_file() photo_path = f"/tmp/receipt_{user_id}.jpg" await photo_file.download_to_drive(photo_path)

img = Image.open(photo_path)
text = pytesseract.image_to_string(img, lang="rus")

if KASPI_NAME.lower() in text.lower():
    await update.message.reply_text(
        "✅ Чек получен. Пожалуйста, подождите 1 минуту, пока мы проверим оплату..."
    )
    await asyncio.sleep(60)
    users_access[user_id] = datetime.datetime.now() + datetime.timedelta(hours=48)
    await update.message.reply_text("🎉 Доступ активирован на 48 часов! Опишите, что хотите найти.")
else:
    await update.message.reply_text(
        "❌ Чек не прошёл проверку. Убедитесь, что на нём есть имя получателя: " + KASPI_NAME
    )

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = update.message.from_user.id now = datetime.datetime.now() if user_id in users_access and users_access[user_id] > now: await search_places(update, context) else: await update.message.reply_text("🚫 Сначала оплатите доступ и отправьте фото чека Kaspi.")

def main(): app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
app.add_handler(MessageHandler(filters.VOICE, voice_handler))
app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

app.run_polling()

if name == "main": main()

