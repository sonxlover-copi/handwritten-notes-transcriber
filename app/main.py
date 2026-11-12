"""Small FastAPI application for uploading and transcribing notes."""

from pathlib import Path

import fitz
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from ollama import ResponseError

from app.config import MAX_PDF_PAGES, MAX_UPLOAD_BYTES, VISION_MODEL
from app.transcriber import NotePage, image_pages, pdf_pages, transcribe_page

app = FastAPI(
    title="Расшифровка конспектов",
    description="Локальное распознавание рукописных заметок с помощью Ollama.",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory="static"), name="static")

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home() -> str:
    """Serve the minimal upload page."""
    return Path("static/index.html").read_text(encoding="utf-8")


@app.get("/health")
def health() -> dict[str, str]:
    """Return basic service information without making a model call."""
    return {"status": "ok", "model": VISION_MODEL}


def _get_pages(filename: str, file_bytes: bytes) -> list[NotePage]:
    """Validate file type and convert supported input to page images."""
    extension = Path(filename).suffix.lower()

    try:
        if extension == ".pdf":
            return pdf_pages(file_bytes, MAX_PDF_PAGES)
        if extension in IMAGE_EXTENSIONS:
            return image_pages(file_bytes)
    except (fitz.FileDataError, OSError) as exc:
        raise HTTPException(status_code=400, detail="Не удалось прочитать файл.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    raise HTTPException(
        status_code=415,
        detail="Поддерживаются PDF, PNG, JPG, JPEG и WEBP.",
    )


@app.post("/transcribe")
def transcribe(file: UploadFile = File(...)) -> dict[str, object]:
    """Transcribe each page and return text with page numbers."""
    filename = file.filename or "uploaded-file"
    file_bytes = file.file.read(MAX_UPLOAD_BYTES + 1)

    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Размер файла не должен превышать 20 МБ.")

    pages = _get_pages(filename, file_bytes)
    if not pages:
        raise HTTPException(status_code=400, detail="В файле не найдено страниц.")

    results = []
    for page in pages:
        try:
            text = transcribe_page(page)
        except ResponseError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Ollama не смог обработать страницу. Проверьте, что загружена модель {VISION_MODEL}.",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail="Нет соединения с Ollama. Проверьте, что контейнер Ollama запущен.",
            ) from exc

        results.append({"page": page.number, "text": text})

    return {"filename": filename, "pages": results}
