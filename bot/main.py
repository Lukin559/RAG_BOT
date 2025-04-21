# bot/main.py
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage       # ← добавить
from rag.config import TELEGRAM_BOT_TOKEN
from db.db_data import init_db_documents

from bot.handlers import register_handlers
from bot.admin_handlers import register_admin_handlers


async def main():
    await init_db_documents()

    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )

    storage = MemoryStorage()             # ← инициализируем
    dp = Dispatcher(storage=storage)      # ← передаём в Dispatcher

    register_admin_handlers(dp)
    register_handlers(dp)

    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())