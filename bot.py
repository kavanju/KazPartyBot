from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import openai
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Загрузка .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
KASPI_PAY_LINK = os.getenv("KASPI_PAY_LINK")
PAYPAL_LINK = "https://www.paypal.com/paypalme/yourlink"  # Замени на свой PayPal
KASPI_PRICE = "400₸ за 48 часов"
PAYPAL_PRICE = "$2.5 for 48 hours"

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
openai.api_key = OPENAI_API_KEY
user_access = {}

# 🔍 GPT-запрос: Найди заведения с параметрами
async def find_places(prompt, lang="ru"):
    system_prompt = {
        "ru": (
            "Ты ИИ-гид по заведениям. Пользователь описал, куда хочет сходить.\n"
            "Предложи 3 заведения, для каждого укажи:\n"
            "- 📍 Название\n"
            "- 📸 Краткое описание и атмосферу (музыка, аудитория)\n"
            "- 💵 Средний чек (еда и напитки)\n"
            "- 🗺️ Адрес или примерное местоположение\n"
            "- 🌐 Пример фото (предложи ссылку или опиши изображение)"
        ),
        "en": (
            "You are an AI assistant for finding venues. The user described what kind of place they want to visit.\n"
            "Suggest 3 venues, and for each include:\n"
            "- 📍 Name\n"
            "- 📸 Short description and atmosphere (music, crowd)\n"
            "- 💵 Average check (food and drinks)\n"
            "- 🗺️ Address or approximate location\n"
            "- 🌐 Example photo link or image description"
        )
    }

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt[lang]},
                {"role": "user", "content": prompt}
            ]
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ Ошибка OpenAI: {e}"

# 🔘 /start
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я — KazPartyBot.\n"
        "Я помогу тебе найти лучшие бары, кафе, клубы и рестораны по твоим критериям 🍸🍔🕺\n\n"
        f"💰 Стоимость:\n• {KASPI_PRICE}\n• {PAYPAL_PRICE}\n\n"
        f"🔗 Kaspi Pay: {KASPI_PAY_LINK}\n"
        f"🌍 PayPal: {PAYPAL_LINK}\n\n"
        "📸 После оплаты — пришли фото или скрин чека."
    )

# 🧾 Фото оплаты
@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_payment_photo(message: types.Message):
    user_id = message.from_user.id
    user_access[user_id] = datetime.utcnow() + timedelta(hours=48)
    await message.reply("✅ Оплата принята! Можешь описать, куда хочешь сходить — я подберу заведения.")

# 🧠 Запрос пользователя
@dp.message_handler(content_types=types.ContentType.TEXT)
async def handle_request(message: types.Message):
    user_id = message.from_user.id
    now = datetime.utcnow()

    if user_id not in user_access or user_access[user_id] < now:
        await message.reply(
            "🔒 Доступ ограничен.\n"
            f"📸 Отправь фото оплаты Kaspi (400₸): {KASPI_PAY_LINK}\n"
            f"🌍 Или оплати через PayPal ($2.5): {PAYPAL_LINK}"
        )
        return

    user_text = message.text
    lang = "ru" if message.from_user.language_code == "ru" else "en"
    await message.reply("🔎 Подбираю заведения по твоим критериям...")
    ai_reply = await find_places(user_text, lang=lang)
    await message.reply(ai_reply)
