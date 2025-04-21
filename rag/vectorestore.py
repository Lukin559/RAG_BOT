# rag/vectorestore.py
from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import List

from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

from .config import OPENAI_API_KEY

DB_PATH = Path("data.db")
BASE_DIR = Path("vectorstore")          # «актуальный» индекс живёт здесь


def _load_docs() -> List[Document]:
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT source, content FROM site_data").fetchall()
    conn.close()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1_000, chunk_overlap=100,
        separators=["\n\n", "\n", ".", "!", "?"],
    )
    docs = []
    for source, content in rows:
        for chunk in splitter.split_text(content):
            docs.append(Document(page_content=chunk, metadata={"source": source}))
    return docs


def _build_index(dir_: Path) -> Chroma:
    docs = _load_docs()
    print(f"📄  Строим индекс в {dir_}. Документов: {len(docs)}")

    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    return Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        collection_name="rag_collection",
        persist_directory=str(dir_),
    )


def create_fresh_vectorstore() -> Chroma:
    """
    1. Создаёт индекс в уникальном временном каталоге.
    2. Удаляет старый BASE_DIR (если был) и «переименовывает» новый.
    3. Возвращает готовый объект Chroma, уже читающий из BASE_DIR.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="vs_tmp_"))
    vs_tmp = _build_index(tmp_dir)      # строим «песочницу»

    # ——> атомарная подмена каталога
    if BASE_DIR.exists():
        shutil.rmtree(BASE_DIR)
    tmp_dir.rename(BASE_DIR)

    # подключаемся к «новому официальному» каталогу
    print("✅  Индекс пересобран")
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    return Chroma(
        collection_name="rag_collection",
        persist_directory=str(BASE_DIR),
        embedding_function=embeddings,
    )