# Chat with Your Docs

**Chat with Your Docs** is a Retrieval-Augmented Generation (RAG) web application that lets you upload a document and ask questions about its contents. It combines a React interface, a FastAPI backend, local Hugging Face embedding and reranking models, ChromaDB vector storage, and the Groq API for answer generation.

The application retrieves relevant passages from the uploaded document before generating an answer. It also returns source information so you can see which file—and, where available, which page or slide—was used.

## Features

- **Document upload:** Upload PDF, DOCX, PPTX, TXT, Markdown, and CSV files.
- **Document-aware Q&A:** Ask natural-language questions about the uploaded file.
- **Hybrid retrieval:** Combines BM25 keyword retrieval with ChromaDB vector similarity.
- **Cross-encoder reranking:** Reorders retrieved passages by relevance before they reach the language model.
- **Source references:** Displays the source filename and page number when page metadata is available.
- **Grounded responses:** The prompt instructs the model to answer only from retrieved context and to say when the context does not contain enough information.
- **React interface:** Includes drag-and-drop upload, chat, source details, and light/dark themes.
- **Local retrieval models:** Embedding and reranking models run locally; answer generation uses Groq.

## Application workflow

1. The user uploads a document through the React frontend.
2. FastAPI validates the file type, checks its contents, and enforces a 20 MB upload limit.
3. The backend extracts text using a format-specific loader.
4. Extracted documents are split into chunks of 800 characters with 100 characters of overlap.
5. The chunks are embedded with `BAAI/bge-small-en-v1.5` and stored in ChromaDB.
6. For each question, the retriever combines BM25 and vector search results (40% and 60% weights respectively).
7. Candidate passages are deduplicated and reranked using `cross-encoder/ms-marco-MiniLM-L-6-v2`.
8. The four highest-ranked passages are passed to the Groq-hosted `openai/gpt-oss-120b` model.
9. The API returns the generated answer and its source references to the frontend.

### RAG pipeline

```text
                         DOCUMENT INGESTION
                                  |
                                  v
                         React file upload
                                  |
                                  v
                            FastAPI /upload
                                  |
                                  v
                       File validation & loading
                                  |
                                  v
                       Text extraction by format
                                  |
                                  v
                    Recursive character splitting
                       (800 size / 100 overlap)
                                  |
                                  v
                   Hugging Face embeddings
                    BAAI/bge-small-en-v1.5
                                  |
                                  v
                              ChromaDB
                                  |
                                  |
                         QUESTION ANSWERING
                                  |
                                  v
                          React chat input
                                  |
                                  v
                            FastAPI /chat
                                  |
                                  v
                       Hybrid retrieval search
                       /                    \
                      v                      v
                BM25 keyword          ChromaDB vector
                  search                  search
                    \                    /
                     \                  /
                      v                v
                       Ensemble retrieval
                       (40% BM25 / 60% vector)
                                  |
                                  v
                         Candidate deduplication
                                  |
                                  v
                         Cross-encoder reranking
                                  |
                                  v
                           Top 4 passages
                                  |
                                  v
                       Context + question prompt
                                  |
                                  v
                         Groq: gpt-oss-120b
                                  |
                                  v
                      Answer + source references
                                  |
                                  v
                           React chat UI
```

## Tech stack

