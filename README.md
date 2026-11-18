
# Chat with Your Docs 📄

A full-stack **Retrieval-Augmented Generation (RAG)** application that allows users to upload documents and interact with their content through an AI-powered conversational interface.

Built using **React, FastAPI, LangChain, ChromaDB, Hugging Face, and Groq**, the application combines semantic search, keyword-based retrieval, and cross-encoder reranking to retrieve relevant document context and generate grounded answers.

---

## 🚀 Features

- **Multi-Format Document Support:** Upload PDF, DOCX, PPTX, TXT, Markdown, and CSV files.
- **Document Processing:** Extract text and split documents into smaller, overlapping chunks for efficient retrieval.
- **Semantic Search:** Generate document embeddings using Hugging Face and store them in ChromaDB.
- **Hybrid Retrieval:** Combine BM25 keyword search and vector similarity search for better context retrieval.
- **Cross-Encoder Reranking:** Rerank retrieved document chunks based on query relevance.
- **AI-Powered Q&A:** Generate context-grounded responses using Groq-hosted LLMs.
- **Source Attribution:** Display source filenames and page or slide references alongside generated answers.
- **Modern User Interface:** React-based conversational interface with light and dark themes.
- **REST API:** FastAPI endpoints for document uploads, question answering, and health checks.

---

## 🏗️ System Architecture

The application follows a Retrieval-Augmented Generation (RAG) architecture consisting of two major workflows.

### 1. Document Ingestion Pipeline

1. The user uploads a document through the React frontend.
2. FastAPI validates the file type, content, and size.
3. LangChain document loaders extract text from the uploaded document.
4. Recursive Character Text Splitter divides the extracted content into chunks.
5. Hugging Face generates embeddings for each chunk.
6. ChromaDB stores the document embeddings for similarity-based retrieval.
7. A BM25 retriever is constructed for keyword-based retrieval.

### 2. Question Answering Pipeline

1. The user submits a question through the chat interface.
2. BM25 and vector retrievers independently retrieve relevant document chunks.
3. An ensemble retriever combines both retrieval strategies using weighted scores.
4. A Cross-Encoder reranks the retrieved candidates based on relevance to the query.
5. The top four relevant chunks are passed to the LLM as context.
6. Groq generates an answer using the retrieved document context.
7. The frontend displays the answer along with its source references.

### Architecture Diagram

```text
                 DOCUMENT INGESTION
                         |
                         v
                  Document Upload
                         |
                         v
                 FastAPI Validation
                         |
                         v
                  Text Extraction
                         |
                         v
                  Text Chunking
                         |
                         v
                Hugging Face Embeddings
                         |
                         v
                     ChromaDB
                         |
                         +----------------+
                         |                |
                         v                v
                    Vector Search     BM25 Search
                         |                |
                         +-------+--------+
                                 |
                                 v
                       Hybrid Retrieval
                                 |
                                 v
                      Cross-Encoder Reranking
                                 |
                                 v
                       Top 4 Relevant Chunks
                                 |
                                 v
                         Groq LLM
                                 |
                                 v
                       Generated Answer
                                 |
                                 v
                    Answer + Source References
```

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Frontend | React.js, JavaScript, CSS |
| Build Tool | Vite |
| Backend | Python, FastAPI |
| API Server | Uvicorn |
| RAG Framework | LangChain |
| Embedding Model | BAAI/bge-small-en-v1.5 |
| Vector Database | ChromaDB |
| Keyword Retrieval | BM25 |
| Hybrid Retrieval | LangChain EnsembleRetriever |
| Reranking | Cross-Encoder |
| Reranking Model | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| LLM Provider | Groq |
| Language Model | openai/gpt-oss-120b |
| Document Processing | PyPDF, Docx2txt, python-pptx |

---

## 🧠 RAG Implementation Details

### 1. Document Chunking

The application uses LangChain's `RecursiveCharacterTextSplitter` to divide extracted document content into smaller chunks.

| Parameter | Value |
|---|---|
| Chunk Size | 800 characters |
| Chunk Overlap | 100 characters |

Chunk overlap helps preserve contextual continuity between consecutive chunks.

### 2. Embeddings and Vector Storage

- **Embedding Model:** `BAAI/bge-small-en-v1.5`
- **Vector Database:** ChromaDB

The embedding model converts document chunks into numerical representations, which are stored in ChromaDB for semantic similarity search.

### 3. Hybrid Retrieval

The application combines two retrieval approaches using LangChain's `EnsembleRetriever`.

| Retrieval Method | Weight |
|---|---:|
| BM25 Keyword Retrieval | 40% |
| Vector Similarity Retrieval | 60% |

Each retriever retrieves up to five candidates. Their results are combined, and duplicate candidates are removed before reranking.

### 4. Cross-Encoder Reranking

The retrieved candidates are reranked using:

`cross-encoder/ms-marco-MiniLM-L-6-v2`

The Cross-Encoder evaluates the relevance between the user's question and each retrieved document chunk.

