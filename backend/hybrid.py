from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from sentence_transformers import CrossEncoder
import os

CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_cross_encoder = None

def get_cross_encoder():
    """Load the cross-encoder once and reuse it afterwards."""
    global _cross_encoder
    if _cross_encoder is None:
        _cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL)
    return _cross_encoder


def build_hybrid_reranker(chunks, vectorstore):
    """
    Build the hybrid (BM25 + vector) retriever and the cross-encoder ONCE.
    Returns a function: hybrid_rerank(query, top_n) -> [(score, doc), ...]
    """
    k = int(os.getenv("RETRIEVER_K", "5"))
    # Vector retriever from the existing ChromaDB
    vector_retriever = vectorstore.as_retriever(search_kwargs={"k": k})

    # BM25 keyword retriever built from the chunks
    bm25_retriever = BM25Retriever.from_documents(chunks)
    bm25_retriever.k = k

    # Hybrid: 40% BM25 + 60% vector similarity
    hybrid_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, vector_retriever],
        weights=[0.4, 0.6],
    )

    cross_encoder = get_cross_encoder()

    def hybrid_rerank(query, top_n=3):
        # 1. Hybrid retrieval
        candidates = hybrid_retriever.invoke(query)

        # Deduplicate by content prefix
        seen, unique = set(), []
        for doc in candidates:
            key = doc.page_content[:100]
            if key not in seen:
                seen.add(key)
                unique.append(doc)

        # 2. Rerank with cross-encoder (higher score = more relevant)
        pairs = [[query, doc.page_content] for doc in unique]
        scores = cross_encoder.predict(pairs)
        ranked = sorted(zip(scores, unique), key=lambda x: x[0], reverse=True)
        return ranked[:top_n]

    return hybrid_rerank