| Layer | Technologies |
|---|---|
| Frontend | React 18, Vite, JavaScript, CSS |
| Backend API | Python, FastAPI, Uvicorn |
| RAG orchestration | LangChain |
| Document loading | PyPDF, Docx2txt, python-pptx, Python CSV/text readers |
| Text splitting | `RecursiveCharacterTextSplitter` |
| Embeddings | Hugging Face `BAAI/bge-small-en-v1.5` |
| Vector database | ChromaDB |
| Keyword retrieval | BM25 with `rank_bm25` |
| Hybrid retrieval | LangChain `EnsembleRetriever` |
| Reranking | Sentence Transformers `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| LLM | Groq API — `openai/gpt-oss-120b` |

## Supported document formats

| Format | Extraction approach | Source location |
|---|---|---|
| PDF | PyPDFLoader | Page number |
| DOCX | Docx2txtLoader | Filename |
| PPTX | Extracts slide text and table contents | Slide number |
| TXT | Text file reader | Filename |
| MD | Text file reader | Filename |
| CSV | Converts each row into `column: value` text | Filename |

The upload limit is **20 MB per file**. Legacy `.doc`, `.ppt`, `.xls`, and `.xlsx` files are not supported; convert them to `.docx`, `.pptx`, or `.csv` respectively.

Scanned PDFs and image-only documents are not OCR-processed. They may fail to produce usable text.

## Repository structure

```text
chat-with-your-docs/
├── backend/
│   ├── chain.py             # RAG prompt, answer generation, and source formatting
│   ├── chunks.py            # File validation, document loaders, and text splitting
│   ├── embed.py             # Hugging Face embeddings and ChromaDB operations
│   ├── hybrid.py            # BM25 + vector retrieval and cross-encoder reranking
│   ├── main.py              # FastAPI application and API endpoints
│   └── test_pipeline.py     # Standalone terminal pipeline test
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main React application and API integration
│   │   ├── App.css          # Application styling and themes
│   │   └── main.jsx         # React entry point
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── .gitignore
├── .python-version
├── pyproject.toml
├── uv.lock
└── README.md
```

## Getting started

### Prerequisites

Make sure you have:

- Python **3.13 or later** (the project configuration specifies `>=3.13`).
- Node.js and npm.
- A [Groq API key](https://console.groq.com/keys).
- Internet access on the first run to download the Hugging Face models and call the Groq API.

> The embedding and cross-encoder models run locally. The Groq API key is required for generating answers.

### 1. Clone the repository

```bash
git clone https://github.com/gandharvk422/chat-with-your-docs.git
cd chat-with-your-docs
```

### 2. Configure the backend

Create and activate a virtual environment from the repository root:

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the backend dependencies:

```bash
python -m pip install --upgrade pip
pip install fastapi "uvicorn[standard]" python-multipart python-dotenv pydantic \
    langchain-core langchain-community langchain-text-splitters \
    langchain-huggingface langchain-chroma langchain-groq langchain-classic \
    pypdf docx2txt python-pptx sentence-transformers rank_bm25
```

Create a `.env` file inside the **repository root** (the backend loads environment variables when it starts):

```env
GROQ_API_KEY=your_groq_api_key
```

Do not commit your `.env` file or expose your API key.

### 3. Start the backend

From the repository root, run:

```bash
cd backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

On startup, the backend clears its local ChromaDB directory and loads the embedding and cross-encoder models. The first startup can take longer because the models need to be downloaded.

The API will be available at:

- API base URL: `http://127.0.0.1:8000`
- Interactive API documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

Keep this terminal running.

### 4. Start the frontend

Open a second terminal and navigate to the frontend directory:

```bash
cd frontend
npm install
npm run dev
```

Vite prints the local development URL in the terminal (normally `http://localhost:5173`). Open that URL in your browser.

The frontend uses `http://127.0.0.1:8000` as its default backend URL. To override it, create `frontend/.env`:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Restart the Vite development server after changing frontend environment variables.

## Using the application

1. Open the frontend in your browser.
2. Select a supported document or drag and drop it into the upload area.
3. Wait for the upload and indexing process to finish.
4. Enter a question in the chat input and submit it.
5. Read the answer and expand the **Sources** section to inspect the returned file and page references.

A new upload replaces the currently indexed document. This version is designed for one active document at a time, not multiple users or independent document collections.

## API reference

The backend currently exposes three endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Returns API status, model-loading status, and the active document filename. |
| `POST` | `/upload` | Accepts a document as multipart form data under the `file` field, validates it, and indexes it. |
| `POST` | `/chat` | Accepts a question as JSON and returns an answer with source references. |

### Upload a document

```bash
curl -X POST "http://127.0.0.1:8000/upload" \
  -F "file=@/path/to/your-document.pdf"
```

