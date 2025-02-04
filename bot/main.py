# bot/main.py

import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from rag.config import TELEGRAM_BOT_TOKEN
from .handlers import register_handlers

async def main():
    # Создаём объекты бота и диспетчера
    bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    # Регистрируем хэндлеры
    register_handlers(dp)

    # Запускаем "вечный" поллинг
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
