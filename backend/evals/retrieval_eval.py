import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))

from embed import embed_and_store, reset_db
from hybrid import build_hybrid_reranker
from run_evals import DOCS_DIR, load_questions

NS = (4, 6, 8)      # the top_n values to compare
POOL = 10           # ask for everything the retriever found (above 10 at most)
STOP = {"about", "which", "their", "there", "these", "those", "where", "after",
        "before", "being", "other", "would", "could", "between", "because",
        "while", "every", "using", "since", "first", "three", "four", "five"}


def key_terms(text):
    return {w for w in re.findall(r"[a-z]{5,}", text.lower()) if w not in STOP}

def term_recall(ground_truth, contexts):
    terms = key_terms(ground_truth)
    if not terms:
        return None
    blob = " ".join(contexts).lower()
    return sum(t in blob for t in terms) / len(terms)


def main(only = None):
    reset_db()
    totals = {n: [] for n in NS}
    totals["pool"] = []
    
    for doc_name, qs in load_questions().items():
        if only and only.lower() not in doc_name.lower():
            continue
        qs = [q for q in qs if q["type"] != "unanswerable"]
        print(f"\n=== {doc_name} ===")
        vectorstore, chunks = embed_and_store(str(DOCS_DIR / doc_name))
        rerank = build_hybrid_reranker(chunks, vectorstore)
        
        for q in qs:
            ranked = rerank(q["question"], top_n = POOL)
            texts = [doc.page_content for _, doc in ranked]
            scores = {n: term_recall(q["answer"], texts[:n]) for n in NS}
            scores["pool"] = term_recall(q["answer"], texts)
            if scores["pool"] is None:
                print(f"    {q["id"]}   (no key terms, skipped)")
                continue
            
            for k, v in scores.items():
                totals[k].append(v)
            cells = "  ".join(f"n = {n}: {scores[n]:.2f}" for n in NS)
            print(f"    {q["id"]}   {cells}     pool({len(texts)}): {scores["pool"]:.2f}")
        
        try:
            vectorstore.delete_collection()
        except Exception:
            pass
        
    print("\nAVERAGE term recall")
    for k, v in totals.items():
        if v:
            label = "whole pool" if k == "pool" else f"top_n = {k}"
            print(f"    {label:12} {sum(v) / len(v):.3f}    (questions: {len(v)})")

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)