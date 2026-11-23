# 📄 Chat with Your Docs

Upload a document, ask questions about it, and get answers grounded **only** in that document — with the source file and page shown for every answer.

Chat with Your Docs is a Retrieval-Augmented Generation (RAG) app. A React frontend talks to a FastAPI backend that chunks and embeds your file, retrieves the most relevant passages with a hybrid (keyword + semantic) search, re-ranks them with a cross-encoder, and asks an LLM (via Groq) to answer from that context alone.

## 🔗 Live Demo

| Part | URL |
|------|-----|
| Frontend (Vercel) | https://chat-with-your-docs-ten.vercel.app/ |
| Backend API docs (Render) | https://chat-with-your-docs-iyaj.onrender.com/docs |

> **Note:** the backend runs on a hosted free-tier-style service and loads two ML models at startup, so the first request after a period of inactivity can take a while to respond. If the first upload fails or hangs, wait a minute and try again.

## ✨ Features

- **Six file formats:** PDF, DOCX, PPTX, TXT, MD and CSV (up to 20 MB).
- **Grounded answers:** the model is instructed to answer using only the retrieved context, and to say *"I don't have enough information in my knowledge base."* when the answer isn't there.
- **Source citations:** each answer lists the file and page (or slide number for PPTX) it was drawn from. Sources are hidden when the model declines to answer.
- **Hybrid retrieval + re-ranking:** BM25 keyword search and vector search are combined, then re-scored by a cross-encoder for better precision.
- **Content validation:** files are checked by their actual bytes, not just their extension, with clear error messages for unsupported or unreadable files (including legacy `.doc` / `.ppt` / `.xls` hints).
- **Clean UI:** drag-and-drop upload, chat view, light/dark theme, and graceful error handling.
- **Evaluation harness:** scripts to measure answer quality and tune retrieval (see [Evaluation](#-evaluation)).
- **Docker support:** one command to run the whole stack locally.

## 🧠 How It Works

```
 Upload                                   Ask a question
   │                                            │
   ▼                                            ▼
Validate file ─► Load (per file type)     Hybrid retrieval
   │                  │                   ├─ BM25 (40%)
   ▼                  ▼                   └─ Vector search (60%)
 Chunk text ─► Embed (BGE-small) ─► ChromaDB     │
 (800 chars, 100 overlap)                        ▼
                                          Cross-encoder re-rank ─► top 4 chunks
                                                 │
                                                 ▼
                                      Groq LLM (gpt-oss-120b)
                                                 │
                                                 ▼
                                      Answer + sources (file, page)
```

1. **Upload** – `POST /upload` saves the file temporarily, validates it, extracts text with a loader chosen by file type, and splits it into overlapping chunks.
2. **Index** – chunks are embedded with `BAAI/bge-small-en-v1.5` and stored in a fresh ChromaDB collection. A BM25 index is built from the same chunks.
3. **Retrieve** – for each question, BM25 and vector retrievers (k = 5 each by default) are merged with weights 0.4 / 0.6, de-duplicated, and re-ranked by `cross-encoder/ms-marco-MiniLM-L-6-v2`. The top 4 chunks are passed to the LLM.
4. **Generate** – the prompt restricts the model (`openai/gpt-oss-120b` on Groq, temperature 0) to the provided context. The response includes the answer and de-duplicated source references.

## 🧰 Tech Stack

**Backend**
- Python 3.13, FastAPI, Uvicorn
- LangChain (`langchain`, `langchain-community`, `langchain-classic`, `langchain-groq`, `langchain-chroma`, `langchain-huggingface`)
- ChromaDB (vector store), `rank_bm25` (keyword search)
- `sentence-transformers` (embeddings + cross-encoder re-ranker), CPU-only PyTorch
- `pypdf` / `pypdfium2`, `docx2txt`, `python-pptx` (document loading)
- Groq API (LLM)

**Frontend**
- React 18, Vite 6, `lucide-react` icons, plain CSS

**Tooling & Deployment**
- Docker + Docker Compose (Nginx serves the built frontend)
- Frontend on Vercel, backend on Render
- RAGAS for evaluation

## 📁 Project Structure

```
chat-with-your-docs/
├── backend/
│   ├── main.py            # FastAPI app: /health, /upload, /chat, CORS, startup
│   ├── chunks.py          # File validation, per-format loaders, text splitter
│   ├── embed.py           # Embedding model, ChromaDB creation/reset
│   ├── hybrid.py          # BM25 + vector ensemble and cross-encoder re-ranker
│   ├── chain.py           # RAG prompt, Groq LLM, answer + sources formatting
│   ├── test_pipeline.py   # Interactive CLI to test the pipeline on a local PDF
│   ├── evals/
│   │   ├── questions.json       # Evaluation question set
│   │   ├── run_evals.py         # Runs questions through the pipeline
│   │   ├── retrieval_eval.py    # Compares retrieval configurations
│   │   ├── score_ragas.py       # Scores results with RAGAS metrics
│   │   ├── compare.py           # Compares an experiment to the baseline
│   │   └── scores_baseline.json # Saved baseline RAGAS scores
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx        # UI, upload flow and API calls
│   │   ├── App.css
│   │   └── main.jsx
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── Dockerfile         # Multi-stage build: Node → Nginx
├── docker-compose.yml     # Runs backend (8000) + frontend (3000)
├── pyproject.toml
└── .python-version        # 3.13
```

## 🚀 Getting Started

### Prerequisites

- Python **3.13**
- Node.js **18+** (the Docker image uses Node 22)
- A free [Groq API key](https://console.groq.com/keys)

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd chat-with-your-docs
```

### 2. Run the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt uvicorn
```

Create `backend/.env`:

```env
GROQ_API_KEY=your_groq_api_key_here
```

Start the server:

```bash
uvicorn main:app --reload --port 8000
```

On first start the app downloads the embedding and re-ranker models from Hugging Face, so the initial launch takes longer. Interactive API docs are available at http://localhost:8000/docs.

### 3. Run the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. By default the frontend calls `http://127.0.0.1:8000`.

To point it at a different backend, create `frontend/.env`:

```env
VITE_API_URL=https://your-backend-url
```

### Run with Docker

Create `backend/.env` with your `GROQ_API_KEY` as above, then from the project root:

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000/docs

Hugging Face models are cached in a Docker volume (`hf_cache`), so they are only downloaded once.

## ⚙️ Configuration

### Backend environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | – (required) | API key for the Groq LLM |
| `FRONTEND_URL` | – | Deployed frontend origin to allow through CORS (e.g. `https://chat-with-your-docs-ten.vercel.app`). `localhost:5173` is always allowed. |
| `CHUNK_SIZE` | `800` | Characters per chunk |
| `CHUNK_OVERLAP` | `100` | Overlap between chunks |
| `RETRIEVER_K` | `5` | Candidates fetched by each retriever (BM25 and vector) |
| `TOP_N` | `4` | Chunks kept after re-ranking (used by the evals; the app uses 4) |
| `PDF_LOADER` | – | PDF loader switch used by the evals. By default PyPDFium2 is tried first, falling back to PyPDF; see `_load_pdf` in `chunks.py` for the exact logic |

### Frontend environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://127.0.0.1:8000` | Base URL of the backend |

The top of `frontend/src/App.jsx` also has a `USE_MOCK` flag. Set it to `true` to try the UI with fake answers and no backend.

## 🔌 API Reference

Full interactive docs: https://chat-with-your-docs-iyaj.onrender.com/docs

### `GET /health`
Returns server status and the name of the currently loaded document.

```json
{ "status": "ok", "models_loaded": true, "document": "report.pdf" }
```

### `POST /upload`
Multipart form upload with a `file` field. Replaces any previously loaded document.

```bash
curl -X POST http://localhost:8000/upload -F "file=@report.pdf"
```

```json
{ "message": "File ready", "filename": "report.pdf", "chunks": 142 }
```

| Status | Meaning |
|--------|---------|
| `400` | Unsupported type, or content doesn't match the extension |
| `413` | File larger than 20 MB |
| `422` | No readable text (e.g. scanned/image-only documents) |
| `500` | Unexpected processing error |

### `POST /chat`
Ask a question about the loaded document (1–1000 characters).

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the key findings?"}'
```

```json
{
  "answer": "The key findings are ...",
  "sources": [{ "file": "report.pdf", "page": 4 }]
}
```

Returns `400` if no document has been uploaded yet, and `500` if the LLM service fails.

## 📑 Supported Formats

| Format | How it's read | Citation shows |
|--------|---------------|----------------|
| `.pdf` | PyPDFium2 (falls back to PyPDF) | File + page |
| `.pptx` | `python-pptx` – text boxes and tables, one document per slide | File + slide number |
| `.docx` | `docx2txt` | File |
| `.txt`, `.md` | Plain text (UTF-8, falls back to Windows-1252) | File |
| `.csv` | One document per row, as `column: value` lines | File |

Scanned PDFs (images of text) are **not** supported — there is no OCR step.

## 📊 Evaluation

The `backend/evals/` folder holds a small harness for measuring answer quality and comparing pipeline settings, so changes can be judged with numbers instead of guesses.

### Test set

`questions.json` has **34 hand-written questions** across five documents, each with an expected answer and a reference page:

| Type | Count | Purpose |
|------|-------|---------|
| `lookup` | 23 | A fact that sits in one place in the document |
| `reasoning` | 6 | Needs several passages combined |
| `unanswerable` | 5 | Not in the document, so the bot should refuse instead of making something up |

Documents covered: a machine-learning textbook PDF (9 questions), a Stoicism PDF (7), a biofeedback DOCX (6), a Markdown file (6) and a short PDF (6). The documents are git-ignored, so place your own files in `backend/evals/docs/` using the names in `questions.json`.

### How the evaluation works

```
questions.json ─► run_evals.py ─► results_<EXP>.json ─► score_ragas.py ─► scores_<EXP>.json
 (questions +      (asks the real     (answers, retrieved    (LLM judge       (per-question
  answer key)       pipeline)          chunks, sources)       grades them)     scores)
```

1. **`run_evals.py`** embeds each document, asks its questions through the real pipeline, and saves the answer, the exact chunks the LLM saw and the cited sources. It also runs two checks that need no judge model:
   - **Refusal check:** unanswerable questions should get *"I don't have enough information"*, and answerable ones should not (flags false refusals).
   - **Page hit:** whether the reference page appears among the cited sources.
2. **`score_ragas.py`** grades the answerable questions with [RAGAS](https://docs.ragas.io/), using `openai/gpt-oss-120b` on Groq as the judge and local `bge-small` embeddings:
   - **Faithfulness:** is the answer supported by the retrieved context?
   - **Answer relevancy:** does the answer address the question?
   - **Context precision:** are the retrieved chunks relevant and well ranked?
   - **Context recall:** did retrieval find what's needed for the expected answer?
3. **`compare.py`** compares an experiment against the baseline, question by question.
4. **`retrieval_eval.py`** compares retrieval settings (for example `RETRIEVER_K` and the PDF loader) using term recall, with no judge needed.

Context precision and recall measure the **retriever**; faithfulness and answer relevancy measure the **answer writer**. A low score therefore tells you which stage to fix.

### Baseline results

Saved in `backend/evals/scores_baseline.json` (default settings: chunk size 800, overlap 100, `RETRIEVER_K=5`, `TOP_N=4`).

| Metric | Average | Questions scored |
|--------|---------|------------------|
| Faithfulness | **0.944** | 9 |
| Answer relevancy | **0.865** | 9 |
| Context precision | **0.936** | 10 |
| Context recall | **0.933** | 10 |

What the numbers show:

- **Answers stay grounded.** Faithfulness is 1.0 on 8 of the 9 scored questions; the one miss (`q05`, 0.5) also had the lowest context recall (0.67).
- **Retrieval is strong on lookups.** Lookup questions average about 0.97 context precision.
- **Reasoning questions are harder.** The one scored reasoning question (`q07`) had context precision 0.64 and answer relevancy 0.74, which suggests retrieval returns extra, loosely related chunks when several passages are needed.
- **False refusals exist.** Two answerable questions (`q08`, `q13`) were refused as "not enough information", about 7% of the 29 answerable questions.

> **Important:** this baseline is **partial**. Only 10 of the 29 answerable questions have judge scores in the saved file; the rest came back empty, most likely because of rate limits on the free Groq tier. Treat the averages as indicative, not final. Rerun `score_ragas.py` to fill them in. With a set this small, one question moves a category score a lot, so differences of a few points are likely noise.

### Run it yourself

From `backend/`:

```bash
# 1. Ask the pipeline every question (EXP_NAME labels the experiment)
EXP_NAME=baseline python evals/run_evals.py

# 2. Grade the answers with RAGAS
EXP_NAME=baseline python evals/score_ragas.py

# 3. Change one setting, re-run, and compare against the baseline
RETRIEVER_K=10 TOP_N=6 EXP_NAME=k10_n6 python evals/run_evals.py
python evals/compare.py k10_n6
```

On Windows PowerShell, set variables first, for example `$env:EXP_NAME="baseline"`. Tunable settings: `CHUNK_SIZE`, `CHUNK_OVERLAP`, `RETRIEVER_K`, `TOP_N`, `PDF_LOADER`. Generated `results*.json` files are git-ignored.

## 🧪 Quick Pipeline Test

To try retrieval and answering from the terminal without the web UI, put a PDF named `test.pdf` in `backend/` and run:

```bash
cd backend
python test_pipeline.py
```

## ☁️ Deployment Notes

- **Backend (Render):** deploy the `backend/` folder (a Dockerfile is included). Set `GROQ_API_KEY` and `FRONTEND_URL=https://chat-with-your-docs-ten.vercel.app`.
- **Frontend (Vercel):** deploy the `frontend/` folder as a Vite project and set `VITE_API_URL=https://chat-with-your-docs-iyaj.onrender.com`.

## ⚠️ Known Limitations

- **One document at a time, shared globally.** The backend keeps a single active document in memory. A new upload replaces the previous one for everyone using that server, so this is best suited to personal use or demos rather than multi-user production.
- **Ephemeral storage.** The vector database is wiped on every server start and is not meant to persist between restarts.
- **No OCR.** Image-only/scanned documents can't be read.
- **Legacy Office formats** (`.doc`, `.ppt`, `.xls`, `.xlsx`) aren't supported; convert to DOCX, PPTX or CSV first.
- **Cold starts.** Loading the embedding and re-ranking models takes time on startup.

## 🛣️ Possible Improvements

- Per-session or per-user document storage and multi-document chat
- Conversation memory for follow-up questions
- Streaming responses
- OCR for scanned PDFs
- Persistent vector storage

## 👤 Author

Created by [Gandharv Kulkarni](https://github.com/gandharvk422)

## 🙏 Acknowledgements

Built with [FastAPI](https://fastapi.tiangolo.com/), [LangChain](https://www.langchain.com/), [ChromaDB](https://www.trychroma.com/), [Sentence Transformers](https://www.sbert.net/), [Groq](https://groq.com/), [React](https://react.dev/) and [Vite](https://vitejs.dev/). Evaluation with [RAGAS](https://docs.ragas.io/).
