import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent    # backend/evals
BACKEND = HERE.parent           # backend
DOCS_DIR = HERE / "docs"
QUESTIONS = HERE / "questions.json"
TOP_N = int(os.getenv("TOP_N", "4"))
EXP = os.getenv("EXP_NAME")
OUT = HERE / (f"results_{EXP}.json" if EXP else "results.json")

SETTINGS = (f"TOP_N={TOP_N} RETRIEVER_K={os.getenv('RETRIEVER_K', '5')} "
            f"CHUNK={os.getenv('CHUNK_SIZE', '800')}/{os.getenv('CHUNK_OVERLAP', '100')} "
            f"PDF_LOADER={os.getenv('PDF_LOADER', 'pypdf')}")

sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(BACKEND / ".env")

from chain import build_chain
from embed import embed_and_store, reset_db
from hybrid import build_hybrid_reranker

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

class DailyLimit(Exception):
    pass

def ask(chain, seen, question, tries = 4):
    """Ask one question. Retries with a growing pause if the call fails."""
    for attempt in range(tries):
        try:
            seen["docs"] = []   # clear leftovers from the previous question
            result = chain.invoke(question)
            contexts = [d.page_content for d in seen["docs"]]
            result["retrieved_pages"] = sorted(
                {d.metadata["page"] + 1 for d in seen["docs"]
                 if d.metadata.get("page") is not None}
            )
            return result, contexts
        except Exception as e:
            if "tokens per day" in str(e):
                raise DailyLimit()
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
        "sources": result["sources"],
        "retrieved_pages": result.get("retrieved_pages", []),
        "settings": SETTINGS,
    }
    
def add_refusal_check(row):
    """Adds two fields: did the bot refuse, and was that the right call?"""
    row["error"] = row["answer"].startswith("ERROR")
    refused = REFUSAL_PHRASE in row["answer"].lower()
    should_refuse = row["type"] == "unanswerable"
    row["refused"] = refused
    row["refusal_correct"] = None if row["error"] else refused == should_refuse
    return row

def expected_pages(reference):
    """'PDF pages 163-164' -> {163, 164}. 'Education' (no page) -> None."""
    m = re.search(r"pages?\s+(\d+)(?:\s*-\s*(\d+))?", reference)
    if not m:
        return None
    start = int(m.group(1))
    end = int(m.group(2) or start)
    return set(range(start, end + 1))

def add_page_check(row):
    """page_hit = True/False for PDF questions, None when there is nothing to check."""
    pages = None if row["type"] == "unanswerable" or row["error"] else expected_pages(row["reference"])
    if pages is None:
        row["page_hit"] = None
    else:
        row["page_hit"] = bool(pages & set(row["retrieved_pages"]))
    
    return row

def line(label, rs):
    """One summary line for a group of rows."""
    errors = sum(r["error"] for r in rs)
    rs = [r for r in rs if not r["error"]]
    refusal_ok = sum(r["refusal_correct"] for r in rs)
    false_refusals = sum(r["refused"] and r["type"] != "unanswerable" for r in rs)
    hallucinations = sum((not r["refused"] and r["type"] == "unanswerable" for r in rs))
    paged = [r for r in rs if r["page_hit"] is not None]
    page = f"{sum(r['page_hit'] for r in paged)}/{len(paged)}" if paged else "-"
    print(f"{label:42} n={len(rs):2}    refusal={refusal_ok}/{len(rs)}  "
          f"false_refusals={false_refusals}     hallucinations={hallucinations}     page_hit={page}  errors={errors}")

def print_summary(rows):
    print()
    line("ALL", rows)
    for t in ("lookup", "reasoning", "unanswerable"):
        group = [r for r in rows if r["type"] == t]
        if group:
            line(t, group)
    print()
    for d in dict.fromkeys(r["doc"] for r in rows):     # unique docs, in order
        line(d, [r for r in rows if r["doc"] == d])
    
def load_saved():
    if not OUT.exists():
        return {}
    return {r["id"]: r for r in json.loads(OUT.read_text(encoding = "utf-8"))}

def check_settings():
    old = {r["settings"] for r in load_saved().values() if r.get("settings")}
    if old in old != {SETTINGS}:
        sys.exit(f"{OUT.name} was made with different settings:\n  {old}\n"
                 f"now:\n  {SETTINGS}\nUse a new EXP_NAME or delete the file.")

def save_results(rows):
    saved = load_saved()
    for r in rows:
        old = saved.get(r["id"])
        if r["answer"].startswith("ERROR") and old and not old["answer"].startswith("ERROR"):
            continue
        saved[r["id"]] = r
    OUT.write_text(json.dumps(list(saved.values()), indent = 2, ensure_ascii = False), encoding = "utf-8")
    
def main(only = None):
    reset_db()
    print("settings:", SETTINGS)
    check_settings()
    done = {i for i, r in load_saved().items() if not r["answer"].startswith("ERROR")} if EXP else set()
    rows = []
    
    try:
        for doc_name, qs in load_questions().items():
            if only and only.lower() not in doc_name.lower():
                continue    # skipping documents that weren't asked to run
            
            path = DOCS_DIR / doc_name
            
            if not path.exists():
                print(f"!! file missing, skipping: {doc_name}")
                continue
            
            qs = [q for q in qs if q["id"] not in done]
            if not qs:
                print(f"\n=== {doc_name}: already done, skipping ===")
                continue
            
            print(f"\n=== {doc_name} ({len(qs)} questions) ===")
            print("embedding the document...")
            vectorstore, chunks, chain, seen = build_pipeline(path)
            print(f"{len(chunks)} chunks ready")
            
            
            for q in qs:
                result, contexts = ask(chain, seen, q["question"])
                rows.append(add_page_check(add_refusal_check(build_row(q, result, contexts))))
                print(f"    {q['id']} [{q['type']}] done")
            
            try:
                vectorstore.delete_collection()
            except DailyLimit:
                print("\nGroq daily token limit reached. Saving what finished.")
            
            save_results(rows)
    except DailyLimit:
        print("\nGroq daily token limit reached. Saving what finished.")
        
    save_results(rows)
    print(f"\nSaved {len(rows)} rows to {OUT}")
    print_summary(rows)

if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else None

    if arg == "check":
        rows = json.loads(OUT.read_text(encoding="utf-8"))
        rows = [add_page_check(add_refusal_check(r)) for r in rows]
        print_summary(rows)
    else:
        main(only=arg)