The four highest-ranked chunks are selected as context for answer generation.

### 5. LLM Integration

The application uses Groq through LangChain's `ChatGroq` integration.

**Model:** `openai/gpt-oss-120b`

The RAG prompt instructs the model to:
- Answer using only the retrieved document context.
- Avoid introducing information that is not present in the context.
- Respond with an insufficient-information message when the retrieved context does not contain the answer.

---

## 📁 Project Structure

```text
chat-with-your-docs/
│
├── backend/
│   ├── main.py
│   ├── chunks.py
│   ├── embed.py
│   ├── hybrid.py
│   ├── chain.py
│   └── test_pipeline.py
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── main.jsx
│   │
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── requirements.txt
├── pyproject.toml
├── uv.lock
└── README.md
```

### Backend Files

| File | Responsibility |
|---|---|
| `main.py` | FastAPI application, API endpoints, and application lifecycle |
| `chunks.py` | File validation, document loading, and text chunking |
| `embed.py` | Embedding generation and ChromaDB operations |
| `hybrid.py` | Hybrid retrieval and Cross-Encoder reranking |
| `chain.py` | RAG prompt construction, LLM integration, and source formatting |
| `test_pipeline.py` | Terminal-based RAG pipeline testing |

### Frontend Files

| File | Responsibility |
|---|---|
| `App.jsx` | Main React application and chat interface |
| `App.css` | Application styling and themes |
| `main.jsx` | React application entry point |

---

## 📄 Supported Document Formats

| File Format | Processing Library |
|---|---|
| PDF | PyPDF |
| DOCX | Docx2txt |
| PPTX | python-pptx |
| TXT | Python |
| Markdown | Python |
| CSV | Python CSV module |

**Upload Limit:** 20 MB per document.

**Note:** Scanned PDFs and image-only documents are not currently supported because OCR functionality has not been implemented.

---

## ⚙️ Installation and Setup

### Prerequisites

Make sure you have the following installed:

- Python 3.13+
- Node.js and npm
- Git
- Groq API Key

### 1. Clone the Repository

```bash
git clone https://github.com/gandharvk422/chat-with-your-docs.git

cd chat-with-your-docs
```

### 2. Configure Environment Variables

Create a `.env` file in the project root directory.

```env
GROQ_API_KEY=your_groq_api_key
```

Get your API key from:

https://console.groq.com/keys

**Important:** Never commit your `.env` file or expose your API key publicly.

### 3. Backend Setup

Create and activate a Python virtual environment.

**Windows:**

```powershell
python -m venv .venv

.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Navigate to the backend directory:

```bash
cd backend
```

Start the FastAPI server:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

The backend will be available at:

- API: http://localhost:8000
- Swagger Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

**Note:** On the first startup, Hugging Face downloads the embedding and Cross-Encoder models. This may take some time.

### 4. Frontend Setup

Open another terminal and navigate to the frontend directory:

```bash
cd frontend
```

Install the dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Open the URL displayed in your terminal (typically):

http://localhost:5173

---

## 🔌 API Endpoints

The backend exposes the following REST API endpoints.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Check API status and currently loaded document |
| POST | `/upload` | Upload and process a document |
| POST | `/chat` | Ask questions about the uploaded document |

### 1. Health Check

```http
GET /health
```

Returns the backend status and currently loaded document information.

### 2. Upload Document

```http
POST /upload
```

Accepts a document using multipart form data.

Example:

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@document.pdf"
```

Example response:

```json
{
  "message": "File ready",
  "filename": "document.pdf",
  "chunks": 18
}
```

### 3. Ask a Question

```http
POST /chat
```

Accepts a question in JSON format.

Example:

```json
{
  "question": "What is the main topic of this document?"
}
```

Example response:

```json
{
  "answer": "The document discusses ...",
  "sources": [
    {
      "file": "document.pdf",
      "page": 2
    }
  ]
}
```

Page references are included when available. For document formats without page metadata, the source filename is returned.

---

## ⚠️ Current Limitations

- **Single Active Document:** Uploading a new document replaces the previously uploaded document.
- **No Multi-User Isolation:** The current backend maintains one active document and RAG chain per application process.
- **Database Reset on Startup:** The ChromaDB directory is cleared when the backend starts, so documents must be uploaded again after a restart.
- **No OCR Support:** Scanned PDFs and image-based documents cannot currently be processed.
- **Context-Based Generation:** Although the prompt instructs the LLM to answer only from retrieved context, generated responses should still be verified against the original document.

---

## 🔮 Future Improvements

- Support multiple documents and document collections.
- Implement persistent document indexing across application restarts.
- Add OCR support for scanned documents.
- Introduce user authentication and document-level isolation.
- Add conversation history and chat session management.
- Improve retrieval evaluation and RAG response quality.
- Add streaming responses for a more interactive chat experience.

---

## 👨‍💻 Author

**Gandharv Kulkarni**

- GitHub: [@gandharvk422](https://github.com/gandharvk422)

---

⭐ If you find this project useful, consider giving the repository a star!