"""Turn image or PDF pages into text with a local vision model."""

from dataclasses import dataclass
from io import BytesIO

import fitz
from ollama import Client
from PIL import Image, ImageOps

from app.config import MAX_IMAGE_SIDE, OLLAMA_BASE_URL, VISION_MODEL

# Keep the client in one place. Ollama runs in its own Compose service.
ollama = Client(host=OLLAMA_BASE_URL, timeout=300.0)

TRANSCRIPTION_PROMPT = """Дословно перепиши рукописный текст с этой страницы на языке оригинала.

Правила:
- Сохраняй слова и формулировки автора, не пересказывай и не исправляй стиль.
- Сохраняй заголовки, абзацы, списки и порядок текста; используй Markdown.
- Формулы записывай в LaTeX, только если можешь разобрать их уверенно.
- Неразборчивые слова и части формул отмечай как ⟦неразборчиво⟧.
- Не добавляй вступлений, пояснений или текста, которого нет на странице.
- Верни только расшифровку страницы.
"""


@dataclass
class NotePage:
    """One page prepared for OCR."""

    number: int
    image: bytes


def _encode_image(image: Image.Image) -> bytes:
    """Normalize orientation and size while keeping the original page readable."""
    image = ImageOps.exif_transpose(image).convert("RGB")
    longest_side = max(image.size)

    # Very large phone photos use more memory. Resize only when necessary.
    if longest_side > MAX_IMAGE_SIDE:
        scale = MAX_IMAGE_SIDE / longest_side
        new_size = (round(image.width * scale), round(image.height * scale))
        image = image.resize(new_size, Image.Resampling.LANCZOS)

    output = BytesIO()
    image.save(output, format="JPEG", quality=95)
    return output.getvalue()


def image_pages(file_bytes: bytes) -> list[NotePage]:
    """Open a supported image and return it as a single normalized page."""
    with Image.open(BytesIO(file_bytes)) as image:
        return [NotePage(number=1, image=_encode_image(image))]


def pdf_pages(file_bytes: bytes, max_pages: int) -> list[NotePage]:
    """Render PDF pages to images because handwritten notes are often scans."""
    pages: list[NotePage] = []
    document = fitz.open(stream=file_bytes, filetype="pdf")

    if document.page_count > max_pages:
        raise ValueError(f"В PDF {document.page_count} страниц; лимит — {max_pages}.")

    for page_index, page in enumerate(document):
        # 2x renders at about 144 DPI, which is readable without huge images.
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        pages.append(NotePage(number=page_index + 1, image=_encode_image(image)))

    return pages


def transcribe_page(page: NotePage) -> str:
    """Ask the local vision model to transcribe one page."""
    response = ollama.chat(
        model=VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": TRANSCRIPTION_PROMPT,
                "images": [page.image],
            }
        ],
        options={"temperature": 0, "num_predict": 2500, "num_ctx": 8192},
    )
    return response.message.content.strip()
