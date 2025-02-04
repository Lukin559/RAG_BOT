from langchain.chains import ConversationalRetrievalChain
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory

from .config import OPENAI_API_KEY, LLM_MODEL_NAME, TEMPERATURE
from .vectorestore import create_or_load_vectorstore

def get_rag_chain():
    """Создаём цепочку RAG на базе ConversationalRetrievalChain."""
    vectorstore = create_or_load_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

    llm = ChatOpenAI(
        openai_api_key=OPENAI_API_KEY,
        model_name=LLM_MODEL_NAME,
        temperature=TEMPERATURE
    )

    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        output_key='answer'
    )

    # Явно указываем, что ключ, который будет «основным» выходом — "answer"
    qa_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        return_source_documents=True,
        output_key="answer"  # <-- важно!
    )
    return qa_chain


def get_answer(question: str, chain) -> str:
    """Вызывает RAG-цепочку и получает ответ. Если контекст пуст — сообщаем, что не нашли информацию."""

    result = chain.invoke({"question": question})
    

    answer = result["answer"]
    source_docs = result["source_documents"]

    if not source_docs:
        return "Не нашли информацию по вашему запросу."
    
    return answer
