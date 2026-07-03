from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True)
class DocumentPage:
    text: str
    page_number: int
    source: str


def load_pdf(path: str | Path) -> list[DocumentPage]:
    pdf_path = Path(path)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Not a PDF file: {pdf_path}")

    reader = PdfReader(pdf_path)
    source = pdf_path.name
    pages: list[DocumentPage] = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        pages.append(
            DocumentPage(
                text=text,
                page_number=page_number,
                source=source,
            )
        )

    return pages
