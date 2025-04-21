# db/db_data.py
import aiosqlite
from datetime import datetime

DATABASE_PATH = "data.db"  # имя файла базы данных

async def init_db_documents():
    """Инициализирует таблицу для хранения данных из сайтов."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS site_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                title TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.commit()

async def add_site_data(source: str, title: str, content: str):
    """Добавляет новую запись в таблицу site_data."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            INSERT INTO site_data (source, title, content, created_at)
            VALUES (?, ?, ?, ?)
        ''', (source, title, content, datetime.utcnow().isoformat()))
        await db.commit()

async def get_all_sources():
    """Возвращает список уникальных источников (source) из таблицы site_data."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT DISTINCT source FROM site_data")
        rows = await cursor.fetchall()
        # Вернём список источников (если строка пуста — не добавим)
        return [row[0] for row in rows]

async def delete_site_data_by_source(source: str):
    """
    Удаляет все записи из site_data с указанным source.
    Возвращает количество удалённых строк.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM site_data WHERE source = ?",
            (source,)
        )
        await db.commit()
        return cursor.rowcount