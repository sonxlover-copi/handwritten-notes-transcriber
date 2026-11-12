from io import BytesIO
from types import SimpleNamespace

import fitz
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.transcriber import NotePage, image_pages, pdf_pages


def test_image_pages_normalizes_an_image_to_jpeg() -> None:
    """A regular image becomes one page that can be sent to Ollama."""
    image = Image.new("RGB", (320, 200), color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")

    pages = image_pages(buffer.getvalue())

    assert len(pages) == 1
    assert pages[0].number == 1
    assert pages[0].image[:3] == b"\xff\xd8\xff"  # JPEG file signature


def test_pdf_pages_renders_each_page() -> None:
    """A two-page PDF should become two separate images with page numbers."""
    document = fitz.open()
    document.new_page()
    document.new_page()

    pages = pdf_pages(document.tobytes(), max_pages=5)

    assert [page.number for page in pages] == [1, 2]
    assert all(page.image[:3] == b"\xff\xd8\xff" for page in pages)


def test_transcribe_endpoint_returns_page_text(monkeypatch) -> None:
    """The API responds correctly without needing to start the local model."""
    monkeypatch.setattr(
        "app.main.transcribe_page",
        lambda page: f"Текст страницы {page.number}",
    )
    image = Image.new("RGB", (40, 30), color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")

    response = TestClient(app).post(
        "/transcribe",
        files={"file": ("notes.png", buffer.getvalue(), "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["pages"] == [{"page": 1, "text": "Текст страницы 1"}]


def test_transcribe_page_calls_ollama_with_image(monkeypatch) -> None:
    """The model receives the image and the transcription instructions."""
    from app import transcriber

    captured = {}

    def fake_chat(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(message=SimpleNamespace(content="Пример текста"))

    monkeypatch.setattr(transcriber.ollama, "chat", fake_chat)
    result = transcriber.transcribe_page(NotePage(number=1, image=b"jpeg"))

    assert result == "Пример текста"
    assert captured["model"] == transcriber.VISION_MODEL
    assert captured["messages"][0]["images"] == [b"jpeg"]
    assert "Дословно перепиши" in captured["messages"][0]["content"]
