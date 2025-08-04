# bot.py
import logging
import os
import io
import base64
from datetime import datetime, timedelta
from PIL import Image
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InputFile
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import asyncio

from recognizer import recognize_kaspi_receipt  # твой AI-парсер чеков

TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
KASPI_NAME = os.getenv("KASPI_NAME")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# Пользовательские доступы
user_access = {}

class States(StatesGroup):
    waiting_for_receipt = State()

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("👋 Привет! Я помогу найти лучшие заведения в твоем городе.\n\n💸 Для доступа отправь чек Kaspi Pay на имя *{name}* суммой 400₸ или оплати тут:\nhttps://pay.kaspi.kz/pay/sav8emzy\n\nПосле оплаты пришли фото чека сюда.".format(name=KASPI_NAME), parse_mode="Markdown")

@dp.message_handler(commands=['check'])
async def check_access(message: types.Message):
    uid = message.from_user.id
    if uid in user_access and user_access[uid] > datetime.now():
        await message.answer("✅ Доступ активен до: {}".format(user_access[uid].strftime("%Y-%m-%d %H:%M")))
    else:
        await message.answer("🚫 У вас нет активного доступа. Пришлите фото Kaspi чека для активации.")

@dp.message_handler(commands=['receipt'])
async def request_receipt(message: types.Message):
    await message.answer("📷 Пожалуйста, пришли фото Kaspi Pay чека.")
    await States.waiting_for_receipt.set()

@dp.message_handler(content_types=types.ContentType.PHOTO, state=States.waiting_for_receipt)
async def handle_receipt_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    photo_bytes = await photo.download(destination=io.BytesIO())
    photo_bytes.seek(0)

    # Распознать чек с помощью AI
    try:
        result = recognize_kaspi_receipt(photo_bytes)
        full_name, amount, date = result['name'], result['amount'], result['date']

        if full_name == KASPI_NAME and amount >= 400:
            user_access[message.from_user.id] = datetime.now() + timedelta(hours=48)
            await message.answer("✅ Успешно! Доступ активен на 48 часов.")
        else:
            await message.answer("🚫 Не удалось подтвердить чек. Проверьте имя и сумму оплаты.")
    except Exception as e:
        logging.error(f"Ошибка при распознавании чека: {e}")
        await message.answer("❌ Ошибка при обработке чека. Попробуйте снова.")

    await state.finish()

@dp.message_handler(lambda message: message.text.lower() in ["где отдохнуть", "найди заведение", "куда сходить"])
async def recommend(message: types.Message):
    uid = message.from_user.id
    if uid not in user_access or user_access[uid] < datetime.now():
        await message.answer("🔒 Сначала активируйте доступ. Пришлите чек Kaspi Pay.")
        return

    await message.answer("🔍 Подбираю лучшие места по отзывам, атмосфере и фото... ⏳")
    
    # 💡 Здесь будет функция сбора данных по заведениям через открытые источники (например, DuckDuckGo/2GIS парсинг)
    await asyncio.sleep(2)

    await message.answer_photo(photo=open("static/bar_example.jpg", "rb"), caption="📍 *Bar Example*\n\n🎶 Музыка: Lounge\n👥 Аудитория: 25-35\n🍽 Средний чек: 4500₸\n⭐️ Отзывы: 4.5/5\n\n[📍 Посмотреть на карте](https://go.2gis.com/x1234)", parse_mode="Markdown")

@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    await message.answer("📌 Команды:\n/start — запустить\n/receipt — отправить чек\n/check — проверить доступ\n/help — помощь")


if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
