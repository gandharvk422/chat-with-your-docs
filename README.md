# Chat with Your Docs

A Retrieval-Augmented Generation (RAG) app that lets you upload a document and ask questions about it. Answers are generated **only from the document's content** and cite the source file and page.

> **Status: work in progress.** The core RAG pipeline works from the terminal with **PDF files only**. There is no web UI or API yet.

## Features (current)

- Load and chunk PDF files
- Local, free embeddings with HuggingFace (`BAAI/bge-small-en-v1.5`)
- Vector storage in ChromaDB
- Answer generation with Groq (`openai/gpt-oss-120b`)
- Answers cite the file name and page number
- Hybrid search (BM25 keyword + vector similarity) with cross-encoder reranking
- Terminal chat loop for testing

## How it works

```
Upload (once per PDF)
  PDF -> PyPDFLoader -> split into chunks -> embed (HuggingFace) -> ChromaDB

Question (every time)
  question -> retriever (top chunks) -> prompt + context -> Groq LLM -> answer with citations
```

The hybrid reranker runs alongside the chain:

```
question -> BM25 (40%) + vector search (60%) -> deduplicate -> cross-encoder rerank -> top 3 chunks
```

## Tech stack

| Part | Tool |
|---|---|
| Language | Python |
| Orchestration | LangChain |
| PDF loading | `PyPDFLoader` |
| Chunking | `RecursiveCharacterTextSplitter` (800 characters, 100 overlap) |
| Embeddings | HuggingFace `BAAI/bge-small-en-v1.5` (runs locally) |
| Vector store | ChromaDB |
| Keyword search | BM25 (`rank_bm25`) |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` (runs locally) |
| LLM | Groq, `openai/gpt-oss-120b` |

## Project structure

```
.
├── chunks.py   # load a PDF and split it into chunks
├── embed.py    # embed chunks and store/load ChromaDB
├── chain.py    # prompt, context formatting, and the RAG chain
├── hybrid.py   # BM25 + vector hybrid retrieval and reranking
├── main.py     # terminal test script
├── .env        # your API key (not committed)
└── test.pdf    # a PDF to test with
```

## Setup

**1. Install dependencies** (Python 3.10+ recommended)

```bash
pip install langchain langchain-community langchain-text-splitters \
            langchain-huggingface langchain-chroma langchain-groq \
            langchain-classic pypdf sentence-transformers rank_bm25 python-dotenv
```

**2. Get a Groq API key**

Create a free key at [console.groq.com](https://console.groq.com), then create a `.env` file in the project folder:

```
GROQ_API_KEY=gsk_...
```

Add `.env` and `chroma_db/` to your `.gitignore`. Never commit your API key.

**3. Add a PDF**

Put a PDF named `test.pdf` in the project folder, or change `DOC_PATH` in `main.py`.

## Usage

```bash
python main.py
```

The script embeds the PDF once, then lets you ask questions in a loop. For each question it prints the answer and the top reranked chunks with their page numbers.

To check only loading and chunking:

```bash
python chunks.py
```

## Notes

- **First run is slow.** The embedding model and the cross-encoder are downloaded from HuggingFace the first time.
- **One document at a time.** Each call to `embed_and_store()` deletes and rebuilds `./chroma_db`, so a new upload replaces the previous one.
- **Use the same embedding model for storing and searching.** If you change `EMBEDDING_MODEL` in `embed.py`, delete `./chroma_db` and re-embed.
- **Scanned PDFs** (images of text) are not supported yet. They need OCR.
- **Groq model names change.** If you get a "model not found" error, list the current models with `Groq().models.list()` or check [console.groq.com/docs/models](https://console.groq.com/docs/models).
- On Windows, deleting `chroma_db` can fail with a permission error if another process still has it open.

## Roadmap

- [ ] Use hybrid retrieval + reranking inside the chain (currently the chain uses plain vector search)
- [ ] Evaluate with RAGAS (using Groq and HuggingFace embeddings as the judge)
- [ ] Support `.txt`, `.docx` and other file types by choosing a loader per extension
- [ ] Backend API with FastAPI or Flask (upload and chat endpoints)
- [ ] React frontend
- [ ] Per-user document storage (metadata filtering or one collection per user)
- [ ] OCR for scanned PDFs

## Acknowledgements

The pipeline structure follows the tutorial [Build a RAG System from Scratch](https://nerdleveltech.com/guides/rag-hands-on-tutorial), adapted for PDF uploads, Groq and local HuggingFace embeddings.