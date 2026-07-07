from collections.abc import Callable
from pathlib import Path

from app.core.config import settings
from app.rag.loaders.base import DocumentLoader
from app.rag.loaders.pdf import PdfDocumentLoader


class UnsupportedDocumentExtensionError(ValueError):
    pass


def _create_pdf_loader() -> DocumentLoader:
    return PdfDocumentLoader(
        min_page_text=settings.rag_ocr_min_page_text,
        min_image_px=settings.rag_ocr_min_image_px,
        tesseract_lang=settings.rag_tesseract_lang,
    )


_LOADER_FACTORIES: dict[str, Callable[[], DocumentLoader]] = {
    ".pdf": _create_pdf_loader,
}


def supported_extensions() -> tuple[str, ...]:
    return tuple(sorted(_LOADER_FACTORIES))


def get_document_loader_for_extension(extension: str) -> DocumentLoader:
    normalized = extension.lower() if extension.startswith(".") else f".{extension.lower()}"
    factory = _LOADER_FACTORIES.get(normalized)
    if factory is None:
        supported = ", ".join(supported_extensions())
        raise UnsupportedDocumentExtensionError(
            f"Unsupported document extension '{normalized}'. Supported: {supported}"
        )
    return factory()


def get_document_loader_for_path(path: str | Path) -> DocumentLoader:
    return get_document_loader_for_extension(Path(path).suffix)


def get_document_loader() -> DocumentLoader:
    return get_document_loader_for_extension(".pdf")
