import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
import os
import json

API_TOKEN = os.getenv("TOKEN")  # Телеграм токен

# Логирование
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Файл для сохранения заведений
DATA_FILE = "data/saved_places.json"
os.makedirs("data", exist_ok=True)

# Загружаем заведения
def load_saved_places():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

# Сохраняем заведения
def save_place(user_id, place):
    data = load_saved_places()
    data.setdefault(str(user_id), []).append(place)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Обработка команды /start
@dp.message_handler(commands=["start"])
async def start_cmd(message: Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📍 Куда сходить?"))
    keyboard.add(KeyboardButton("📚 Мои сохранённые места"))
    await message.answer("Привет! Я ИИ-помощник по заведениям. Опиши, куда хочешь сходить, или выбери опцию.", reply_markup=keyboard)

# Обработка кнопки "Мои сохранённые места"
@dp.message_handler(lambda m: m.text == "📚 Мои сохранённые места")
async def show_saved(message: Message):
    data = load_saved_places()
    places = data.get(str(message.from_user.id), [])
    if not places:
        await message.answer("У тебя пока нет сохранённых мест.")
    else:
        reply = "📌 Твои места:\n\n"
        for i, place in enumerate(places, 1):
            reply += f"{i}. {place.get('name', 'Без названия')}\n"
        await message.answer(reply)

# Обработка текстового запроса пользователя
@dp.message_handler()
async def handle_request(message: Message):
    user_input = message.text.strip()
    # Здесь — заглушка ИИ, можно подключить OpenAI
    example_place = {
        "name": f"Пример заведения для: {user_input}",
        "description": "Уютное место с музыкой и танцами",
        "price": "Средний чек: 5000₸",
    }
    save_place(message.from_user.id, example_place)

    await message.answer(
        f"🎉 Нашёл место для тебя:\n\n"
        f"🏠 Название: {example_place['name']}\n"
        f"📖 Описание: {example_place['description']}\n"
        f"💰 {example_place['price']}"
    )

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