Successful response:

```json
{
  "message": "File ready",
  "filename": "your-document.pdf",
  "chunks": 18
}
```

The `chunks` value depends on the document's extracted text.

### Ask a question

```bash
curl -X POST "http://127.0.0.1:8000/chat" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"What is this document about?\"}"
```

Response shape:

```json
{
  "answer": "The answer generated from the retrieved document context.",
  "sources": [
    {
      "file": "your-document.pdf",
      "page": 2
    }
  ]
}
```

The `page` field is included when page metadata is available. The backend converts zero-based PDF page metadata to human-readable, one-based page numbers. PPTX slide metadata is also represented through the page field. Other supported formats may return only the filename.

The `/chat` endpoint requires a non-empty question of at most 1,000 characters and requires a document to have been uploaded first.

## Configuration

The main configuration values are currently defined in the source files:

| Setting | Location | Current value |
|---|---|---|
| Maximum upload size | `backend/main.py` | 20 MB |
| Chunk size | `backend/chunks.py` | 800 characters |
| Chunk overlap | `backend/chunks.py` | 100 characters |
| Embedding model | `backend/embed.py` | `BAAI/bge-small-en-v1.5` |
| Vector database directory | `backend/embed.py` | `backend/chroma_db/` |
| BM25 / vector weights | `backend/hybrid.py` | 0.4 / 0.6 |
| Initial candidates per retriever | `backend/hybrid.py` | 5 |
| Reranked passages sent to the LLM | `backend/main.py` | 4 |
| Cross-encoder model | `backend/hybrid.py` | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Groq chat model | `backend/chain.py` | `openai/gpt-oss-120b` |
| Frontend API URL | `frontend/src/App.jsx` | `http://127.0.0.1:8000` |

## Running the pipeline test

The repository also includes a terminal-based pipeline test. Place a sample PDF named `test.pdf` inside the `backend/` directory, then run:

```bash
cd backend
python test_pipeline.py
```

The script resets the local vector database, indexes the PDF, builds the hybrid retriever and RAG chain, and starts an interactive question-answering loop. Enter `quit`, `exit`, or an empty input to stop.

## Important implementation notes

- **One active document:** Each upload builds a new collection and replaces the previously active document. The application is not currently configured for per-user or multi-document isolation.
- **Database lifecycle:** The backend deletes `backend/chroma_db/` at startup. Uploaded document embeddings therefore do not persist across backend restarts.
- **Local model downloads:** Hugging Face models are downloaded on first use and cached by the local model tooling.
- **Grounding is prompt-based:** The prompt tells the LLM to use only retrieved context. RAG reduces unsupported answers but does not guarantee that a generated answer is always correct.
- **Citations depend on loader metadata:** Page/slide references are available for PDF and PPTX documents. DOCX, TXT, Markdown, and CSV source references currently identify the file only.
- **CORS:** The API currently permits the Vite development origins `localhost:5173` and `127.0.0.1:5173`.
- **Dependency configuration:** `pyproject.toml` currently lists only a subset of the packages imported by the backend. The explicit installation command above includes the runtime packages used by the current source files.

## Potential improvements

- Add persistent, per-user document collections and support multiple active documents.
- Add OCR for scanned PDFs and image-based documents.
- Add automated retrieval and answer evaluation (for example, with a RAG evaluation framework).
- Add automated tests for file loaders, retrieval quality, and API endpoints.
- Move model names, chunking settings, and upload limits into environment-based configuration.
- Improve citation granularity for formats that do not currently expose page metadata.
- Add production deployment configuration, authentication, and stricter CORS settings.

## Acknowledgements

The RAG pipeline was informed by the tutorial [Build a RAG System from Scratch](https://nerdleveltech.com/guides/rag-hands-on-tutorial), with the implementation adapted to this application's document loaders, hybrid retrieval, reranking, FastAPI backend, and React frontend.

---

**Built with Python, LangChain, FastAPI, React, ChromaDB, Hugging Face, and Groq.**
