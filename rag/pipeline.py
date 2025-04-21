# rag/pipeline.py
import logging
from typing import Optional

from langchain.chains import ConversationalRetrievalChain
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory

from .vectorestore import create_fresh_vectorstore
from .config import OPENAI_API_KEY, LLM_MODEL_NAME, TEMPERATURE

# единственный глобальный объект
rag_chain: Optional[ConversationalRetrievalChain] = None

def _make_chain(vs) -> ConversationalRetrievalChain:
    """
    Создаёт новую RAG‑цепочку на основе переданного векторстора.
    """
    llm = ChatOpenAI(
        openai_api_key=OPENAI_API_KEY,
        model_name=LLM_MODEL_NAME,
        temperature=TEMPERATURE,
    )
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        output_key="answer",
    )
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vs.as_retriever(search_kwargs={"k": 5}),
        memory=memory,
        return_source_documents=True,
        output_key="answer",
    )
    return chain

def get_rag_chain() -> ConversationalRetrievalChain:
    """
    При первом вызове создаёт RAG‑цепочку.
    Повторные — возвращают уже готовую.
    """
    global rag_chain
    if rag_chain is None:
        logging.info("🔄  Создаём RAG‑цепочку впервые…")
        vs = create_fresh_vectorstore()
        rag_chain = _make_chain(vs)
        logging.info("✅  RAG‑цепочка создана")
    return rag_chain

def refresh_chain() -> None:
    """
    Полностью пересоздаёт векторное хранилище и RAG‑цепочку.
    Вызывайте его после любых изменений данных.
    """
    global rag_chain
    logging.info("🔄  Пересоздаём векторный индекс и RAG‑цепочку…")
    vs = create_fresh_vectorstore()
    rag_chain = _make_chain(vs)
    logging.info("✅  RAG‑цепочка обновлена")

def get_answer(question: str, source: str) -> str:
    """
    Возвращает ответ на вопрос, фильтруя по метаданным source.
    """
    chain = get_rag_chain()
    # обновляем фильтр на источник
    chain.retriever.search_kwargs["filter"] = {"source": source}
    result = chain({"question": question})
    docs = result.get("source_documents") or []
    return result["answer"] if docs else "Не нашли информацию по вашему запросу."