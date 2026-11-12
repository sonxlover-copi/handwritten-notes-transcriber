import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen2.5:3b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", "data/chroma"))
DOCS_DIR = Path(os.getenv("DOCS_DIR", "data/docs"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "local_knowledge")
TOP_K = int(os.getenv("TOP_K", "4"))
MIN_RELEVANCE = float(os.getenv("MIN_RELEVANCE", "0.15"))
