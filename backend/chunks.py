import csv
import io
import os
from pathlib import Path

from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pptx import Presentation


# ---------------------------------------------------------------------------
# One small loader per file type. Each returns a list of Documents with
# metadata["source"] set; PDFs and slides also set metadata["page"] (0-based).
# ---------------------------------------------------------------------------
def _read_text(path):
    """Read a text file, trying UTF-8 first and then Windows-1252."""
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            with open(path, encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise ValueError("Couldn't read this file's text. Save it as UTF-8 and try again.")


def _load_pdf(path):
    if os.getenv("PDF_LOADER") == "pdfium":
        return PyPDFLoader(path).load()
    try:
        from langchain_community.document_loaders import PyPDFium2Loader
        return PyPDFium2Loader(path).load()
    except Exception:
        return PyPDFLoader(path).load()


def _load_docx(path):
    return Docx2txtLoader(path).load()


def _load_text(path):
    return [Document(page_content=_read_text(path), metadata={"source": path})]


def _load_csv(path):
    """One Document per row, written as 'column: value' lines."""
    rows = csv.DictReader(io.StringIO(_read_text(path)))
    docs = []
    for i, row in enumerate(rows):
        text = "\n".join(f"{k}: {v}" for k, v in row.items() if k and v)
        if text:
            docs.append(Document(page_content=text, metadata={"source": path, "row": i + 2}))
    return docs


def _load_pptx(path):
    """One Document per slide (stored as 'page', so the UI shows the slide number)."""
    docs = []
    for i, slide in enumerate(Presentation(path).slides):
        parts = []
        for shape in slide.shapes:
            if shape.has_text_frame and shape.text_frame.text.strip():
                parts.append(shape.text_frame.text.strip())
            if getattr(shape, "has_table", False) and shape.has_table:
                for row in shape.table.rows:
                    parts.append(" | ".join(cell.text.strip() for cell in row.cells))
        if parts:
            docs.append(Document(page_content="\n".join(parts), metadata={"source": path, "page": i}))
    return docs


LOADERS = {
    ".pdf": _load_pdf,
    ".docx": _load_docx,
    ".pptx": _load_pptx,
    ".txt": _load_text,
    ".md": _load_text,
    ".csv": _load_csv,
}
SUPPORTED_EXTENSIONS = set(LOADERS)


def validate_file(path):
    """Check the real content matches the extension. Returns an error message, or None if OK."""
    ext = Path(path).suffix.lower()
    with open(path, "rb") as f:
        head = f.read(4096)

    if ext == ".pdf":
        return None if head.startswith(b"%PDF-") else "This file isn't a valid PDF."
    if ext in (".docx", ".pptx"):  # both are zip files
        return None if head.startswith(b"PK") else f"This file isn't a valid {ext[1:].upper()} document."
    if b"\x00" in head:  # text files never contain NUL bytes
        return "This doesn't look like a plain text file. Save it as UTF-8 text and try again."
    return None


def fetch_doc(file):
    """Load a file with the loader for its extension -> list of Documents."""
    ext = Path(file).suffix.lower()
    if ext not in LOADERS:
        raise ValueError(f"Unsupported file type: {ext or 'unknown'}")
    return LOADERS[ext](file)


def chunk_doc(docs):
    """Split the Documents into smaller chunk Documents."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=int(os.getenv("CHUNK_SIZE", "800")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "100")),
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(docs)