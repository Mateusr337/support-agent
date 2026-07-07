import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rag.chunking import TextChunk
from app.rag.corpus import LAPTOP_MANUAL_FILENAME, PRINTER_MANUAL_FILENAME
from app.rag.loaders.base import DocumentLoadResult, DocumentPage
from app.rag.manifest import MANIFEST_FILENAME, DocumentManifestEntry
from app.repositories.vector_repository import VectorChunkPayload
from app.rag.service import FileIngestStats, IngestReport, RagService, get_rag_service
from app.tools.base import RetrievedChunk

LAPTOP_ENTRY = DocumentManifestEntry(
    filename=LAPTOP_MANUAL_FILENAME,
    product_name="OMEN 17.3 inch Gaming Laptop PC",
    product_type="laptop",
)
PRINTER_ENTRY = DocumentManifestEntry(
    filename=PRINTER_MANUAL_FILENAME,
    product_name="HP ENVY 6000 All-in-One series",
    product_type="printer",
)


@pytest.fixture()
def vector_repository():
    return MagicMock()


@pytest.fixture()
def embedding_provider():
    async def embed(texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2] for _ in texts]

    provider = MagicMock()
    provider.dimension = 1536
    provider.embed = AsyncMock(side_effect=embed)
    return provider


@pytest.fixture()
def document_loader():
    loader = MagicMock()
    loader.name = "pdf"
    return loader


@pytest.fixture()
def loader_for_path(document_loader):
    return lambda _path: document_loader


@pytest.fixture()
def service(vector_repository, embedding_provider, loader_for_path):
    return RagService(
        vector_repository=vector_repository,
        embedding_provider=embedding_provider,
        loader_for_path=loader_for_path,
        embed_batch_size=2,
    )


def _load_result(*pages: DocumentPage, total_pages: int | None = None) -> DocumentLoadResult:
    page_list = list(pages)
    return DocumentLoadResult(
        pages=tuple(page_list),
        total_pages=total_pages if total_pages is not None else len(page_list),
    )


def _write_manifest(directory: Path, documents: list[dict]) -> None:
    (directory / MANIFEST_FILENAME).write_text(
        json.dumps({"documents": documents}),
        encoding="utf-8",
    )


def test_ingest_directory_raises_for_missing_directory(service):
    with pytest.raises(NotADirectoryError, match="Not a directory"):
        asyncio.run(service.ingest_directory(Path("/missing/dir")))


def test_ingest_directory_returns_error_when_manifest_missing(service, tmp_path: Path):
    report = asyncio.run(service.ingest_directory(tmp_path))

    assert report.files_processed == 0
    assert len(report.errors) == 1
    assert MANIFEST_FILENAME in report.errors[0]
    service._vector_repository.ensure_collection.assert_called_once_with(1536)


def test_ingest_directory_returns_empty_report_when_manifest_has_no_documents(
    service,
    tmp_path: Path,
):
    _write_manifest(tmp_path, [])

    report = asyncio.run(service.ingest_directory(tmp_path))

    assert report == IngestReport()
    service._vector_repository.ensure_collection.assert_called_once_with(1536)


def test_ingest_directory_uses_recreate_when_force(service, tmp_path: Path):
    _write_manifest(tmp_path, [])

    asyncio.run(service.ingest_directory(tmp_path, force=True))

    service._vector_repository.recreate_collection.assert_called_once_with(1536)
    service._vector_repository.ensure_collection.assert_not_called()


def test_ingest_directory_indexes_manifest_documents(document_loader, service, tmp_path: Path):
    pdf_path = tmp_path / "manual.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    _write_manifest(
        tmp_path,
        [
            {
                "filename": "manual.pdf",
                "product_name": "OMEN Laptop",
                "product_type": "laptop",
            }
        ],
    )

    document_loader.load.return_value = _load_result(
        DocumentPage(
            text="Reset steps",
            page_number=1,
            source="manual.pdf",
            has_native_text=True,
        ),
        total_pages=1,
    )

    report = asyncio.run(service.ingest_directory(tmp_path))

    assert report.files_processed == 1
    assert report.chunks_indexed == 1
    assert report.pages_indexed == 1
    assert report.pages_native_only == 1
    assert len(report.file_stats) == 1
    service._vector_repository.delete_by_doc_id.assert_called_once_with("manual.pdf")
    service._vector_repository.upsert.assert_called_once()
    payload = service._vector_repository.upsert.call_args.args[0][0].payload
    assert payload.product_name == "OMEN Laptop"
    assert payload.product_type == "laptop"


