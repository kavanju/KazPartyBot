import os
import logging
import tempfile
import pytesseract
from PIL import Image
from pydub import AudioSegment
import speech_recognition as sr
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes,
    filters, CallbackQueryHandler
)

# Загрузка .env
load_dotenv()
TOKEN = os.getenv("TOKEN")
KASPI_NAME = os.getenv("KASPI_NAME")
OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Старт
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Описать, куда хочу", callback_data='text')],
                [InlineKeyboardButton("Голосом сказать", callback_data='voice')],
                [InlineKeyboardButton("Оплатил - чек фото", callback_data='check')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Что хочешь сделать?", reply_markup=reply_markup)

# Обработчик кнопок
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'text':
        await query.message.reply_text("Отправь описание места")
    elif query.data == 'voice':
        await query.message.reply_text("Говори! Отправь голосовое сообщение")
    elif query.data == 'check':
        await query.message.reply_text("Загрузи фото чека Kaspi")

# Обработка текста
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await update.message.reply_text(f"Ищу место по описанию: {text}\nСкоро всё найду...")
    # Тут можешь добавить поиск заведений через API

# Обработка голосового
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.voice.get_file()
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as ogg:
        await file.download_to_drive(ogg.name)
        audio = AudioSegment.from_file(ogg.name)
        wav_path = ogg.name.replace(".ogg", ".wav")
        audio.export(wav_path, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data, language="ru-RU")
                await update.message.reply_text(f"Распознанно: {text}")
                await handle_text(update, context)
            except sr.UnknownValueError:
                await update.message.reply_text("Не понял, повтори")

# Обработка чеков
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.photo[-1].get_file()
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        await file.download_to_drive(tf.name)
        image = Image.open(tf.name)
        text = pytesseract.image_to_string(image, lang='rus')
        if KASPI_NAME.lower() in text.lower():
            await update.message.reply_text("Чек подтверждён. Доступ активирован на 48 часов!")
        else:
            await update.message.reply_text("Имя в чеке не совпадает. Проверьте, что чек каспи содержит имя: {KASPI_NAME}")

# Запуск
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.run_polling()
