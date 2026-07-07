import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.rag.loaders.factory import (
    UnsupportedDocumentExtensionError,
    get_document_loader,
    get_document_loader_for_extension,
    get_document_loader_for_path,
    supported_extensions,
)
from app.rag.loaders.pdf import PdfDocumentLoader


@patch("app.rag.loaders.factory.settings")
def test_get_document_loader_for_extension_returns_pdf_loader(mock_settings):
    mock_settings.rag_ocr_min_page_text = 50
    mock_settings.rag_ocr_min_image_px = 100
    mock_settings.rag_tesseract_lang = "eng"

    loader = get_document_loader_for_extension(".pdf")

    assert isinstance(loader, PdfDocumentLoader)
    assert loader.name == "pdf"


@patch("app.rag.loaders.factory.settings")
def test_get_document_loader_for_path_uses_file_suffix(mock_settings):
    mock_settings.rag_ocr_min_page_text = 50
    mock_settings.rag_ocr_min_image_px = 100
    mock_settings.rag_tesseract_lang = "eng"

    loader = get_document_loader_for_path("manual.pdf")

    assert isinstance(loader, PdfDocumentLoader)


@patch("app.rag.loaders.factory.settings")
def test_get_document_loader_returns_pdf_loader(mock_settings):
    mock_settings.rag_ocr_min_page_text = 50
    mock_settings.rag_ocr_min_image_px = 100
    mock_settings.rag_tesseract_lang = "eng"

    loader = get_document_loader()

    assert isinstance(loader, PdfDocumentLoader)


def test_get_document_loader_for_extension_raises_for_unsupported_extension():
    with pytest.raises(UnsupportedDocumentExtensionError, match="Unsupported document extension"):
        get_document_loader_for_extension(".docx")


def test_supported_extensions_lists_registered_extensions():
    assert supported_extensions() == (".pdf",)
