import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.metrics.collections import Faithfulness

HERE = Path(__file__).parent
load_dotenv(HERE.parent / ".env")

client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ["GROQ_API_KEY"],
    max_retries=6
)

judge = llm_factory(
    "openai/gpt-oss-20b",
    provider = "openai",
    client = client,
    temperature = 0,
    max_tokens = 4096
)
faithfulness = Faithfulness(llm = judge)

if __name__ == '__main__':
    rows = json.loads((HERE / "results_baseline.json").read_text(encoding="utf-8"))
    # Skip unanswerable questions and refusals: faithfulness needs a real answer
    rows = [r for r in rows if r["type"] != "unanswerable" and not r["refused"]]
    
    for r in rows[:3]:
        result = faithfulness.score(
            user_input = r["question"],
            response = r["answer"],
            retrieved_contexts = r["contexts"]
        )
        print(r["id"], "faithfulness =", result.value)