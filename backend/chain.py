import os

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_groq import ChatGroq

RAG_PROMPT = ChatPromptTemplate.from_template(
    """You are a helpful AI assistant.
Answer the question using ONLY the context provided below.
If the answer is not in the context, say "I don't have enough information in my knowledge base."
Do not add a list of sources at the end; the app shows the sources separately.

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

def sources_from_docs(docs):
    """Unique [{"file": ..., "page": ...}] list. `page` is left out when unknown."""
    seen, sources = set(), []
    for d in docs:
        file = os.path.basename(d.metadata.get("source", "unknown"))
        page = d.metadata.get("page")
        page = page + 1 if page is not None else None
        
        if (file, page) in seen:
            continue
        seen.add((file, page))
        item = {"file": file}
        if page is not None:
            item["page"] = page
        sources.append(item)
    return sources


def build_chain(retrieve):
    """
    Build the RAG chain from any retriever (plain vector retriever now,
    a hybrid one later). Needs GROQ_API_KEY in the environment.
    """
    llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
    answer_chain = RAG_PROMPT | llm | StrOutputParser()
    
    def run(question):
        docs = retrieve(question)
        answer = answer_chain.invoke(
            {"context": format_docs(docs), "question": question}
        )
        
        if "have enough information" in answer.lower():
            return {"answer": answer, "sources": []}
        
        return {"answer": answer, "sources": sources_from_docs(docs)}

    return RunnableLambda(run)