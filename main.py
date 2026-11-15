from dotenv import load_dotenv

load_dotenv()  # reads GROQ_API_KEY from a .env file

from embed import embed_and_store
from chain import build_chain
from hybrid import build_hybrid_reranker

PDF_PATH = "test.pdf"

if __name__ == "__main__":
    # 1. Once per upload: load, chunk, embed, store
    vectorstore, chunks = embed_and_store(PDF_PATH)
    print(f"Stored {len(chunks)} chunks\n")

    # 2. Build the chain and the reranker once
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    chain = build_chain(retriever)
    hybrid_rerank = build_hybrid_reranker(chunks, vectorstore)

    # 3. Per question: reuse everything
    while True:
        question = input("\nAsk a question (or 'quit'): ").strip()
        if question.lower() in ("quit", "exit", ""):
            break

        print("\nANSWER:")
        print(chain.invoke(question))

        print("\nTOP HYBRID + RERANKED CHUNKS:")
        for score, doc in hybrid_rerank(question, top_n=3):
            page = doc.metadata.get("page")
            page_label = page + 1 if page is not None else "?"
            print(f"  rerank={score:.3f} | page {page_label} | "
                  f"{doc.page_content[:80].strip()}...")