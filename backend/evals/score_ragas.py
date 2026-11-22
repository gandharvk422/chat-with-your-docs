import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.embeddings import HuggingFaceEmbeddings
from ragas.metrics.collections import AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness

HERE = Path(__file__).parent
load_dotenv(HERE.parent / ".env")

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
            print(f"    {name} failed: {type(e).__name__}: {e}")
            out[name] = None
    
    return out

if __name__ == '__main__':
    rows = json.loads((HERE / "results_baseline.json").read_text(encoding="utf-8"))
    rows = {r["id"]: r for r in rows}
    
    for i in ("q01", "q08", "q10"):
        print(i, score_row(rows[i]))