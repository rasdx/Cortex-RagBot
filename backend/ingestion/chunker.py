"""
Splits documents into overlapping text chunks.
Section 7 contract: split_documents(docs) -> list[Chunk]
Uses RecursiveCharacterTextSplitter to keep semantic boundaries intact (Section 1).
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from config import CHUNK_SIZE, CHUNK_OVERLAP


def split_documents(docs: list[Document]) -> list[Document]:
    """Split documents into chunks (~500-800 tokens, 10-15% overlap per Section 1)."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(docs)

    # Assign a stable chunk ID so dense and sparse indexes can be merged later (Section 1).
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = f"chunk_{i}"

    return chunks
