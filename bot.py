import logging
import openai
import os
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import sqlite3
import requests

# ✅ Логирование
logging.basicConfig(level=logging.INFO)

# ✅ Инициализация
TOKEN = os.getenv("TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)

# ✅ SQLite база для сохранения
conn = sqlite3.connect("data/places.db")
cur = conn.cursor()
cur.execute('''CREATE TABLE IF NOT EXISTS saved_places 
               (user_id INTEGER, name TEXT, description TEXT, image_url TEXT, map_url TEXT)''')
conn.commit()


# ✅ Старт
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("👋 Привет! Опиши, куда хочешь пойти (например, 'бар с живой музыкой и танцами')")


# ✅ Сохранение места
@dp.message_handler(lambda msg: msg.text.startswith("✅ Сохранить"))
async def save_place(message: types.Message):
    data = message.text.replace("✅ Сохранить: ", "").split(" | ")
    if len(data) >= 3:
        name, desc, map_url = data[:3]
        cur.execute("INSERT INTO saved_places VALUES (?, ?, ?, ?, ?)", (message.from_user.id, name, desc, "", map_url))
        conn.commit()
        await message.answer("✅ Место сохранено!")
    else:
        await message.answer("Ошибка при сохранении.")


# ✅ Просмотр сохранённых мест
@dp.message_handler(commands=["saved"])
async def show_saved(message: types.Message):
    cur.execute("SELECT name, description, map_url FROM saved_places WHERE user_id = ?", (message.from_user.id,))
    rows = cur.fetchall()
    if not rows:
        await message.answer("У тебя пока нет сохранённых мест.")
    else:
        for row in rows:
            await message.answer(f"📍 {row[0]}\n{row[1]}\n🔗 {row[2]}")


# ✅ ИИ-поиск места
@dp.message_handler()
async def search_places(message: types.Message):
    query = message.text

    await message.answer("🔎 Ищу заведения по твоему запросу...")

    try:
        # AI-пояснение
        completion = openai_client.chat.completions.create(
            messages=[{"role": "user", "content": f"Определи тип заведения из запроса: {query}"}],
            model="gpt-3.5-turbo",
        )
        ai_result = completion.choices[0].message.content.strip()

        # Поиск через SerpAPI
        params = {
            "engine": "google_maps",
            "q": query,
            "type": "search",
            "hl": "ru",
            "api_key": SERPAPI_API_KEY
        }
        response = requests.get("https://serpapi.com/search", params=params).json()
        places = response.get("local_results", [])

        if not places:
            await message.answer("😕 Ничего не найдено.")
            return

        for place in places[:3]:  # Только топ-3
            name = place.get("title", "Без названия")
            desc = place.get("description", "")
            image = place.get("thumbnail")
            map_link = place.get("link")

            text = f"📍 {name}\n📝 {desc}\n🔗 {map_link}"
            if image:
                await bot.send_photo(message.chat.id, photo=image, caption=text)
            else:
                await message.answer(text)

            save_btn = InlineKeyboardMarkup().add(
                InlineKeyboardButton("✅ Сохранить", callback_data=f"save|{name}|{desc}|{map_link}")
            )
            await message.answer("Хочешь сохранить это место?", reply_markup=save_btn)

    except Exception as e:
        await message.answer(f"❌ Ошибка AI:\n\n{e}")


# ✅ Обработка кнопки "Сохранить"
@dp.callback_query_handler(lambda call: call.data.startswith("save|"))
async def callback_save(call: types.CallbackQuery):
    _, name, desc, map_url = call.data.split("|", 3)
    cur.execute("INSERT INTO saved_places VALUES (?, ?, ?, ?, ?)", (call.from_user.id, name, desc, "", map_url))
    conn.commit()
    await call.message.edit_text(f"✅ Место сохранено: {name}")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
