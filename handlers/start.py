from aiogram import Dispatcher, types

async def cmd_start(message: types.Message):
    await message.answer("Привет! Я KazPartyBot. Напиши, куда хочешь пойти, и я подберу заведения!")

def register_start_handlers(dp: Dispatcher):
    dp.register_message_handler(cmd_start, commands=["start", "help"])
