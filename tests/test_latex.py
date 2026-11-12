from app.latex import make_latex, safe_math
from app.transcriber import ContentBlock, PageStructure


def test_latex_escapes_user_text_but_keeps_math() -> None:
    page = PageStructure(
        title="Вариант_2",
        blocks=[
            ContentBlock(kind="paragraph", text=r"Найдите \(f(x)=\sqrt{1+x^2}\)."),
        ],
    )

    source = make_latex([page], fallback_title="notes")

    assert r"Вариант\_2" in source
    assert r"\(f(x)=\sqrt{1+x^2}\)" in source


def test_unsafe_latex_command_becomes_a_review_marker() -> None:
    assert safe_math(r"\input{/etc/passwd}") == r"\text{[формула требует проверки]}"
    assert safe_math(r"\(x+y\)") == "x+y"
    assert safe_math(r"x^{2}}") == r"\text{[формула требует проверки]}"


def test_pdf_endpoint_returns_a_pdf_attachment(monkeypatch) -> None:
    from app.main import app
    from fastapi.testclient import TestClient

    monkeypatch.setattr("app.main.compile_pdf", lambda source: b"%PDF-demo")
    payload = {
        "filename": "notes.jpg",
        "pages": [
            {
                "page": 1,
                "title": "Заметки",
                "metadata": [],
                "blocks": [{"kind": "paragraph", "text": "Текст", "level": 1}],
            }
        ],
    }

    response = TestClient(app).post("/pdf", json=payload)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == b"%PDF-demo"
