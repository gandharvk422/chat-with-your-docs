import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.embeddings import HuggingFaceEmbeddings
from ragas.metrics.collections import AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness
from statistics import mean

HERE = Path(__file__).parent
load_dotenv(HERE.parent / ".env")

RESULTS = HERE / "results_baseline.json"
OUT = HERE / "scores_baseline.json"
METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]

client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ["GROQ_API_KEY"],
    max_retries=6
)

JUDGE_MODEL = "openai/gpt-oss-120b"

judge = llm_factory(
    JUDGE_MODEL,
    provider="openai",
    client=client,
    temperature=0,
    max_tokens=8192,
)
print("judge model:", JUDGE_MODEL)

embeddings = HuggingFaceEmbeddings(model = "BAAI/bge-small-en-v1.5")

faithfulness = Faithfulness(llm = judge)
precision = ContextPrecision(llm = judge)
recall = ContextRecall(llm = judge)
relevancy = AnswerRelevancy(llm = judge, embeddings = embeddings)

class DailyLimit(Exception):
    pass

def score_row(r):
    q, a, ctx, gt = r["question"], r["answer"], r["contexts"], r["ground_truth"]
    answered = not r["refused"]
    
    calls = {
        "context_precision": lambda: precision.score(user_input = q, reference = gt, retrieved_contexts = ctx),
        "context_recall": lambda: recall.score(user_input = q, reference = gt, retrieved_contexts = ctx)
    }
    
    if answered:    # these two need a real answer to judge
        calls["faithfulness"] = lambda: faithfulness.score(user_input = q, response = a, retrieved_contexts = ctx)
        calls["answer_relevancy"] = lambda: relevancy.score(user_input = q, response = a)
        
    out = {"faithfulness": None, "answer_relevancy": None}
    for name, call in calls.items():
        try:
            out[name] = round(call().value, 3)
        except Exception as e:
            if "tokens per day" in str(e):
                raise DailyLimit()
            print(f"    {name} failed: {type(e).__name__}: {e}")
            out[name] = None
    
    return out

def print_summary(scores):
    def line(label, rows):
        parts = []
        for m in METRICS:
            vals = [r[m] for r in rows if r[m] is not None]
            parts.append(f"{m} = {mean(vals):.2f} (n = {len(vals)})" if vals else f"{m} = -")
        print(f"{label:42} " + "  ".join(parts))
    
    print()
    line("ALL", scores)
    for t in ("lookup", "reasoning"):
        group = [s for s in scores if s["type"] == t]
        if group:
            line(t, group)
    
    print()
    for d in dict.fromkeys(s["doc"] for s in scores):
        line(d, [s for s in scores if s["doc"] == d])
    
    failed = [
        s["id"] for s in scores
        if s["context_precision"] is None or s["context_recall"] is None
        or (not s["refused"] and (s["faithfulness"] is None or s["answer_relevancy"] is None))
    ]
    print("\nrows with failed metrics:", failed or "none")
    
def is_complete(s):
    needed = ["context_precision", "context_recall"]
    if not s["refused"]:
        needed += ["faithfulness", "answer_relevancy"]
    
    return all(s[m] is not None for m in needed)
    
def main():
    results = json.loads(RESULTS.read_text(encoding="utf-8"))
    results = [r for r in results if r["type"] != "unanswerable"]
    
    done = {}
    
    if OUT.exists():
        done = {s["id"]: s for s in json.loads(OUT.read_text(encoding = "utf-8"))}
    
    try:
        for n, r in enumerate(results, 1):
            if r["id"] in done and is_complete(done[r["id"]]):
                continue    # already scored in an earlier run
            print(f"[{n}/{len(results)}] {r["id"]}")
            done[r["id"]] = {
                "id": r["id"], "doc": r["doc"], "type": r["type"], "refused": r["refused"], **score_row(r)
            }
            OUT.write_text(json.dumps(list(done.values()), indent = 2), encoding = "utf-8")
    except DailyLimit:
        print("\nDaily Groq taken limit reached. Progress is saved; run again later to continue.")
    
    print_summary(list(done.values()))

if __name__ == '__main__':
    main()