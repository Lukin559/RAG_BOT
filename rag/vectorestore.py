import os
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain_chroma import Chroma

from .config import DATA_PATH, OPENAI_API_KEY

def load_documents_from_txt(file_path: str) -> list:
    """Загружаем текст из файла и превращаем в список Document, чтобы LangChain мог с ними работать."""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Разбиваем текст на части для более точного поиска
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=100, 
        separators=["\n\n", "\n", ".", "!", "?"]
    )
    
    chunks = text_splitter.split_text(text)
    docs = [Document(page_content=chunk) for chunk in chunks]
    return docs

def create_or_load_vectorstore(persist_directory: str = "vectorstore") -> Chroma:
    """
    Создает или подгружает существующее векторное хранилище (Chroma).
    Если хранилища нет, создаст с нуля.
    """
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

    if not os.path.exists(persist_directory):
        os.makedirs(persist_directory)

    # Проверяем, есть ли уже файлы Chroma
    if len(os.listdir(persist_directory)) > 0:
        # Если есть, подгружаем
        vectorstore = Chroma(collection_name="my_collection",
                             persist_directory=persist_directory,
                             embedding_function=embeddings)
    else:
        # Иначе — создаем
        docs = load_documents_from_txt(DATA_PATH)
        vectorstore = Chroma.from_documents(
            documents=docs,
            embedding=embeddings,
            collection_name="my_collection",
            persist_directory=persist_directory
        )
    
    return vectorstore
