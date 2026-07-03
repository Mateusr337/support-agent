from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.rag.loaders.pdf import DocumentPage, load_pdf


def test_load_pdf_extracts_non_empty_pages(tmp_path: Path):
    pdf_path = tmp_path / "manual.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 placeholder")

    mock_page_one = MagicMock()
    mock_page_one.extract_text.return_value = "Printer setup guide"
    mock_page_two = MagicMock()
    mock_page_two.extract_text.return_value = "   "
    mock_page_three = MagicMock()
    mock_page_three.extract_text.return_value = "Troubleshooting steps"

    mock_reader = MagicMock()
    mock_reader.pages = [mock_page_one, mock_page_two, mock_page_three]

    with patch("app.rag.loaders.pdf.PdfReader", return_value=mock_reader):
        pages = load_pdf(pdf_path)

    assert pages == [
        DocumentPage(
            text="Printer setup guide",
            page_number=1,
            source="manual.pdf",
        ),
        DocumentPage(
            text="Troubleshooting steps",
            page_number=3,
            source="manual.pdf",
        ),
    ]


def test_load_pdf_raises_when_file_is_missing(tmp_path: Path):
    missing_path = tmp_path / "missing.pdf"

    with pytest.raises(FileNotFoundError, match="PDF not found"):
        load_pdf(missing_path)


def test_load_pdf_raises_when_extension_is_not_pdf(tmp_path: Path):
    text_file = tmp_path / "notes.txt"
    text_file.write_text("not a pdf", encoding="utf-8")

    with pytest.raises(ValueError, match="Not a PDF file"):
        load_pdf(text_file)


def test_load_pdf_returns_empty_list_when_all_pages_are_blank(tmp_path: Path):
    pdf_path = tmp_path / "blank.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 placeholder")

    mock_page = MagicMock()
    mock_page.extract_text.return_value = ""
    mock_reader = MagicMock()
    mock_reader.pages = [mock_page]

    with patch("app.rag.loaders.pdf.PdfReader", return_value=mock_reader):
        pages = load_pdf(pdf_path)

    assert pages == []
