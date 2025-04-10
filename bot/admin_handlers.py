# admin_handlers.py
from aiogram import Dispatcher, types
from io import BytesIO
from db.db_data import add_site_data
from aiogram import F, types

# Список ID администраторов (замените на реальные ID)
ADMIN_IDS = [123456789]

async def handle_admin_file(message: types.Message):
    """
    Обработка текстовых файлов, отправленных администратором.
    Файл будет сохранен в БД, где:
    - source: "admin_{user_id}"
    - title: имя файла
    - content: содержимое файла
    """
    if message.from_.id not in ADMIN_IDS:
        await message.reply("У вас нет доступа к этой команде.")
        return

    if not message.document:
        await message.reply("Пожалуйста, отправьте текстовый файл.")
        return

    # Проверяем mime-type (опционально)
    if "text" not in message.document.mime_type:
        await message.reply("Файл должен быть текстовым.")
        return

    # Скачиваем документ
    file_info = await message.bot.get_file(message.document.file_id)
    file_bytes = await message.bot.download_file(file_info.file_path)
    
    # Если file_bytes возвращается как BinaryIO, читаем содержимое
    content = file_bytes.read().decode("utf-8")
    
    # Используем имя файла как заголовок
    title = message.document.file_name
    # Указываем source, например, "admin_<user_id>"
    source = f"admin_{message.from_.id}"
    
    await add_site_data(source, title, content)
    await message.reply("Файл успешно добавлен в базу данных!")

def register_admin_handlers(dp: Dispatcher):
    # Регистрируем обработчик для документов
   dp.message.register(handle_admin_file, F.document)