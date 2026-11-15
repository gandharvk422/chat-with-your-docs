import os
import shutil

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from chunks import fetch_pdf, chunk_pdf

DB_PATH = "./chroma_db"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

_embeddings = None


def get_embeddings():
    """Load the embedding model once and reuse it afterwards."""
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return _embeddings


def embed_and_store(file):
    """
    Run ONCE per uploaded PDF: load -> chunk -> embed -> store in ChromaDB.
    Deletes any existing database first (a new upload replaces the old one).

    Returns (vectorstore, chunks) so later steps can reuse them
    without re-reading or re-embedding the PDF.
    """
    chunks = chunk_pdf(fetch_pdf(file))

    if os.path.exists(DB_PATH):
        shutil.rmtree(DB_PATH)

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=get_embeddings(),
        persist_directory=DB_PATH,
    )
    return vectorstore, chunks


def load_vectorstore():
    """Open the existing ChromaDB from disk (no re-embedding)."""
    return Chroma(
        persist_directory=DB_PATH,
        embedding_function=get_embeddings(),
    )