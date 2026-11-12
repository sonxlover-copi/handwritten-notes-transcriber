"""API response models for extracted pages and generated documents."""

from pydantic import BaseModel

from app.transcriber import PageStructure


class DocumentPage(PageStructure):
    """Structured transcription plus its original page number."""

    page: int


class TranscribedDocument(BaseModel):
    """A complete upload, ready to review or export."""

    filename: str
    pages: list[DocumentPage]
