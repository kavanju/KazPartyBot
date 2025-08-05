import os import logging import asyncio from telegram import Update, InputFile, KeyboardButton, ReplyKeyboardMarkup from telegram.ext import ( ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters ) from dotenv import load_dotenv from duckduckgo_search import DDGS from PIL import Image import requests import io import speech_recognition as sr from pydub import AudioSegment from flask import Flask from threading import Thread

load_dotenv()

TOKEN = os.getenv("TOKEN") OWNER_ID = int(os.getenv("OWNER_ID")) KASPI_NAME = os.getenv("KASPI_NAME") FREE_ATTEMPT_USERS = set() PAID_USERS = {}

logging.basicConfig(level=logging.INFO)

Flask app for Render keep-alive

app = Flask('')

@app.route('/') def home(): return "KazPartyBot is alive!"

def run(): app.run(host='0.0.0.0', port=8080)

def keep_alive(): Thread(target=run).start()

====== ПОИСК ЗАВЕДЕНИЙ ЧЕРЕЗ ИИ (DuckDuckGo) ======

def search_places(query): results = [] with DDGS() as ddgs: for r in ddgs.text(query + " site:2gis.kz", max_results=3): results.append({"title": r['title'], "href": r['href'], "body": r['body']}) return results

====== РАСПОЗНАВАНИЕ ГОЛОСА ======

async def recognize_voice(file_path): recognizer = sr.Recognizer() sound = AudioSegment.from_file(file_path) wav_path = file_path.replace(".ogg", ".wav") sound.export(wav_path, format="wav")

with sr.AudioFile(wav_path) as source:
    audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio, language="ru-RU")
        return text
    except sr.UnknownValueError:
        return "Не удалось распознать речь."

====== ОБРАБОТКА КОМАНД ======

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): await update.message.reply_text( "👋 Привет! Я ИИ-помощник по заведениям Казахстана. Напиши, куда хочешь пойти — я подберу лучшие варианты.\n\n" "🗣 Можешь использовать голосовой ввод или текст.\n" "💵 Для неограниченного доступа — оплати 400₸: https://pay.kaspi.kz/pay/sav8emzy\n" "После оплаты доступ активируется в течение 1 минуты.\n" )

====== ПРОВЕРКА ДОСТУПА ======

def user_has_access(user_id): return user_id in PAID_USERS or user_id in FREE_ATTEMPT_USERS

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE): user_id = update.effective_user.id text = update.message.text

if not user_has_access(user_id):
    FREE_ATTEMPT_USERS.add(user_id)
    await update.message.reply_text("🔄 Проверка оплаты... Пожалуйста, подождите минуту.")
    await asyncio.sleep(60)
    PAID_USERS[user_id] = True
    await update.message.reply_text("✅ Доступ выдан! Теперь вы можете пользоваться ботом без ограничений на 48 часов.")

results = search_places(text)
if not results:
    await update.message.reply_text("❌ Ничего не найдено. Попробуйте описать запрос иначе.")
    return

for place in results:
    msg = f"🏙 <b>{place['title']}</b>\n{place['body']}\n🔗 <a href='{place['href']}'>Ссылка</a>"
    await update.message.reply_html(msg)

====== ОБРАБОТКА ГОЛОСА ======

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.effective_user voice = await update.message.voice.get_file() file_path = f"voice_{user.id}.ogg" await voice.download_to_drive(file_path)

text = await recognize_voice(file_path)
update.message.text = text
await handle_message(update, context)

====== ОСНОВНОЙ ЗАПУСК ======

if name == 'main': keep_alive() app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(MessageHandler(filters.VOICE, handle_voice))

print("Bot is running...")
app.run_polling()

