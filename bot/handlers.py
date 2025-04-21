# bot/handlers.py
import logging
from datetime import date
from aiogram.enums import ContentType
from aiogram import F, Dispatcher
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from bot.state import support_store
from rag.pipeline import get_rag_chain, get_answer
from db.db_data import get_all_sources

# ────────────────────────────────────────────────
# Константы
# ────────────────────────────────────────────────
SUPPORT_ADMIN_IDS = [504895191]
SUPPORT_BUTTON_TEXT = "Обращение в службу поддержки"
CHANGE_SOURCE_BUTTON_TEXT = "Сменить сервис"
END_SUPPORT_TEXT = "Завершить чат с оператором"
MAX_DAILY_REQUESTS = 10  # максимум вопросов к LLM в день

# ────────────────────────────────────────────────
# Хранилища
# ────────────────────────────────────────────────
user_sources: dict[int, str] = {}      # выбранный сервис
user_requests: dict[int, dict] = {}    # счётчики запросов: {user_id: {"date": date, "count": int}}

rag_chain = get_rag_chain()

# reply‑клавиатура, которая отображается ВСЕГДА
main_reply_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=SUPPORT_BUTTON_TEXT)],
        [KeyboardButton(text=CHANGE_SOURCE_BUTTON_TEXT)],
    ],
    resize_keyboard=True,
)

# ────────────────────────────────────────────────
# /start
# ────────────────────────────────────────────────
async def cmd_start(message: Message):
    sources = await get_all_sources()
    if not sources:
        await message.answer(
            "Источники данных не найдены. Загрузите данные, пожалуйста.",
            reply_markup=main_reply_kb,
        )
        return

    inline_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=src, callback_data=src)] for src in sources]
    )

    await message.answer(
        "Привет! Я бот, который помогает пользователям с их вопросами о различных сервисах. Выберите сервис:",
        reply_markup=inline_kb,
    )
    await message.answer(
        "В любой момент можете вызвать оператора или сменить сервис через кнопки ниже.",
        reply_markup=main_reply_kb,
    )

# ────────────────────────────────────────────────
# Выбор / смена сервиса
# ────────────────────────────────────────────────
async def handle_source_selection(callback: CallbackQuery):
    selected = callback.data
    user_sources[callback.from_user.id] = selected
    logging.info(f"{callback.from_user.id=}: выбран сервис {selected!r}")
    await callback.answer(f"Вы выбрали сервис: {selected}")
    await callback.message.answer(
        f"Теперь можете задавать вопросы о {selected}.",
        reply_markup=main_reply_kb,
    )

async def send_source_list(chat_id: int, bot):
    sources = await get_all_sources()
    if not sources:
        await bot.send_message(chat_id, "Источники данных не найдены.", reply_markup=main_reply_kb)
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=s, callback_data=s)] for s in sources]
    )
    await bot.send_message(chat_id, "Выберите сервис:", reply_markup=kb)

# ────────────────────────────────────────────────
# RAG‑вопрос с лимитом
# ────────────────────────────────────────────────
async def process_rag_question(message: Message):
    user_id = message.from_user.id

    # Проверка, выбрал ли сервис
    if user_id not in user_sources:
        await message.answer(
            "Сначала выберите сервис командой /start.", reply_markup=main_reply_kb
        )
        return

    # Получаем и валидируем текст
    if not (text := message.text and message.text.strip()):
        await message.answer("Пожалуйста, отправьте непустой текстовый вопрос.", reply_markup=main_reply_kb)
        return

    # Лимитирование запросов в день
    today = date.today()
    entry = user_requests.get(user_id)
    if entry and entry["date"] == today:
        if entry["count"] >= MAX_DAILY_REQUESTS:
            await message.answer(
                f"Извините, вы исчерпали {MAX_DAILY_REQUESTS} запросов к LLM за сегодня. Попробуйте завтра.",
                reply_markup=main_reply_kb,
            )
            return
        entry["count"] += 1
    else:
        # Новый день или первый запрос
        user_requests[user_id] = {"date": today, "count": 1}

    # Логируем номер запроса
    logging.info(
        f"Пользователь {user_id} запрос №{user_requests[user_id]['count']} за {today}: {text!r}"
    )

    # Получаем и отправляем ответ
    source = user_sources[user_id]
    answer = get_answer(text, source)
    await message.answer(answer, reply_markup=main_reply_kb)

