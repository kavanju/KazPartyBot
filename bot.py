import os
import logging
import asyncio
import tempfile
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton,
    ReplyKeyboardMarkup, InputFile, MessageEntity
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from duckduckgo_search import DDGS
from PIL import Image
import pytesseract
import speech_recognition as sr
from pydub import AudioSegment

load_dotenv()
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
KASPI_NAME = os.getenv("KASPI_NAME")

user_access = {}  # user_id: datetime
used_free = set()  # кто уже использовал бесплатный пробный запрос

# ==== Меню ====
main_menu = InlineKeyboardMarkup([
    [InlineKeyboardButton("📍 Найти место", callback_data="find")],
    [InlineKeyboardButton("🗣 Голосовой ввод", callback_data="voice")],
    [InlineKeyboardButton("💳 Отправить чек Kaspi", callback_data="pay")],
    [InlineKeyboardButton("ℹ️ Инфо", callback_data="info")]
])

# ==== Команды ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Добро пожаловать в KazPartyBot!\n\n"
        "Я подберу заведения по твоему описанию (бар, клуб, ресторан и т.п.).\n\n"
        "💡 Первый запрос — бесплатный!\n\n"
        "⏳ Оплата: 400₸ за 48 часов доступа.",
        reply_markup=main_menu
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "find":
        await query.message.reply_text("✍️ Опиши, куда хочешь пойти:")
    elif query.data == "voice":
        await query.message.reply_text("🎤 Отправь голосовое сообщение.")
    elif query.data == "pay":
        await query.message.reply_text("📷 Отправь фото чека Kaspi.")
    elif query.data == "info":
        await query.message.reply_text(
            "💳 Оплата через Kaspi: 400₸ за 48 часов доступа.\n"
            f"Имя получателя: *{KASPI_NAME}*\n"
            "Ссылка на оплату: https://pay.kaspi.kz/pay/sav8emzy",
            parse_mode='Markdown'
        )

# ==== Проверка доступа ====
def has_access(user_id: int) -> bool:
    if user_id in user_access and user_access[user_id] > datetime.now():
        return True
    return False

def grant_access(user_id: int, hours=48):
    user_access[user_id] = datetime.now() + timedelta(hours=hours)

# ==== Обработка текстов ====
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if not has_access(user_id):
        if user_id in used_free:
            await update.message.reply_text("🔒 У вас нет доступа. Отправьте чек Kaspi для активации.")
            return
        else:
            used_free.add(user_id)
            await update.message.reply_text("✅ Использован бесплатный пробный запрос.")

    await update.message.reply_text("🔍 Ищу заведения, подождите...")

    results = DDGS().text(text, max_results=5)
    if not results:
        await update.message.reply_text("❌ Ничего не найдено.")
        return

    for res in results:
        msg = f"🏙️ *{res['title']}*\n🌐 {res['href']}"
        if res.get("body"):
            msg += f"\n📝 {res['body']}"
        await update.message.reply_text(msg, parse_mode="Markdown")

# ==== Обработка фото (Kaspi чек) ====
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    photo = update.message.photo[-1]
    file = await photo.get_file()
    path = tempfile.mktemp(suffix=".jpg")
    await file.download_to_drive(path)

    text = pytesseract.image_to_string(Image.open(path))
    if KASPI_NAME.lower() in text.lower() and "400" in text:
        grant_access(user_id)
        await update.message.reply_text("✅ Оплата подтверждена. Доступ активирован на 48 часов.")
    else:
        await update.message.reply_text("❌ Не удалось подтвердить оплату. Проверьте, чтобы было видно имя и сумму 400₸.")

# ==== Обработка голосовых ====
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if not has_access(user_id) and user_id in used_free:
        await update.message.reply_text("🔒 Нет доступа. Отправьте чек Kaspi.")
        return

    file = await update.message.voice.get_file()
    ogg_path = tempfile.mktemp(suffix=".ogg")
    wav_path = tempfile.mktemp(suffix=".wav")
    await file.download_to_drive(ogg_path)

    sound = AudioSegment.from_ogg(ogg_path)
    sound.export(wav_path, format="wav")

    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio, language="ru-RU")
        await update.message.reply_text(f"🗣 Вы сказали: {text}")
        await handle_text(update, context)
    except:
        await update.message.reply_text("❌ Не удалось распознать речь.")

# ==== Основной запуск ====
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    print("✅ Бот запущен...")
    app.run_polling()
