"""Load Markdown/text files, split them into chunks, and persist embeddings."""

import hashlib
from pathlib import Path

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import (
    CHROMA_DIR,
    COLLECTION_NAME,
    DOCS_DIR,
    EMBEDDING_MODEL,
    OLLAMA_BASE_URL,
)


def get_vector_store() -> Chroma:
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR),
    )


def ingest_documents(docs_dir: Path = DOCS_DIR) -> int:
    files = sorted([*docs_dir.rglob("*.md"), *docs_dir.rglob("*.txt")])
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    store = get_vector_store()
    indexed = 0

    for file_path in files:
        text = file_path.read_text(encoding="utf-8").strip()
        if not text:
            continue

        source = file_path.relative_to(docs_dir).as_posix()
        chunks = splitter.create_documents([text], metadatas=[{"source": source}])
        # Replace this source's previous chunks so repeated runs are idempotent.
        try:
            store.delete(where={"source": source})
        except Exception:
            # A new Chroma collection has nothing to delete yet.
            pass

        ids = [
            hashlib.sha256(f"{source}:{i}:{chunk.page_content}".encode()).hexdigest()
            for i, chunk in enumerate(chunks)
        ]
        store.add_documents(chunks, ids=ids)
        indexed += len(chunks)

    return indexed


if __name__ == "__main__":
    count = ingest_documents()
    print(f"Indexed {count} chunks from {DOCS_DIR}")
