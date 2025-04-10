# rag/vectorestore.py
import os
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from .config import DATA_PATH, OPENAI_API_KEY
from langchain.docstore.document import Document
import sqlite3
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Функция, читающая документы из текстового файла (уже реализована)
def load_documents_from_txt(file_path: str) -> list:
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    from langchain.text_splitter import RecursiveCharacterTextSplitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=100, 
        separators=["\n\n", "\n", ".", "!", "?"]
    )
    
    chunks = text_splitter.split_text(text)
    docs = [Document(page_content=chunk) for chunk in chunks]
    return docs

def load_documents_from_db(db_path: str = "data.db") -> list:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id, source, title, content, created_at FROM site_data")
    rows = c.fetchall()
    conn.close()

    docs = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        separators=["\n\n", "\n", ".", "!", "?"]
    )
    
    for row in rows:
        content = row[3]
        chunks = text_splitter.split_text(content)
        docs.extend([Document(page_content=chunk) for chunk in chunks])
    
    return docs

def create_or_load_vectorstore(persist_directory: str = "vectorstore", use_db: bool = False) -> Chroma:
    """
    Создает или подгружает существующее векторное хранилище (Chroma).
    Если хранилище отсутствует, создает его на основе документов,
    загруженных либо из текстового файла, либо из базы данных.
    """
    from langchain_openai import OpenAIEmbeddings
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

    if not os.path.exists(persist_directory):
        os.makedirs(persist_directory)

    # Если в хранилище уже есть файлы, подгружаем существующее хранилище.
    if len(os.listdir(persist_directory)) > 0:
        vectorstore = Chroma(
            collection_name="my_collection",
            persist_directory=persist_directory,
            embedding_function=embeddings
        )
    else:
        # Выбираем источник документов.
        if use_db:
            docs = load_documents_from_db()
        else:
            docs = load_documents_from_txt(DATA_PATH)
        vectorstore = Chroma.from_documents(
            documents=docs,
            embedding=embeddings,
            collection_name="my_collection",
            persist_directory=persist_directory
        )
    
    return vectorstore