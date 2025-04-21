# bot/admin_handlers.py
from __future__ import annotations

import asyncio
import logging

from aiogram import Dispatcher, types, F
from aiogram.filters import Command, CommandObject

from db.db_data import (
    add_site_data,
    delete_site_data_by_source,
    get_all_sources,
)
from rag.pipeline import refresh_chain

# ────────────────────────────────────────────────
ADMIN_IDS = {123456789, 504895191}

ADD_BTN = "➕ Добавить источник"
DEL_BTN = "🗑 Удалить источник"
BACK_BTN = "↩️ Назад (пользователь)"

# временный флаг «ждём файл»  {admin_id: True}
_wait_file: dict[int, bool] = {}

# ────────────────────────────────────────────────
#   Клавиатуры
# ────────────────────────────────────────────────
def admin_kb() -> types.ReplyKeyboardMarkup:
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text=ADD_BTN)],
            [types.KeyboardButton(text=DEL_BTN)],
            [types.KeyboardButton(text=BACK_BTN)],
        ],
        resize_keyboard=True,
    )


def user_kb() -> types.ReplyKeyboardRemove:
    return types.ReplyKeyboardRemove()


# ────────────────────────────────────────────────
#   /panel  — показать/обновить админ‑панель
# ────────────────────────────────────────────────
async def cmd_panel(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("Панель администратора:", reply_markup=admin_kb())


# ────────────────────────────────────────────────
#   Кнопка «Назад»
# ────────────────────────────────────────────────
async def back_to_user(message: types.Message):
    from bot.handlers import main_reply_kb 
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("Возврат к пользовательскому режиму.",
                         reply_markup=main_reply_kb)


# ────────────────────────────────────────────────
#   Кнопка «Добавить источник»
# ────────────────────────────────────────────────
async def add_btn_pressed(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    _wait_file[message.from_user.id] = True
    await message.reply("Пришлите .txt‑файл.\n"
                        "Имя файла (до точки) станет названием источника.")


# ────────────────────────────────────────────────
#   Получили .txt‑файл от админа
# ────────────────────────────────────────────────
async def handle_admin_file(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("У вас нет доступа к этой команде.")
        return

    if not message.document or "text" not in message.document.mime_type:
        await message.reply("Пришлите текстовый файл (.txt).")
        return

    # скачали и декодировали (ваш проверенный алгоритм)…
    file_info = await message.bot.get_file(message.document.file_id)
    raw = await message.bot.download_file(file_info.file_path)
    content_bytes = raw.read()
    for enc in ("utf-8", "cp1251", "latin-1"):
        try:
            content = content_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        await message.reply("Не смог прочитать файл: неизвестная кодировка.")
        return

    title = message.document.file_name
    alias = title.rsplit(".", 1)[0]

    # 1) сохраняем в БД
    await add_site_data(alias, title, content)

    # 2) уведомляем админа и сразу же НЕ фоново, а inline делаем rebuild
    await message.reply("📥 Файл сохранён, индекс обновляется… Пожалуйста, подождите.")

    # ниже — синхронный вызов, но в executor, чтобы не блокировать event‑loop слишком долго
    refresh_chain()
    # 3) и наконец сообщаем об окончании
    await message.reply("✅ Индекс обновлён и готов к работе!")

    logging.info(f"Admin {message.from_user.id}: импортировал {alias}/{title}")


async def _rebuild_index(chat_id: int, bot: types.Bot):
    refresh_chain()
    await bot.send_message(chat_id, "✅ Индекс обновлён.")


# ────────────────────────────────────────────────
#   Кнопка «Удалить источник»
# ────────────────────────────────────────────────
async def del_btn_pressed(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    sources = await get_all_sources()
    if not sources:
        await message.reply("Источники не найдены.")
        return
    ikb = types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text=s, callback_data=f"del:{s}")]
                         for s in sources]
    )
    await message.reply("Выберите источник для удаления:", reply_markup=ikb)


@staticmethod
async def _delete_and_refresh(src: str, chat_id: int, bot: types.Bot):
    rows = await delete_site_data_by_source(src)
    refresh_chain()
    await bot.send_message(chat_id, f"🗑 Удалено {rows} записей источника «{src}»."
                                    "\n✅ Индекс обновлён.")


@staticmethod
async def confirm_delete(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    source = callback.data.split(":", 1)[1]
    await callback.answer("Удаляем…", show_alert=False)
    asyncio.create_task(
        _delete_and_refresh(source, callback.message.chat.id, callback.bot)
    )
    await callback.message.edit_text(f"Удаление «{source}» запущено.",
                                     reply_markup=None)


# ────────────────────────────────────────────────
#   /reply  и пересылки (без изменений)
# ────────────────────────────────────────────────
async def relay_admin_reply(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    src = message.reply_to_message
    if not src or not src.forward_from:
        return
    target_id = src.forward_from.id
    try:
        if message.text:
            await message.bot.send_message(target_id, message.text)
        elif message.document:
            await message.bot.send_document(target_id, message.document.file_id,
                                            caption=message.caption or "")
        elif message.photo:
            await message.bot.send_photo(target_id, message.photo[-1].file_id,
                                         caption=message.caption or "")
        else:
            await message.reply("❌ Только текст, фото, документы.")
            return
        await message.reply("✅ Отправлено пользователю.")
    except Exception as exc:
        await message.reply(f"❌ Ошибка пересылки: {exc}")


async def admin_reply(message: types.Message, command: CommandObject):
    if message.from_user.id not in ADMIN_IDS:
        return
    if not command.args:
        await message.reply("⚠️ /reply <user_id> <текст>")
        return
    try:
        uid_str, text = command.args.split(maxsplit=1)
        uid = int(uid_str)
    except ValueError:
        await message.reply("⚠️ Неверный формат.")
        return
    try:
        await message.bot.send_message(uid, text)
        await message.reply("✅ Отправлено.")
    except Exception as exc:
        await message.reply(f"❌ Не удалось: {exc}")


# ────────────────────────────────────────────────
#   РЕГИСТРАЦИЯ
# ────────────────────────────────────────────────
def register_admin_handlers(dp: Dispatcher):
    dp.message.register(cmd_panel, Command("panel"), flags={"block": True})
    dp.message.register(back_to_user, lambda m: m.text == BACK_BTN, flags={"block": True})
    dp.message.register(add_btn_pressed, lambda m: m.text == ADD_BTN, flags={"block": True})
    dp.message.register(del_btn_pressed, lambda m: m.text == DEL_BTN, flags={"block": True})

    dp.message.register(handle_admin_file, F.document, flags={"block": True})

    dp.callback_query.register(confirm_delete, lambda c: c.data and c.data.startswith("del:"))

    dp.message.register(admin_reply, Command("reply"), flags={"block": True})
    dp.message.register(relay_admin_reply, lambda m: m.reply_to_message is not None)