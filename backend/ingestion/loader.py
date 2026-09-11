"""
Reads raw files from data/raw and returns plain text per document.
Section 7 contract: load_documents(dir) -> list[Document]
Uses LangChain document loaders so multiple file types are supported
(PDF, DOCX, TXT, MD, CSV) rather than a single raw open()/read().
"""

import os

from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    CSVLoader,
)
from langchain_core.documents import Document

# One loader class per supported extension. Add a new entry here to support
# another file type — no other code in this file needs to change.
_LOADER_BY_EXTENSION = {
    ".pdf": PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".txt": TextLoader,
    ".md": TextLoader,
    ".csv": CSVLoader,
}


def load_documents(dir: str) -> list[Document]:
    """Read every supported file in `dir` and return one or more Documents per file
    (e.g. a multi-page PDF returns one Document per page)."""
    documents = []

    for filename in sorted(os.listdir(dir)):
        file_path = os.path.join(dir, filename)

        if not os.path.isfile(file_path):
            continue

        ext = os.path.splitext(filename)[1].lower()
        loader_cls = _LOADER_BY_EXTENSION.get(ext)

        if loader_cls is None:
            continue  # unsupported file type — skip rather than error the whole batch

        loader = loader_cls(file_path)
        documents.extend(loader.load())

    return documents
