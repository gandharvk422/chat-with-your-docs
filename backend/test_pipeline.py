from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from embed import embed_and_store, reset_db
from chain import build_chain
from hybrid import build_hybrid_reranker

# Put a sample PDF named test.pdf in the backend folder (or change this name)
DOC_PATH = Path(__file__).parent / "test.pdf"

if __name__ == "__main__":
    if not DOC_PATH.exists():
        raise SystemExit(f"File not found: {DOC_PATH}. Add a sample PDF there.")

    print("=========Embed and Store=========")
    reset_db()
    # 1. Once per upload: load, chunk, embed, store
    vectorstore, chunks = embed_and_store(str(DOC_PATH))
    print(f"Stored {len(chunks)} chunks\n")

    print("=========Chain and Reranking=========")
    # 2. Build the chain and the reranker once
    hybrid_rerank = build_hybrid_reranker(chunks, vectorstore)
    chain = build_chain(lambda q: [doc for _, doc in hybrid_rerank(q, top_n = 4)])

    print("=========Question-Answering=========")
    # 3. Per question: reuse everything
    while True:
        question = input("\nAsk a question (or 'quit'): ").strip()
        if question.lower() in ("quit", "exit", ""):
            break

        result = chain.invoke(question)
        print("\nANSWER:")
        print(result["answer"])
        print("\nSOURCES:", result["sources"])