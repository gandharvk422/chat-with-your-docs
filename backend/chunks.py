from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def fetch_doc(file):
    """Load a PDF and return a list of Documents (one per page)."""
    loader = PyPDFLoader(file)
    return loader.load()

def chunk_doc(file):
    """Split the page Documents into smaller chunk Documents."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(file)