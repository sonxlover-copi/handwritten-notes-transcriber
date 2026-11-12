"""Application settings, read from environment variables."""

import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
VISION_MODEL = os.getenv("VISION_MODEL", "qwen3-vl:8b")
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "20"))
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_IMAGE_SIDE = 1800
