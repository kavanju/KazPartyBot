import os
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from PIL import Image
import pytesseract
from io import BytesIO
import speech_recognition as sr
from pydub import AudioSegment
import requests

load_dotenv()

TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
KASPI_NAME = os.getenv("KASPI_NAME")

logging.basicConfig(level=logging.INFO)

# Проверка оплаты по чеку
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    img_bytes = await file.download_as_bytearray()
    image = Image.open(BytesIO(img_bytes))
    text = pytesseract.image_to_string(image)

    if KASPI_NAME.lower() in text.lower():
        await update.message.reply_text("✅ Оплата найдена. Доступ активирован на 48 часов.")
        # здесь можно сохранить доступ в базу
    else:
        await update.message.reply_text("❌ Не удалось подтвердить оплату. Убедитесь, что чек читаем и отправлен в виде фото.")

# Распознавание речи
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    voice_ogg = BytesIO()
    await file.download_to_memory(out=voice_ogg)
    voice_ogg.seek(0)

    ogg_path = "voice.ogg"
    wav_path = "voice.wav"

    with open(ogg_path, "wb") as f:
        f.write(voice_ogg.read())

    # Конвертация ogg в wav
    audio = AudioSegment.from_ogg(ogg_path)
    audio.export(wav_path, format="wav")

    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data, language="ru-RU")
            await update.message.reply_text(f"Вы сказали: {text}")
            await search_places(update, context, text)
        except sr.UnknownValueError:
            await update.message.reply_text("😕 Не удалось распознать речь.")
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {e}")

# Поиск заведений
async def search_places(update: Update, context: ContextTypes.DEFAULT_TYPE, query=None):
    if not query:
        query = update.message.text
    await update.message.reply_text("🔎 Ищу заведения по вашему запросу...")

    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(f"{query} site:2gis.kz", region="kz-ru", max_results=5):
            results.append(f"{r['title']}\n{r['href']}\n")

    if results:
        await update.message.reply_text("\n\n".join(results))
    else:
        await update.message.reply_text("😔 Не нашёл подходящих заведений. Попробуйте другой запрос.")

# Кнопки
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("🎙️ Голосом", callback_data="voice")],
        [InlineKeyboardButton("📸 Фото чека", callback_data="check")]
    ]
    await update.message.reply_text(
        "Привет! Я помогу тебе найти лучшие места для отдыха и проверю оплату.\n\nПросто напиши, куда хочешь пойти, отправь голос или фото чека.",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "voice":
        await query.edit_message_text("🎤 Отправьте голосовое сообщение.")
    elif query.data == "check":
        await query.edit_message_text("📸 Отправьте фото Kaspi-чека.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_places))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    app.run_polling()

if __name__ == "__main__":
    main()
