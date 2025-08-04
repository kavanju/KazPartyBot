import os import logging import pytesseract import datetime import io import re from PIL import Image from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler) from flask import Flask from threading import Thread from dotenv import load_dotenv from collections import defaultdict from pydub import AudioSegment import speech_recognition as sr import requests

load_dotenv()

TOKEN = os.getenv("TOKEN") OWNER_ID = int(os.getenv("OWNER_ID", "123456789")) KASPI_NAME = os.getenv("KASPI_NAME", "Имя Kaspi")

user_access = {} free_trial_used = set() saved_places = defaultdict(list)

logging.basicConfig(level=logging.INFO) logger = logging.getLogger(name)

flask_app = Flask(name)

@flask_app.route("/") def home(): return "KazPartyBot is alive!"

def run_flask(): flask_app.run(host="0.0.0.0", port=8080)

Кнопки меню

main_keyboard = InlineKeyboardMarkup([ [InlineKeyboardButton("📚 Мои сохранённые места", callback_data="saved")] ])

Команды

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = update.effective_user.id if user_id == OWNER_ID: user_access[user_id] = True await update.message.reply_text("👑 Привет, админ! Доступ активирован навсегда.", reply_markup=main_keyboard) return

if user_access.get(user_id):
    await update.message.reply_text("✅ У вас уже есть доступ.", reply_markup=main_keyboard)
elif user_id not in free_trial_used:
    free_trial_used.add(user_id)
    user_access[user_id] = True
    await update.message.reply_text("🎁 Бесплатный доступ активирован! Напишите запрос.", reply_markup=main_keyboard)
else:
    await update.message.reply_text(
        "❌ У вас нет доступа.\n\n💸 Оплата за 48 часов:\n"
        "• 400₸ Kaspi Pay\n• $2 PayPal\n\n"
        "📎 Kaspi: https://pay.kaspi.kz/pay/sav8emzy\n"
        "После оплаты пришлите чек сюда."
    )

Распознавание текста с чека

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = update.effective_user.id photo = await update.message.photo[-1].get_file() image_bytes = await photo.download_as_bytearray() image = Image.open(io.BytesIO(image_bytes)) text = pytesseract.image_to_string(image, lang='rus+eng') logger.info(f"Чек от {user_id}: {text}")

today = datetime.datetime.now().strftime("%d.%m.%Y")
if KASPI_NAME in text and "400" in text and today in text:
    user_access[user_id] = True
    await update.message.reply_text("✅ Доступ активирован. Пишите, что ищем!", reply_markup=main_keyboard)
else:
    await update.message.reply_text("❌ Не удалось подтвердить чек. Убедитесь, что видно имя, сумму 400₸ и сегодняшнюю дату.")

Голосовые запросы

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = update.effective_user.id if not user_access.get(user_id) and user_id != OWNER_ID: await update.message.reply_text("❌ Нет доступа. Нажмите /start") return

voice = await update.message.voice.get_file()
ogg_data = await voice.download_as_bytearray()
ogg_audio = io.BytesIO(ogg_data)
ogg_audio.name = 'input.ogg'

audio = AudioSegment.from_file(ogg_audio)
wav_io = io.BytesIO()
audio.export(wav_io, format="wav")
wav_io.seek(0)

recognizer = sr.Recognizer()
with sr.AudioFile(wav_io) as source:
    audio_data = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio_data, language="ru-RU")
        await update.message.reply_text(f"🎤 Вы сказали: {text}")
        await process_search(text, update, context)
    except sr.UnknownValueError:
        await update.message.reply_text("😕 Не удалось распознать речь.")

Обработка текста и голосовых запросов

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = update.effective_user.id if not user_access.get(user_id) and user_id != OWNER_ID: await update.message.reply_text("❌ Нет доступа. Нажмите /start") return

query = update.message.text
await process_search(query, update, context)

Обработка кнопок меню

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query user_id = query.from_user.id await query.answer() if query.data == "saved": places = saved_places.get(user_id, []) if not places: await query.edit_message_text("📭 У вас нет сохранённых мест.") return msg = "📚 Ваши сохранённые места:\n\n" + "\n\n".join(places) await query.edit_message_text(msg[:4000])

# Поиск заведений через DuckDuckGo/TripAdvisor/2GIS

async def process_search(query: str, update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = update.effective_user.id await update.message.reply_text(f"🤖 Ищу по запросу: «{query}»...")

try:
    url = f"https://duckduckgo.com/html/?q=site:2gis.kz+{query.replace(' ', '+')}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    results = re.findall(r'<a rel="nofollow" class="result__a" href="(.*?)">(.*?)</a>', r.text)

    if not results:
        await update.message.reply_text("😕 Ничего не найдено. Попробуйте уточнить запрос.")
        return

    messages = []
    for link, title in results[:3]:
        place_text = f"🏙️ <b>{title}</b>\n🔗 <a href='{link}'>{link}</a>"
        messages.append(place_text)
        saved_places[user_id].append(f"{title} - {link}")

    for msg in messages:
        await update.message.reply_text(msg, parse_mode='HTML')

except Exception as e:
    logger.error(f"Ошибка поиска: {e}")
    await update.message.reply_text("⚠️ Ошибка при поиске. Попробуйте позже.")

def main(): Thread(target=run_flask).start()

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_buttons))
app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.add_handler(MessageHandler(filters.VOICE, voice_handler))

app.run_polling()

if name == "main": main()


