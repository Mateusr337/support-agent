from pathlib import Path

import fitz

from app.rag.loaders.base import DocumentLoadResult, DocumentPage
from app.rag.loaders.ocr import ocr_image_bytes
from app.rag.loaders.utils import (
    merge_page_text,
    normalize_whitespace,
    ocr_overlaps_native,
)


class PdfDocumentLoader:
    def __init__(
        self,
        *,
        min_page_text: int = 50,
        min_image_px: int = 100,
        tesseract_lang: str = "eng",
        page_render_scale: float = 2.0,
    ) -> None:
        self._min_page_text = min_page_text
        self._min_image_px = min_image_px
        self._tesseract_lang = tesseract_lang
        self._page_render_scale = page_render_scale

    @property
    def name(self) -> str:
        return "pdf"

    def load(self, path: str | Path) -> DocumentLoadResult:
        pdf_path = Path(path)
        if not pdf_path.is_file():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        if pdf_path.suffix.lower() != ".pdf":
            raise ValueError(f"Not a PDF file: {pdf_path}")

        source = pdf_path.name
        pages: list[DocumentPage] = []

        with fitz.open(pdf_path) as document:
            total_pages = len(document)
            for page_index in range(total_pages):
                page_number = page_index + 1
                page = document[page_index]
                native = normalize_whitespace(page.get_text() or "")
                figure_ocr_parts = _ocr_embedded_images(
                    document,
                    page,
                    min_image_px=self._min_image_px,
                    tesseract_lang=self._tesseract_lang,
                )

                full_page_ocr = ""
                if len(native) < self._min_page_text:
                    full_page_ocr = _ocr_rendered_page(
                        page,
                        scale=self._page_render_scale,
                        tesseract_lang=self._tesseract_lang,
                    )
                    if ocr_overlaps_native(native, full_page_ocr):
                        full_page_ocr = ""

                merged = merge_page_text(
                    page_number=page_number,
                    native=native,
                    figure_ocr_parts=figure_ocr_parts,
                    full_page_ocr=full_page_ocr,
                )
                if _is_page_marker_only(merged):
                    continue

                pages.append(
                    DocumentPage(
                        text=merged,
                        page_number=page_number,
                        source=source,
                        has_native_text=bool(native),
                        has_ocr_text=bool(figure_ocr_parts or full_page_ocr),
                    )
                )

        return DocumentLoadResult(pages=tuple(pages), total_pages=total_pages)


def _ocr_embedded_images(
    document: fitz.Document,
    page: fitz.Page,
    *,
    min_image_px: int,
    tesseract_lang: str,
) -> list[str]:
    ocr_parts: list[str] = []

    for image_info in page.get_images(full=True):
        xref = image_info[0]
        try:
            extracted = document.extract_image(xref)
        except Exception:
            continue

        width = extracted.get("width", 0)
        height = extracted.get("height", 0)
        if width < min_image_px or height < min_image_px:
            continue

        image_bytes = extracted.get("image")
        if not image_bytes:
            continue

        ocr_text = normalize_whitespace(
            ocr_image_bytes(image_bytes, lang=tesseract_lang)
        )
        if ocr_text:
            ocr_parts.append(ocr_text)

    return ocr_parts


def _ocr_rendered_page(
    page: fitz.Page,
    *,
    scale: float,
    tesseract_lang: str,
) -> str:
    matrix = fitz.Matrix(scale, scale)
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
    return normalize_whitespace(
        ocr_image_bytes(pixmap.tobytes("png"), lang=tesseract_lang)
    )


def _is_page_marker_only(merged: str) -> bool:
    stripped = merged.strip()
    if not stripped:
        return True
    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    return len(lines) == 1 and lines[0].startswith("[Page ")
