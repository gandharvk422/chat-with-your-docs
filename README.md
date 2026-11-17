# Chat with Your Docs

A small RAG app I built so I could upload a document and ask it questions. You drop in a file, wait a few seconds while it gets indexed, and then chat with it. Answers come back with the file (and page or slide, when that's available) they were pulled from.

The stack is React on the front, FastAPI on the back, ChromaDB for vectors, and Groq for the actual answer generation. The embedding and reranking models run locally on your machine.

It handles PDF, DOCX, PPTX, TXT, Markdown and CSV files.

## How it works

When you upload a file, the backend checks the type and size (20 MB max), pulls the text out with a loader that matches the format, and splits it into chunks of 800 characters with a 100 character overlap. Each chunk is embedded with `BAAI/bge-small-en-v1.5` and stored in ChromaDB.

When you ask a question, two searches run side by side: BM25 for keyword matching and a vector search against Chroma. Results are merged (40% BM25, 60% vector), deduplicated, and then reranked with `cross-encoder/ms-marco-MiniLM-L-6-v2`. The top 4 passages go to `openai/gpt-oss-120b` on Groq along with your question. The prompt tells the model to stick to the provided context and say so if the answer isn't there.

```text
Upload:  file -> /upload -> validate + load -> split -> embed -> ChromaDB

Chat:    question -> /chat -> BM25 + vector search -> merge + dedupe
                           -> cross-encoder rerank -> top 4 -> Groq -> answer + sources
```

## Tech stack

- **Frontend:** React 18, Vite, plain CSS
- **Backend:** Python, FastAPI, Uvicorn
- **RAG plumbing:** LangChain (`RecursiveCharacterTextSplitter`, `EnsembleRetriever`)
- **Loaders:** PyPDF, Docx2txt, python-pptx, and the standard library for CSV and text
- **Embeddings:** `BAAI/bge-small-en-v1.5` via Hugging Face
- **Vector store:** ChromaDB
- **Keyword search:** BM25 (`rank_bm25`)
- **Reranker:** `cross-encoder/ms-marco-MiniLM-L-6-v2` via Sentence Transformers
- **LLM:** `openai/gpt-oss-120b` on Groq

## Supported files

| Format | How text is extracted | What the source shows |
|---|---|---|
| PDF | PyPDFLoader | Page number |
| DOCX | Docx2txt | Filename only |
| PPTX | Slide text and table contents | Slide number |
| TXT / MD | Plain text read | Filename only |
| CSV | Each row becomes `column: value` text | Filename only |

Old formats (`.doc`, `.ppt`, `.xls`, `.xlsx`) aren't supported. Convert them to `.docx`, `.pptx` or `.csv` first. Scanned PDFs and image-only documents won't work well either, since there's no OCR step.

## Project layout

```text
chat-with-your-docs/
├── backend/
│   ├── chain.py            # prompt, answer generation, source formatting
│   ├── chunks.py           # file validation, loaders, text splitting
│   ├── embed.py            # embeddings and ChromaDB
│   ├── hybrid.py           # BM25 + vector retrieval, reranking
│   ├── main.py             # FastAPI app and endpoints
│   └── test_pipeline.py    # terminal-only pipeline test
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── pyproject.toml
├── uv.lock
└── README.md
```

## Running it locally

You'll need Python 3.13+, Node.js with npm, and a [Groq API key](https://console.groq.com/keys). The first run also needs internet access to download the Hugging Face models.

### 1. Clone

```bash
git clone https://github.com/gandharvk422/chat-with-your-docs.git
cd chat-with-your-docs
```

### 2. Backend setup

Create a virtual environment from the repo root.

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Then install the dependencies:

```bash
python -m pip install --upgrade pip
pip install fastapi "uvicorn[standard]" python-multipart python-dotenv pydantic \
    langchain-core langchain-community langchain-text-splitters \
    langchain-huggingface langchain-chroma langchain-groq langchain-classic \
    pypdf docx2txt python-pptx sentence-transformers rank_bm25
```

I'm listing the packages by hand because `pyproject.toml` only covers some of what the backend imports. That's on my list to fix.

Create a `.env` file in the repo root:

```env
GROQ_API_KEY=your_groq_api_key
```

Keep that file out of git.

### 3. Start the backend

```bash
cd backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The first start is slow because the models have to download. On every start the backend also wipes `backend/chroma_db/`, so nothing you've indexed survives a restart.

Once it's up:

- API: `http://127.0.0.1:8000`
- Swagger docs: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

Leave that terminal open.

### 4. Start the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite will print a URL, usually `http://localhost:5173`. Open it. The frontend talks to `http://127.0.0.1:8000` by default; if your backend lives somewhere else, put this in `frontend/.env` and restart Vite:

```env
VITE_API_URL=http://127.0.0.1:8000
```

## Using it

Pick a file or drag it onto the upload area, wait for indexing to finish, then type a question. Each answer has a **Sources** section you can expand to see where it came from.

Uploading a new file replaces the old one. The app only keeps one active document at a time, and it isn't built for multiple users.

## API

There are three endpoints:

| Method | Endpoint | What it does |
|---|---|---|
| GET | `/health` | Status, whether the models have loaded, and the current filename |
| POST | `/upload` | Takes a file (multipart, field name `file`) and indexes it |
| POST | `/chat` | Takes a question as JSON and returns an answer plus sources |

Upload:

```bash
curl -X POST "http://127.0.0.1:8000/upload" \
  -F "file=@/path/to/your-document.pdf"
```

```json
{
  "message": "File ready",
  "filename": "your-document.pdf",
  "chunks": 18
}
```

The chunk count depends on how much text was extracted.

Chat:

```bash
curl -X POST "http://127.0.0.1:8000/chat" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"What is this document about?\"}"
```

```json
{
  "answer": "The answer generated from the retrieved document context.",
  "sources": [
    { "file": "your-document.pdf", "page": 2 }
  ]
}
```

`page` only shows up when the loader provides it (PDF and PPTX). PDF pages are zero-based internally, and the backend converts them to normal page numbers. The question has to be non-empty and no longer than 1,000 characters, and you need to have uploaded a document first.

## Settings

Everything is hardcoded in the source for now:

| Setting | File | Value |
|---|---|---|
| Max upload size | `backend/main.py` | 20 MB |
| Chunk size / overlap | `backend/chunks.py` | 800 / 100 characters |
| Embedding model | `backend/embed.py` | `BAAI/bge-small-en-v1.5` |
| Vector DB directory | `backend/embed.py` | `backend/chroma_db/` |
| BM25 / vector weights | `backend/hybrid.py` | 0.4 / 0.6 |
| Candidates per retriever | `backend/hybrid.py` | 5 |
| Cross-encoder | `backend/hybrid.py` | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Passages sent to the LLM | `backend/main.py` | 4 |
| Groq model | `backend/chain.py` | `openai/gpt-oss-120b` |
| Frontend API URL | `frontend/src/App.jsx` | `http://127.0.0.1:8000` |

## Testing the pipeline without the UI

Put a PDF called `test.pdf` in `backend/` and run:

```bash
cd backend
python test_pipeline.py
```

It resets the vector DB, indexes the PDF, builds the retriever and chain, and drops you into a Q&A loop in the terminal. Type `quit`, `exit`, or just hit enter on an empty line to stop.

## Things to know

- Only one document is active at a time. Each upload replaces the last.
- The Chroma directory is deleted on startup, so embeddings don't persist.
- Grounding is done through the prompt only. It cuts down on made-up answers but doesn't rule them out, so double-check anything important.
- Page and slide references only exist for PDF and PPTX. For everything else you get the filename.
- CORS only allows the Vite dev origins (`localhost:5173` and `127.0.0.1:5173`).

## What I'd like to add

- Persistent, per-user collections and support for several documents at once
- OCR for scanned PDFs
- Proper retrieval and answer evaluation
- Tests for the loaders, retrieval quality and endpoints
- Config through environment variables instead of constants in the code
- Finer-grained citations for DOCX, TXT, Markdown and CSV
- Auth, stricter CORS and a real deployment setup

## Credits

The RAG pipeline started from the tutorial [Build a RAG System from Scratch](https://nerdleveltech.com/guides/rag-hands-on-tutorial). I adapted it with my own loaders, hybrid retrieval, reranking, FastAPI backend and React frontend.