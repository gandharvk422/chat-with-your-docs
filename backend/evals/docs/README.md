# Chat with Your Docs

A full-stack Retrieval-Augmented Generation (RAG) app. Upload a document, ask questions about it, and get answers generated **only from that document**, with the source file and page shown for every answer.

**Live demo:** [chat-with-your-docs-ten.vercel.app](https://chat-with-your-docs-ten.vercel.app)
**API docs:** [chat-with-your-docs-iyaj.onrender.com/docs](https://chat-with-your-docs-iyaj.onrender.com/docs)

> The backend runs on a free Render plan. It sleeps when idle, so the first request after a pause can take about a minute, and you need to upload your file again after it wakes up.

## Features

- Upload **PDF, DOCX, PPTX, TXT, MD and CSV** files, by drag and drop or the file picker
- Answers grounded in the uploaded document, with **source file and page** (slide number for PPTX)
- **Hybrid retrieval**: BM25 keyword search (40%) + vector similarity (60%)
- Optional **cross-encoder reranking** of the retrieved chunks
- Local, free embeddings (`BAAI/bge-small-en-v1.5`) and Groq for answer generation (`openai/gpt-oss-120b`)
- Upload checks: file extension, real file content, and a 20 MB size limit, with clear error messages
- React UI with a chat view, collapsible sources, typing indicator and light/dark theme

## How it works

```
Upload (once per file)
  file -> loader (by type) -> split into chunks -> embed (HuggingFace) -> ChromaDB

Question (every time)
  question -> BM25 + vector search -> (rerank) -> top chunks -> prompt -> Groq LLM
           -> { answer, sources: [{ file, page }] }
```

## Tech stack

| Part | Tool |
|---|---|
| Frontend | React, Vite, lucide-react |
| Backend | Python, FastAPI, Uvicorn |
| RAG framework | LangChain |
| Document loading | PyPDF, docx2txt, python-pptx, built-in CSV and text readers |
| Chunking | `RecursiveCharacterTextSplitter` (800 characters, 100 overlap) |
| Embeddings | HuggingFace `BAAI/bge-small-en-v1.5` (runs locally) |
| Vector store | ChromaDB |
| Keyword search | BM25 (`rank_bm25`) |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` (runs locally) |
| LLM | Groq, `openai/gpt-oss-120b` |
| Deployment | Vercel (frontend), Render with Docker (backend) |

## Project structure

```
.
├── pyproject.toml          # Python dependencies (managed with uv)
├── .python-version
├── backend/
│   ├── main.py             # FastAPI app: /health, /upload, /chat, CORS, startup
│   ├── chunks.py           # loaders for each file type, validation, chunking
│   ├── embed.py            # embeddings and ChromaDB storage
│   ├── chain.py            # prompt, context formatting, RAG chain, sources
│   ├── hybrid.py           # BM25 + vector retrieval and reranking
│   ├── test_pipeline.py    # terminal test of the whole pipeline
│   ├── requirements.txt    # pinned packages used by the Docker build
│   ├── Dockerfile
│   └── .env.example
└── frontend/
    ├── index.html
    ├── package.json
    └── src/
        ├── main.jsx
        ├── App.jsx         # UI and the API calls
        └── App.css
```

## API

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Server status, and the name of the loaded document |
| POST | `/upload` | Multipart form with a `file` field. Loads, chunks, embeds and stores it. |
| POST | `/chat` | JSON `{ "question": "..." }`. Returns `{ "answer": "...", "sources": [{ "file": "...", "page": 1 }] }` |

Errors are returned as `{ "detail": "..." }` with a readable message.

## Run it locally

**Requirements:** Python (see `.python-version`), [uv](https://docs.astral.sh/uv/), Node.js 18+, and a free [Groq API key](https://console.groq.com).

**1. Backend**

```bash
uv sync
cd backend
cp .env.example .env      # then put your key in it: GROQ_API_KEY=gsk_...
uv run uvicorn main:app --reload --port 8000
```

The first start downloads the embedding and reranker models, so wait for "Application startup complete". Check `http://127.0.0.1:8000/health`.

**2. Frontend**

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend calls `http://127.0.0.1:8000` by default. To use another address, create `frontend/.env` with `VITE_API_URL=...` and restart the dev server.

**3. Terminal test (optional)**

Put a sample PDF named `test.pdf` in `backend/`, then run `uv run python test_pipeline.py` from `backend/`.

## Deployment

| Part | Where | Settings |
|---|---|---|
| Frontend | Vercel | Root Directory `frontend`. Environment variable `VITE_API_URL` set to the backend URL. |
| Backend | Render (Docker) | Root Directory `backend`. Environment variables `GROQ_API_KEY` and `FRONTEND_URL` (the Vercel address, for CORS). |

Optional backend variables:
- `USE_RERANKER=false` skips the cross-encoder, which is faster on a small CPU.
- `CHROMA_DB_DIR` sets where ChromaDB stores its data (the Dockerfile uses `/tmp`).

Both services redeploy automatically when you push to `main`. Never commit your `.env` file or API key.

## Limitations

- **One document at a time for the whole server.** The loaded document is kept in memory, so a new upload replaces it for every user, and the document is lost when the server restarts.
- No login and no rate limiting.
- Scanned PDFs and images are not supported (no OCR).
- Old Office formats (`.doc`, `.ppt`, `.xls`, `.xlsx`) are not supported. Save them as `.docx` / `.pptx` or export a `.csv`.
- CSV works for looking up facts, but not for totals or averages, since only a few rows are retrieved per question.

## Author

Created by [Gandharv Kulkarni](https://github.com/gandharvk422)