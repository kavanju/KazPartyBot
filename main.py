from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.utils import executor
import logging
import os

from handlers.start import register_start_handlers

API_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

register_start_handlers(dp)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
