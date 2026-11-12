"""Small FastAPI application for uploading and transcribing notes."""

from pathlib import Path
from io import BytesIO
import subprocess
from urllib.parse import quote

import fitz
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from ollama import ResponseError
from pydantic import ValidationError

from app.config import MAX_PDF_PAGES, MAX_UPLOAD_BYTES, VISION_MODEL
from app.documents import DocumentPage, TranscribedDocument
from app.latex import compile_pdf, make_latex
from app.transcriber import NotePage, PageStructure, image_pages, pdf_pages, transcribe_page

app = FastAPI(
    title="Расшифровка конспектов в PDF",
    description="Локально распознаёт страницу, создаёт структурированный LaTeX и PDF.",
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
    """Extract structured page content and prepare its LaTeX source."""
    filename = file.filename or "uploaded-file"
    file_bytes = file.file.read(MAX_UPLOAD_BYTES + 1)

    if len(file_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Размер файла не должен превышать 20 МБ.")

    pages = _get_pages(filename, file_bytes)
    if not pages:
        raise HTTPException(status_code=400, detail="В файле не найдено страниц.")

    results: list[DocumentPage] = []
    for page in pages:
        try:
            structure = transcribe_page(page)
        except ResponseError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Ollama не смог обработать страницу. Проверьте, что загружена модель {VISION_MODEL}.",
            ) from exc
        except ValidationError as exc:
            raise HTTPException(
                status_code=502,
                detail="Модель вернула структуру, которую приложение не смогло разобрать.",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail="Нет соединения с Ollama. Проверьте, что контейнер Ollama запущен.",
            ) from exc

        results.append(DocumentPage(page=page.number, **structure.model_dump()))

    document = TranscribedDocument(filename=filename, pages=results)
    page_structures = [PageStructure(**page.model_dump(exclude={"page"})) for page in results]
    latex_source = make_latex(page_structures, fallback_title=Path(filename).stem)
    preview = "\n\n".join(
        "\n".join(
            ("# " + page.title if page.title else "", *page.metadata,
                *[block.text for block in page.blocks])
        ).strip()
        for page in page_structures
    )
    return {
        "document": document.model_dump(),
        "preview": preview,
        "latex_source": latex_source,
    }


@app.post("/pdf")
def create_pdf(document: TranscribedDocument) -> StreamingResponse:
    """Compile the reviewed transcription to a PDF attachment."""
    pages = [PageStructure(**page.model_dump(exclude={"page"})) for page in document.pages]
    latex_source = make_latex(pages, fallback_title=Path(document.filename).stem)

    try:
        pdf_bytes = compile_pdf(latex_source)
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(status_code=503, detail="Не удалось собрать PDF. Проверьте LaTeX-компилятор.") from exc

    filename = Path(document.filename).stem or "notes"
    ascii_filename = "notes.pdf"
    encoded_filename = quote(f"{filename}.pdf")
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{encoded_filename}",
        },
    )
