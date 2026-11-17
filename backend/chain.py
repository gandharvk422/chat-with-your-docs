import os

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_groq import ChatGroq

RAG_PROMPT = ChatPromptTemplate.from_template(
    """You are a helpful AI assistant.
Answer the question using ONLY the context provided below.
If the answer is not in the context, say "I don't have enough information in my knowledge base."
Always cite which source(s) you used at the end of your answer.

Context:
{context}

Question: {question}

Answer:"""
)


def format_docs(docs):
    """Turn retrieved chunks into one context string, with file name and page."""
    parts = []
    for d in docs:
        name = os.path.basename(d.metadata.get("source", "unknown"))
        page = d.metadata.get("page")
        label = f"{name}, page {page + 1}" if page is not None else name
        parts.append(f"[Source: {label}]\n{d.page_content}")
    return "\n\n---\n\n".join(parts)


def build_chain(retriever):
    """
    Build the RAG chain from any retriever (plain vector retriever now,
    a hybrid one later). Needs GROQ_API_KEY in the environment.
    """
    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)

    return (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | RAG_PROMPT
        | llm
        | StrOutputParser()
    )