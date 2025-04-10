# bot/main.py
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from rag.config import TELEGRAM_BOT_TOKEN
from bot.handlers import register_handlers  # абсолютный импорт
from db.db_data import init_db_documents  # инициализация таблицы
from bot.admin_handlers import register_admin_handlers  # админ-обработчики

async def main():
    # Инициализируем БД (таблица для данных)
    await init_db_documents()

    bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    register_handlers(dp)         # регистрация обычных хэндлеров
    register_admin_handlers(dp)   # регистрация админских хэндлеров

    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())