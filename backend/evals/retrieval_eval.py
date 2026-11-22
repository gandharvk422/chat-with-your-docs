import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))

from embed import embed_and_store, reset_db
from hybrid import build_hybrid_reranker
from run_evals import DOCS_DIR, load_questions

NS = (4, 6)      # the top_n values to compare
POOL = 30           # ask for everything the retriever found (above 10 at most)
STOP = {"about", "which", "their", "there", "these", "those", "where", "after",
        "before", "being", "other", "would", "could", "between", "because",
        "while", "every", "using", "since", "first", "three", "four", "five"}

CONFIGS = {
    "baseline":   {"CHUNK_SIZE": "800", "CHUNK_OVERLAP": "100", "RETRIEVER_K": "5"},
    "k10":        {"CHUNK_SIZE": "800", "CHUNK_OVERLAP": "100", "RETRIEVER_K": "10"},
    "pdfium":     {"PDF_LOADER": "pdfium", "CHUNK_SIZE": "800", "CHUNK_OVERLAP": "100", "RETRIEVER_K": "5"},
    "pdfium_k10": {"PDF_LOADER": "pdfium", "CHUNK_SIZE": "800", "CHUNK_OVERLAP": "100", "RETRIEVER_K": "10"},
}

def key_terms(text):
    return {w for w in re.findall(r"[a-z]{5,}", text.lower()) if w not in STOP}

def term_recall(ground_truth, contexts):
    terms = key_terms(ground_truth)
    if not terms:
        return None
    blob = " ".join(contexts).lower()
    return sum(t in blob for t in terms) / len(terms)

def run_config(env, only):
    os.environ.pop("PDF_LOADER", None)  # start every config with the default loader
    os.environ.update(env)  # takes effect when embed_and_store / build_hybrid_reranker run
    scores, sizes, sizes6 = {}, [], []
    for doc_name, qs in load_questions().items():
        if only and only.lower() not in doc_name.lower():
            continue
        qs = [q for q in qs if q["type"] != "unanswerable"]
        vectorstore, chunks = embed_and_store(str(DOCS_DIR / doc_name))
        rerank = build_hybrid_reranker(chunks, vectorstore)
        for q in qs:
            texts = [d.page_content for _, d in rerank(q["question"], top_n = POOL)]
            row = {n: term_recall(q["answer"], texts[:n]) for n in NS}
            row["pool"] = term_recall(q["answer"], texts)
            if row["pool"] is None:
                continue
            scores[q["id"]] = row
            sizes.append(len("".join(texts[:4])))   # how much text the LLM gets at top_n = 4
            sizes6.append(len("".join(texts[:6])))   # how much text the LLM gets at top_n = 6
        try:
            vectorstore.delete_collection()
        except Exception:
            pass
    
    return scores, sum(sizes) / len(sizes)

def main(only = None):
    reset_db()
    results, chars = {}, {}
    
    for name, env in CONFIGS.items():
        print(f"\n##### config: {name} {env}")
        results[name], chars[name] = run_config(env, only)
        
    names = list(CONFIGS)
    print("\nterm recall at top_n = 4, per question")
    print("     " + "  ".join(f"{n:>10}" for n in names))
    for qid in results["baseline"]:
        print(f"{qid:6}" + "  ".join(f"{results[n][qid][4]:10.2f}" for n in names))
    
    print()
    for label, key in (("avg top_n=4", 4), ("avg top_n=6", 6), ("avg pool", "pool")):
        vals = "  ".join(
            f"{sum(r[key] for r in results[n].values()) / len(results[n]):10.3f}" for n in names
        )
        print(f"{label:12}" + vals)
    print(f"{'chars @ n=4':12}" + "  ".join(f"{chars[n]:10.0f}" for n in names))
    
if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)