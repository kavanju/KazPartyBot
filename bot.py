import os
import logging
import json
from dotenv import load_dotenv
import openai
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

load_dotenv()

TOKEN = os.getenv("TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logging.error("OpenAI API key is missing!")

openai.api_key = OPENAI_API_KEY

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

DATA_FILE = "data/saved_places.json"
os.makedirs("data", exist_ok=True)

def load_saved():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE, "r", encoding="utf-8"))
    return {}

def save_place(user_id: int, place: dict):
    data = load_saved()
    data.setdefault(str(user_id), []).append(place)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📍 Куда сходить?"))
    kb.add(KeyboardButton("📚 Мои сохранённые места"))
    await message.answer("Привет! Я AI-помощник. Опиши, куда хочешь сходить.", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "📚 Мои сохранённые места")
async def show_saved(message: types.Message):
    data = load_saved().get(str(message.from_user.id)) or []
    if not data:
        await message.answer("У тебя нет сохранённых мест.")
    else:
        reply = "\n".join(f"{i+1}. {p.get('name')}" for i,p in enumerate(data))
        await message.answer(f"📌 Сохранённые места:\n\n{reply}")

async def ask_openai(question: str) -> str:
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":question}],
            temperature=0.6,
            max_tokens=500
        )
        return resp.choices[0].message["content"].strip()
    except Exception as e:
        logging.exception("OpenAI error")
        return f"Ошибка AI: {e}"

@dp.message_handler()
async def handle_text(message: types.Message):
    await message.answer("⌛ Думаю...")
    ai_reply = await ask_openai(message.text)
    # Пример сохранения:
    place = {"name": f"Рекомендация: тема — {message.text}", "description": ai_reply}
    save_place(message.from_user.id, place)
    await message.answer(f"{ai_reply}\n\n✅ Сохранил это место!")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