def test_ingest_directory_skips_blank_documents(document_loader, service, tmp_path: Path):
    pdf_path = tmp_path / "blank.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    _write_manifest(
        tmp_path,
        [
            {
                "filename": "blank.pdf",
                "product_name": "Blank Product",
                "product_type": "unknown",
            }
        ],
    )
    document_loader.load.return_value = DocumentLoadResult(pages=(), total_pages=2)

    report = asyncio.run(service.ingest_directory(tmp_path))

    assert report.skipped_files == ("blank.pdf",)
    assert report.pages_skipped == 2
    assert report.file_stats[0].chunks_indexed == 0
    service._vector_repository.upsert.assert_not_called()


def test_ingest_directory_collects_errors(document_loader, service, tmp_path: Path):
    good_pdf = tmp_path / "good.pdf"
    bad_pdf = tmp_path / "bad.pdf"
    good_pdf.write_bytes(b"%PDF-1.4")
    bad_pdf.write_bytes(b"%PDF-1.4")
    _write_manifest(
        tmp_path,
        [
            {
                "filename": "good.pdf",
                "product_name": "Good Product",
                "product_type": "laptop",
            },
            {
                "filename": "bad.pdf",
                "product_name": "Bad Product",
                "product_type": "printer",
            },
        ],
    )

    def load_side_effect(path: Path):
        if path.name == "good.pdf":
            return _load_result(
                DocumentPage(
                    text="Content",
                    page_number=1,
                    source="good.pdf",
                    has_native_text=True,
                )
            )
        raise FileNotFoundError("PDF not found")

    document_loader.load.side_effect = load_side_effect

    report = asyncio.run(service.ingest_directory(tmp_path))

    assert report.files_processed == 1
    assert report.chunks_indexed == 1
    assert report.errors == ("bad.pdf: PDF not found",)


def test_ingest_directory_reports_missing_manifest_file(service, tmp_path: Path):
    _write_manifest(
        tmp_path,
        [
            {
                "filename": "missing.pdf",
                "product_name": "Missing Product",
                "product_type": "laptop",
            }
        ],
    )

    report = asyncio.run(service.ingest_directory(tmp_path))

    assert report.files_processed == 0
    assert report.errors == ("missing.pdf: file not found",)


def test_ingest_file_ensures_collection_before_index(document_loader, service, tmp_path: Path):
    pdf_path = tmp_path / "manual.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    _write_manifest(
        tmp_path,
        [
            {
                "filename": "manual.pdf",
                "product_name": "OMEN Laptop",
                "product_type": "laptop",
            }
        ],
    )

    document_loader.load.return_value = _load_result(
        DocumentPage(
            text="Setup guide",
            page_number=1,
            source="manual.pdf",
            has_native_text=True,
        )
    )
    indexed = asyncio.run(service.ingest_file(pdf_path))

    assert indexed == 1
    service._vector_repository.ensure_collection.assert_called_once_with(1536)


def test_search_returns_retrieved_chunks(service, vector_repository, embedding_provider):
    embedding_provider.embed = AsyncMock(return_value=[[0.5, 0.6]])
    vector_repository.search.return_value = [
        MagicMock(
            text="Reset steps",
            source="manual.pdf",
            score=0.91,
            page_number=2,
            product_name="OMEN Laptop",
            product_type="laptop",
        )
    ]

    chunks = asyncio.run(service.search("reset printer", top_k=3))

    embedding_provider.embed.assert_awaited_once_with(["reset printer"])
    vector_repository.search.assert_called_once_with(
        [0.5, 0.6],
        top_k=3,
        score_threshold=None,
        product_name=None,
        product_type=None,
    )
    assert chunks == [
        RetrievedChunk(
            text="Reset steps",
            source="manual.pdf",
            page_number=2,
            score=0.91,
            product_name="OMEN Laptop",
            product_type="laptop",
        )
    ]


