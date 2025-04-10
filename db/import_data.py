# db/import_data.py
import os
import asyncio
from db_data import init_db_documents, add_site_data

# Каталог, в котором лежат папки с данными.
DATA_DIR = "data"

async def import_all_data():
    # Инициализируем таблицу, если ещё не создана.
    await init_db_documents()
    
    # Проходим по всем элементам в каталоге DATA_DIR.
    for entry in os.listdir(DATA_DIR):
        subdir = os.path.join(DATA_DIR, entry)
        # Если элемент — папка, считаем её именем источника.
        if os.path.isdir(subdir):
            source = entry  # имя папки будет использоваться как source
            # Проходим по файлам внутри папки.
            for filename in os.listdir(subdir):
                if filename.endswith(".txt"):
                    file_path = os.path.join(subdir, filename)
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    # Название файла (без расширения) используем как title.
                    title = os.path.splitext(filename)[0]
                    await add_site_data(source, title, content)
                    print(f"Импортирован файл: {source}/{filename}")

if __name__ == "__main__":
    asyncio.run(import_all_data())