# ────────────────────────────────────────────────
# Поддержка
# ────────────────────────────────────────────────
async def process_support_request(message: Message):
    await message.answer(
        "Скоро к вам подключится оператор.\n"
        f"Завершить чат — «{END_SUPPORT_TEXT}».",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=END_SUPPORT_TEXT)]],
            resize_keyboard=True,
        ),
    )
    await support_store.enter(message.from_user.id)
    # Уведомляем операторов
    await _copy_to_admins(message)

async def end_support_session(message: Message):
    if not await support_store.active(message.from_user.id):
        await message.answer("Вы не в чате с оператором.")
        return

    await support_store.leave(message.from_user.id)
    await message.answer(
        "Чат с оператором завершён. Можете продолжить работу с ботом.",
        reply_markup=main_reply_kb,
    )
    for admin_id in SUPPORT_ADMIN_IDS:
        await message.bot.send_message(
            admin_id, f"❕ Пользователь {message.from_user.id} завершил чат поддержки."
        )

# ────────────────────────────────────────────────
# Роутер всех текст‑сообщений
# ────────────────────────────────────────────────
async def user_message_router(message: Message):
    text = message.text.strip()

    if text == SUPPORT_BUTTON_TEXT:
        await process_support_request(message)
        return

    if text == END_SUPPORT_TEXT:
        await end_support_session(message)
        return

    if text == CHANGE_SOURCE_BUTTON_TEXT:
        await send_source_list(message.chat.id, message.bot)
        return

    if await support_store.active(message.from_user.id):
        await _copy_to_admins(message)
        return

    # Все прочие — в RAG‑обработчик с лимитами
    await process_rag_question(message)

# ────────────────────────────────────────────────
# Вспомогательные функции
# ────────────────────────────────────────────────
async def _copy_to_admins(msg: Message):
    user_id = msg.from_user.id
    username = f"@{msg.from_user.username}" if msg.from_user.username else "—"
    info = (
        f"👤 ID: <code>{user_id}</code>\n"
        f"Username: {username}\n"
        f"Ответить командой:\n"
        f"<code>/reply {user_id} …текст…</code>"
    )
    for admin_id in SUPPORT_ADMIN_IDS:
        try:
            await msg.bot.forward_message(
                chat_id=admin_id, from_chat_id=msg.chat.id, message_id=msg.message_id
            )
            await msg.bot.send_message(admin_id, info)
        except Exception as exc:
            logging.error(f"Не удалось переслать админу {admin_id}: {exc}")

async def handle_non_text_message(message: Message):
    from bot.admin_handlers import ADMIN_IDS        # локальный импорт, чтобы избежать циклов
    if message.from_user.id in ADMIN_IDS:
        return

    await message.answer(
        "Неверный формат. Пожалуйста, отправьте текстовое сообщение.",
        reply_markup=main_reply_kb,
    )

# ────────────────────────────────────────────────
# Регистрация хэндлеров

def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, Command("start"))
    dp.callback_query.register(handle_source_selection, lambda c: c.data != "change_source")

    # ⬇️  обычные тексты, не начинающиеся с «/»
    dp.message.register(
        user_message_router,
        lambda m: (
            m.content_type == ContentType.TEXT
            and m.text
            and not m.text.startswith("/")
        ),
        flags={"block": True},
    )

    # все остальные типы сообщений (кроме текста) для обычного юзера
    dp.message.register(
        handle_non_text_message,
        lambda m: m.content_type != ContentType.TEXT,
        flags={"block": True},
    )