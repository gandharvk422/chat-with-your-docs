from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def fetch_pdf(file):
    """Load a PDF and return a list of Documents (one per page)."""
    loader = PyPDFLoader(file)
    return loader.load()

def chunk_pdf(pdf):
    """Split the page Documents into smaller chunk Documents."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(pdf)


if __name__ == "__main__":
    pdf = fetch_pdf("test.pdf")
    chunks = chunk_pdf(pdf)

    print(f"{len(pdf)} pages -> {len(chunks)} chunks")
    print(chunks[0].page_content[:200])
    print(chunks[0].metadata)