from dotenv import load_dotenv

import logging
import os
import shutil
import tempfile
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from chain import build_chain
from chunks import SUPPORTED_EXTENSIONS, validate_file
from embed import embed_and_store, get_embeddings, reset_db
from hybrid import build_hybrid_reranker, get_cross_encoder

load_dotenv()

logger = logging.getLogger("uvicorn.error")

MAX_MB = 20
LEGACY_HINTS = {
    ".doc": "Save it as .docx and try again.",
    ".ppt": "Save it as .pptx and try again.",
    ".xls": "Export it as .csv and try again.",
    ".xlsx": "Export it as .csv and try again.",
}


def unsupported_message(ext):
    supported = ", ".join(e[1:].upper() for e in sorted(SUPPORTED_EXTENSIONS))
    return f"Unsupported file type. Supported: {supported}. {LEGACY_HINTS.get(ext, '')}".strip()
upload_lock = threading.Lock()  # only one upload is processed at a time


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- Runs ONCE when the server starts ----
    reset_db()  # start with a clean database (nothing has it open yet)

    print("Loading models (the first run downloads them)...")
    get_embeddings()
    get_cross_encoder()
    print("Models ready.")

    # Holds the current document's data (filled by /upload)
    app.state.doc_name = None
    app.state.vectorstore = None
    app.state.chunks = None
    app.state.chain = None
    app.state.rerank = None

    yield


app = FastAPI(title="Chat with Your Docs API", lifespan=lifespan)

# Allow the React dev server to call this API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Check that the server is running and a document is loaded."""
    return {
        "status": "ok",
        "models_loaded": True,
        "document": app.state.doc_name,
    }


# Plain `def` (not `async def`): FastAPI runs it in a worker thread, so the slow
# embedding work doesn't freeze the rest of the server (e.g. /health).
@app.post("/upload")
def upload(file: UploadFile = File(...)):
    name = Path(file.filename or "").name  # drops any folder part of the name
    ext = Path(name).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(400, unsupported_message(ext))

    # Save under the ORIGINAL file name so citations show it, not a temp name
    tmp_dir = tempfile.mkdtemp()
    path = os.path.join(tmp_dir, name)

    try:
        # 1. Save to disk, enforcing the size limit
        size = 0
        with open(path, "wb") as out:
            while block := file.file.read(1024 * 1024):
                size += len(block)
                if size > MAX_MB * 1024 * 1024:
                    raise HTTPException(413, f"That file is larger than {MAX_MB} MB.")
                out.write(block)

        # 2. Check the real content, not just the name
        problem = validate_file(path)
        if problem:
            raise HTTPException(400, problem)

        # 3. Load, chunk, embed, store, then build the chain and reranker
        with upload_lock:
            vectorstore, chunks = embed_and_store(path)
            rerank = build_hybrid_reranker(chunks, vectorstore)
            chain = build_chain(lambda q: [doc for _, doc in rerank(q, top_n=4)])

            # Swap in the new document only after everything succeeded
            old_store = app.state.vectorstore
            app.state.doc_name = name
            app.state.vectorstore = vectorstore
            app.state.chunks = chunks
            app.state.chain = chain
            app.state.rerank = rerank

            if old_store is not None:
                try:
                    old_store.delete_collection()
                except Exception:
                    logger.warning("Could not delete the previous collection")

        return {"message": "File ready", "filename": name, "chunks": len(chunks)}

    except HTTPException:
        raise
    except ValueError as e:  # e.g. no readable text
        raise HTTPException(422, str(e))
    except Exception:
        logger.exception("Upload failed")
        raise HTTPException(500, "Something went wrong while reading your document. Try again.")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)


@app.post("/chat")
def chat(req: ChatRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "Type a question first.")

    chain = app.state.chain  # read once, so a new upload can't swap it mid-request
    if chain is None:
        raise HTTPException(400, "Upload a document before asking a question.")

    try:
        return chain.invoke(question)  # {"answer": ..., "sources": [...]}
    except Exception:
        logger.exception("Chat failed")
        raise HTTPException(500, "The AI service couldn't answer right now. Try again in a moment.")