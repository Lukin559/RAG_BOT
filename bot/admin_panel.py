# bot/admin_panel.py
from __future__ import annotations

import logging
from aiogram import Router, types, F
from aiogram.filters import Command, CommandStart
from aiogram.enums import ContentType

from db.db_data import add_site_data, delete_site_data_by_source, get_all_sources
from rag.pipeline import refresh_chain

ADMIN_IDS = {123456789, 504895191}

router = Router(name="admin-panel")

ADD_BTN = "➕ Добавить источник"
DEL_BTN = "🗑 Удалить источник"

# временное хранилище «ждём файл» {admin_id: True}
_wait_file: dict[int, bool] = {}


# ────────────────────────────────────────────────
#   показываем две постоянные кнопки
# ────────────────────────────────────────────────
def admin_kb() -> types.ReplyKeyboardMarkup:
    return types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=ADD_BTN)],
                  [types.KeyboardButton(text=DEL_BTN)]],
        resize_keyboard=True
    )


@router.message(CommandStart())
async def adm_start(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("Панель администратора:", reply_markup=admin_kb())


# ────────────────────────────────────────────────
#   «Добавить источник»
# ────────────────────────────────────────────────
@router.message(lambda m: m.text == ADD_BTN)
async def add_source_button(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    _wait_file[message.from_user.id] = True
    await message.answer("Пришлите .txt‑файл — его имя станет alias источника.")


@router.message(lambda m: m.document is not None)
async def handle_admin_file(message: types.Message):
    uid = message.from_user.id
    if uid not in ADMIN_IDS or not _wait_file.pop(uid, False):
        return  # файл нам не нужен

    # проверяем текст
    if not message.document.mime_type.startswith("text"):
        await message.reply("⚠️ Нужен именно .txt‑файл.")
        return

    # качаем
    file = await message.bot.get_file(message.document.file_id)
    raw = await message.bot.download_file(file.file_path)
    content_bytes = raw.read()
    for enc in ("utf-8", "cp1251", "latin-1"):
        try:
            content = content_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        await message.reply("Не удалось декодировать файл.")
        return

    alias = message.document.file_name.rsplit(".", 1)[0]
    await add_site_data(alias, alias, content)
    refresh_chain()

    await message.reply(f"✅ Источник «{alias}» добавлен.",
                        reply_markup=admin_kb())
    logging.info(f"Admin {uid}: добавил {alias}")


# ────────────────────────────────────────────────
#   «Удалить источник»
# ────────────────────────────────────────────────
@router.message(lambda m: m.text == DEL_BTN)
async def del_source_button(message: types.Message):
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


@router.callback_query(lambda c: c.data and c.data.startswith("del:"))
async def confirm_delete(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    src = callback.data.split(":", 1)[1]
    rows = await delete_site_data_by_source(src)
    refresh_chain()
    await callback.answer()
    await callback.message.edit_text(f"🗑 Удалено {rows} записей источника «{src}».",
                                     reply_markup=None)
    logging.info(f"Admin {callback.from_user.id}: удалил {src}")