def test_search_passes_explicit_score_threshold(service, vector_repository, embedding_provider):
    embedding_provider.embed = AsyncMock(return_value=[[0.5, 0.6]])
    vector_repository.search.return_value = []

    asyncio.run(service.search("reset printer", top_k=3, score_threshold=0.45))

    vector_repository.search.assert_called_once_with(
        [0.5, 0.6],
        top_k=3,
        score_threshold=0.45,
        product_name=None,
        product_type=None,
    )


def test_search_passes_product_filters(service, vector_repository, embedding_provider):
    embedding_provider.embed = AsyncMock(return_value=[[0.5, 0.6]])
    vector_repository.search.return_value = []

    asyncio.run(
        service.search(
            "reset printer",
            product_name="HP ENVY 6000 All-in-One series",
            product_type="printer",
        )
    )

    vector_repository.search.assert_called_once_with(
        [0.5, 0.6],
        top_k=5,
        score_threshold=None,
        product_name="HP ENVY 6000 All-in-One series",
        product_type="printer",
    )


def test_search_returns_empty_list_when_embedding_is_empty(service, embedding_provider):
    embedding_provider.embed = AsyncMock(return_value=[])

    chunks = asyncio.run(service.search("reset printer"))

    assert chunks == []


def test_to_vector_point_builds_stable_payload(service):
    chunk = TextChunk(
        text="Reset steps",
        source="manual.pdf",
        page_number=2,
        chunk_index=0,
    )
    entry = DocumentManifestEntry(
        filename="manual.pdf",
        product_name="OMEN Laptop",
        product_type="laptop",
    )

    point = service._to_vector_point(
        doc_id="manual.pdf",
        entry=entry,
        chunk=chunk,
        vector=[0.1, 0.2],
    )

    assert point.vector == [0.1, 0.2]
    assert point.payload == VectorChunkPayload(
        text="Source: OMEN Laptop (product type: laptop)\n\nReset steps",
        source="manual.pdf",
        page_number=2,
        chunk_index=0,
        doc_id="manual.pdf",
        content_type="native",
        product_name="OMEN Laptop",
        product_type="laptop",
    )
    assert point.id == service._to_vector_point(
        doc_id="manual.pdf",
        entry=entry,
        chunk=chunk,
        vector=[9.9, 9.9],
    ).id


def test_enrich_chunk_text_uses_manifest_metadata():
    laptop_text = RagService._enrich_chunk_text(
        product_name=LAPTOP_ENTRY.product_name,
        product_type=LAPTOP_ENTRY.product_type,
        text="Safety warning",
    )
    assert "product type: laptop" in laptop_text
    assert LAPTOP_ENTRY.product_name in laptop_text
    assert "Safety warning" in laptop_text

    printer_text = RagService._enrich_chunk_text(
        product_name=PRINTER_ENTRY.product_name,
        product_type=PRINTER_ENTRY.product_type,
        text="Quiet Mode",
    )
    assert "product type: printer" in printer_text
    assert PRINTER_ENTRY.product_name in printer_text


def test_ingest_file_falls_back_when_manifest_entry_missing(document_loader, service, tmp_path: Path):
    pdf_path = tmp_path / "standalone.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    _write_manifest(
        tmp_path,
        [
            {
                "filename": "other.pdf",
                "product_name": "Other Product",
                "product_type": "laptop",
            }
        ],
    )

    document_loader.load.return_value = _load_result(
        DocumentPage(
            text="Standalone content",
            page_number=1,
            source="standalone.pdf",
            has_native_text=True,
        )
    )

    indexed = asyncio.run(service.ingest_file(pdf_path))

    assert indexed == 1
    payload = service._vector_repository.upsert.call_args.args[0][0].payload
    assert payload.product_name == "standalone"
    assert payload.product_type == "unknown"


@patch("app.rag.service.get_embedding_provider")
@patch("app.rag.service.VectorRepository")
@patch("app.rag.service.settings")
def test_get_rag_service_builds_dependencies(
    mock_settings,
    mock_vector_repository,
    mock_get_embedding_provider,
):
    mock_settings.qdrant_collection = "support_documents"
    mock_get_embedding_provider.return_value = MagicMock()
    get_rag_service.cache_clear()

    service = get_rag_service()

    mock_vector_repository.assert_called_once_with(collection_name="support_documents")
    assert isinstance(service, RagService)

    get_rag_service.cache_clear()
