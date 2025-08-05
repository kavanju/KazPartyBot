import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes,
    MessageHandler, CommandHandler,
    filters
)
from duckduckgo_search import DDGS
from dotenv import load_dotenv
import speech_recognition as sr
from pydub import AudioSegment
import requests

load_dotenv()
TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))

logging.basicConfig(level=logging.INFO)

users_with_access = {}

# Проверка доступа
def has_access(user_id):
    return users_with_access.get(user_id, False)

# Генерация кнопки оплаты
def get_payment_keyboard():
    keyboard = [
        [InlineKeyboardButton("💳 Оплатить 400₸ через Kaspi", url="https://pay.kaspi.kz/pay/sav8emzy")],
        [InlineKeyboardButton("🔁 Я оплатил", callback_data="check_payment")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Команда старта
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я помогу найти заведение по твоему описанию.\n\n"
        "💬 Просто напиши, куда хочешь сходить — например: «Хочу бар с живой музыкой и кальяном».\n\n"
        "🗣️ Можешь отправить голосовое сообщение.\n"
        "💳 Чтобы получить доступ — оплати 400₸ за 48 часов доступа.",
        reply_markup=get_payment_keyboard()
    )

# Проверка оплаты (с задержкой)
async def check_payment_delayed(user_id, context):
    await asyncio.sleep(60)  # Ждём 1 минуту
    users_with_access[user_id] = True
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Спасибо! Доступ активирован на 48 часов. Можешь описывать, куда хочешь пойти 😊"
        )
    except:
        pass

# Обработка нажатий кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "check_payment":
        await query.edit_message_text(
            "⏳ Проверка оплаты... Пожалуйста, убедитесь, что вы отправили средства и подождите. Доступ будет предоставлен в течение 1 минуты."
        )
        asyncio.create_task(check_payment_delayed(user_id, context))

# Поиск заведений через DuckDuckGo
def search_places(query: str):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query + " site:2gis.kz", max_results=3):
            results.append(r)
    return results

# Получение изображений
def get_images(query: str):
    images = []
    with DDGS() as ddgs:
        for img in ddgs.images(query, max_results=2):
            images.append(img["image"])
    return images

# Обработка текстовых сообщений
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if not has_access(user_id):
        await update.message.reply_text("🚫 У вас нет доступа. Пожалуйста, оплатите, чтобы продолжить.", reply_markup=get_payment_keyboard())
        return

    query = update.message.text
    await update.message.reply_text("🔍 Ищу подходящие места...")

    places = search_places(query)
    images = get_images(query)

    if not places:
        await update.message.reply_text("❌ Не удалось найти заведения. Попробуйте переформулировать запрос.")
        return

    for i, place in enumerate(places):
        text = f"📍 *{place['title']}*\n{place['body']}\n🔗 [Открыть]({place['href']})"
        img_url = images[i] if i < len(images) else None
        if img_url:
            await update.message.reply_photo(photo=img_url, caption=text, parse_mode="Markdown")
        else:
            await update.message.reply_text(text, parse_mode="Markdown")

# Распознавание голосовых сообщений
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if not has_access(user_id):
        await update.message.reply_text("🚫 У вас нет доступа. Пожалуйста, оплатите, чтобы продолжить.", reply_markup=get_payment_keyboard())
        return

    voice = await update.message.voice.get_file()
    ogg_path = f"voice_{user_id}.ogg"
    wav_path = f"voice_{user_id}.wav"
    await voice.download_to_drive(ogg_path)

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
        await update.message.reply_text("❌ Не удалось распознать речь. Попробуйте ещё раз.")

# Запуск бота
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.ALL, lambda u, c: None))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, lambda u, c: None))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, lambda u, c: None))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_TITLE, lambda u, c: None))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_PHOTO, lambda u, c: None))
    app.add_handler(MessageHandler(filters.StatusUpdate.DELETE_CHAT_PHOTO, lambda u, c: None))
    app.add_handler(MessageHandler(filters.StatusUpdate.GROUP_CHAT_CREATED, lambda u, c: None))
    app.add_handler(MessageHandler(filters.StatusUpdate.SUPERGROUP_CHAT_CREATED, lambda u, c: None))
    app.add_handler(MessageHandler(filters.StatusUpdate.CHANNEL_CHAT_CREATED, lambda u, c: None))
    app.add_handler(MessageHandler(filters.StatusUpdate.MIGRATE_TO_CHAT_ID, lambda u, c: None))
    app.add_handler(MessageHandler(filters.StatusUpdate.MIGRATE_FROM_CHAT_ID, lambda u, c: None))
    app.add_handler(MessageHandler(filters.StatusUpdate.PINNED_MESSAGE, lambda u, c: None))
    app.add_handler(MessageHandler(filters.StatusUpdate.MESSAGE_AUTO_DELETE_TIMER_CHANGED, lambda u, c: None))
    app.add_handler(MessageHandler(filters.StatusUpdate.UNKNOWN, lambda u, c: None))
    app.add_handler(MessageHandler(filters.UpdateType.UNKNOWN, lambda u, c: None))
    app.add_handler(MessageHandler(filters.UpdateType.CALLBACK_QUERY, button_handler))

    print("🤖 Бот запущен...")
    app.run_polling()
