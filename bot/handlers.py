# bot/handlers.py
from aiogram import F
from aiogram.types import Message
from aiogram import Dispatcher
from aiogram.filters import Command

# Импортируем нашу RAG-цепочку
from rag.pipeline import get_rag_chain, get_answer

# Инициализируем цепочку заранее (или можно при старте бота)
rag_chain = get_rag_chain()

async def cmd_start(message: Message):
    """Обработка команды /start"""
    await message.answer("Привет! Я RAG-бот. Задайте вопрос о нашем онлайн-кинотеатре.")

async def process_user_question(message: Message):
    """Обработка любого другого текстового вопроса."""
    user_question = message.text.strip()
    if not user_question:
        await message.answer("Пожалуйста, введите вопрос.")
        return

    answer = get_answer(user_question, rag_chain)
    await message.answer(answer)

def register_handlers(dp: Dispatcher):
    """
    Регистрация всех хэндлеров в диспетчере aiogram 3.
    Порядок регистрации важен, сначала команда /start, потом любой текст.
    """
    # Фильтр команды
    dp.message.register(cmd_start, Command(commands=["start"]))

    # Фильтр "любой текст" (если не команда)
    dp.message.register(process_user_question, F.text)
