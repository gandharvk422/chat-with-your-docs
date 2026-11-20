import sys
from pathlib import Path

HERE = Path(__file__).parent    # backend/evals
BACKEND = HERE.parent           # backend
DOCS_DIR = HERE / "docs"
QUESTIONS = HERE / "questions.json"
OUT = HERE / "results.json"

sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(BACKEND / ".env")

from chain import build_chain
from embed import embed_and_store, reset_db
from hybrid import build_hybrid_reranker

TOP_N = 4
REFUSAL_PHRASE = "have enough information"

import json
from collections import defaultdict

def load_questions():
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    by_doc = defaultdict(list)
    for q in questions:
        by_doc[q["doc"]].append(q)
    
    return by_doc

def build_pipeline(path):
    """Same steps as /upload in main.py, but it also remembers the retrieved chunks."""
    vectorstore, chunks = embed_and_store(str(path))
    rerank = build_hybrid_reranker(chunks, vectorstore)
    
    seen = {"docs": []}     # filled in every time a question is related
    
    def retrieve(question):
        docs = [doc for _, doc in rerank(question, top_n = TOP_N)]
        seen["docs"] = docs     # remember what the LLM is about to see
        return docs
    
    chain = build_chain(retrieve)
    return vectorstore, chunks, chain, seen

# Temporary check, delete later
if __name__ == '__main__':
    reset_db()
    vectorstore, chunks, chain, seen = build_pipeline(DOCS_DIR / "test.pdf")
    print("chunks created:", len(chunks))
    
    result = chain.invoke("What degree did Gandharv Kulkarni earn?")
    print("answer:", result["answer"])
    print("source:", result["sources"])
    print("chunks the LLM saw:", len(seen["docs"]))
    print("first chunk starts:", seen["docs"][0].page_content[:100])