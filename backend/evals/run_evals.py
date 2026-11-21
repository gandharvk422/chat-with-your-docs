import sys
import time
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

def ask(chain, seen, question, tries = 4):
    """Ask one question. Retries with a growing pause if the call fails."""
    for attempt in range(tries):
        try:
            seen["docs"] = []   # clear leftovers from the previous question
            result = chain.invoke(question)
            contexts = [d.page_content for d in seen["docs"]]
            return result, contexts
        except Exception as e:
            if attempt == tries - 1:
                return {"answer": f"ERROR: {e}", "sources": []}, []
            time.sleep(2 ** (attempt + 1))      # wait 2 secs, then 4 secs, and then 8 secs
            
def build_row(q, result, contexts):
    """Everything about one question, in one dictionary."""
    return {
        "id": q["id"],
        "doc": q["doc"],
        "type": q["type"],
        "question": q["question"],
        "answer": result["answer"],
        "contexts": contexts,
        "ground_truth": q["answer"],
        "reference": q["reference"],
        "sources": result["sources"]
    }
    
def save_results(rows):
    OUT.write_text(json.dumps(rows, indent = 2, ensure_ascii = False), encoding = "utf-8")
    
def main(only = None):
    reset_db()
    rows = []
    
    for doc_name, qs in load_questions().items():
        if only and only.lower() not in doc_name.lower():
            continue    # skipping documents that weren't asked to run
        
        path = DOCS_DIR / doc_name
        
        if not path.exists():
            print(f"!! file missing, skipping: {doc_name}")
            continue
        
        print(f"\n=== {doc_name} ({len(qs)} questions) ===")
        print("embedding the document...")
        vectorstore, chunks, chain, seen = build_pipeline(path)
        print(f"{len(chunks)} chunks ready")
        
        
        for q in qs:
            result, contexts = ask(chain, seen, q["question"])
            rows.append(build_row(q, result, contexts))
            print(f"    {q['id']} [{q['type']}] done")
        
        try:
            vectorstore.delete_collection()
        except Exception:
            pass    # cleanup only; not worth stopping the run
        
        save_results(rows)
        
    print(f"\nSaved {len(rows)} rows to {OUT}")

if __name__ == '__main__':
    main(only = sys.argv[1] if len(sys.argv) > 1 else None)