from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.rag.loaders.pdf import PdfDocumentLoader


@pytest.fixture()
def loader() -> PdfDocumentLoader:
    return PdfDocumentLoader(
        min_page_text=50,
        min_image_px=100,
        tesseract_lang="eng",
    )


def test_pdf_document_loader_name(loader: PdfDocumentLoader):
    assert loader.name == "pdf"


def test_load_pdf_merges_native_and_ocr(loader: PdfDocumentLoader, tmp_path: Path):
    pdf_path = tmp_path / "manual.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    mock_page = MagicMock()
    mock_document = MagicMock()
    mock_document.__enter__ = MagicMock(return_value=mock_document)
    mock_document.__exit__ = MagicMock(return_value=False)
    mock_document.__len__ = MagicMock(return_value=1)
    mock_document.__getitem__ = MagicMock(return_value=mock_page)

    with (
        patch("app.rag.loaders.pdf.fitz.open", return_value=mock_document),
        patch(
            "app.rag.loaders.pdf._ocr_embedded_images",
            return_value=["USB port rear panel"],
        ),
        patch("app.rag.loaders.pdf._ocr_rendered_page", return_value=""),
    ):
        mock_page.get_text.return_value = "Connect the USB cable."
        result = loader.load(pdf_path)

    assert result.total_pages == 1
    assert len(result.pages) == 1
    assert result.pages[0].page_number == 1
    assert result.pages[0].content_type == "mixed"
    assert "[Native]" in result.pages[0].text
    assert "USB port rear panel" in result.pages[0].text


def test_load_pdf_uses_full_page_ocr_when_native_is_sparse(
    loader: PdfDocumentLoader,
    tmp_path: Path,
):
    pdf_path = tmp_path / "diagram.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    mock_page = MagicMock()
    mock_document = MagicMock()
    mock_document.__enter__ = MagicMock(return_value=mock_document)
    mock_document.__exit__ = MagicMock(return_value=False)
    mock_document.__len__ = MagicMock(return_value=1)
    mock_document.__getitem__ = MagicMock(return_value=mock_page)

    with (
        patch("app.rag.loaders.pdf.fitz.open", return_value=mock_document),
        patch("app.rag.loaders.pdf._ocr_embedded_images", return_value=[]),
        patch(
            "app.rag.loaders.pdf._ocr_rendered_page",
            return_value="Blinking amber light means paper jam",
        ),
    ):
        mock_page.get_text.return_value = ""
        result = loader.load(pdf_path)

    assert len(result.pages) == 1
    assert result.pages[0].content_type == "ocr"
    assert "Blinking amber light means paper jam" in result.pages[0].text


def test_load_pdf_skips_page_when_no_content_extracted(
    loader: PdfDocumentLoader,
    tmp_path: Path,
):
    pdf_path = tmp_path / "empty.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    mock_page = MagicMock()
    mock_document = MagicMock()
    mock_document.__enter__ = MagicMock(return_value=mock_document)
    mock_document.__exit__ = MagicMock(return_value=False)
    mock_document.__len__ = MagicMock(return_value=1)
    mock_document.__getitem__ = MagicMock(return_value=mock_page)

    with (
        patch("app.rag.loaders.pdf.fitz.open", return_value=mock_document),
        patch("app.rag.loaders.pdf._ocr_embedded_images", return_value=[]),
        patch("app.rag.loaders.pdf._ocr_rendered_page", return_value=""),
    ):
        mock_page.get_text.return_value = ""
        result = loader.load(pdf_path)

    assert result.pages == ()
    assert result.total_pages == 1
    assert result.pages_skipped == 1


def test_load_pdf_raises_when_file_is_missing(loader: PdfDocumentLoader, tmp_path: Path):
    missing_path = tmp_path / "missing.pdf"

    with pytest.raises(FileNotFoundError, match="PDF not found"):
        loader.load(missing_path)


def test_load_pdf_raises_when_extension_is_not_pdf(loader: PdfDocumentLoader, tmp_path: Path):
    text_file = tmp_path / "notes.txt"
    text_file.write_text("not a pdf", encoding="utf-8")

    with pytest.raises(ValueError, match="Not a PDF file"):
        loader.load(text_file)
