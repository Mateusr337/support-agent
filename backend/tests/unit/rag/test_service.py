import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rag.chunking import TextChunk
from app.rag.service import DEFAULT_SEARCH_SCORE_THRESHOLD, IngestReport, RagService, get_rag_service
from app.tools.base import RetrievedChunk


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
def service(vector_repository, embedding_provider):
    return RagService(
        vector_repository=vector_repository,
        embedding_provider=embedding_provider,
        embed_batch_size=2,
    )


def test_ingest_directory_raises_for_missing_directory(service):
    with pytest.raises(NotADirectoryError, match="Not a directory"):
        asyncio.run(service.ingest_directory(Path("/missing/dir")))


def test_ingest_directory_returns_empty_report_when_no_pdfs(service, tmp_path: Path):
    report = asyncio.run(service.ingest_directory(tmp_path))

    assert report == IngestReport()
    service._vector_repository.ensure_collection.assert_called_once_with(1536)


def test_ingest_directory_uses_recreate_when_force(service, tmp_path: Path):
    asyncio.run(service.ingest_directory(tmp_path, force=True))

    service._vector_repository.recreate_collection.assert_called_once_with(1536)
    service._vector_repository.ensure_collection.assert_not_called()


@patch("app.rag.service.load_pdf")
def test_ingest_directory_indexes_pdfs(mock_load_pdf, service, tmp_path: Path):
    pdf_path = tmp_path / "manual.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    mock_load_pdf.return_value = [
        MagicMock(text="Reset steps", page_number=1, source="manual.pdf")
    ]

    report = asyncio.run(service.ingest_directory(tmp_path))

    assert report.files_processed == 1
    assert report.chunks_indexed == 1
    service._vector_repository.delete_by_doc_id.assert_called_once_with("manual.pdf")
    service._vector_repository.upsert.assert_called_once()


@patch("app.rag.service.load_pdf")
def test_ingest_directory_skips_blank_pdfs(mock_load_pdf, service, tmp_path: Path):
    pdf_path = tmp_path / "blank.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    mock_load_pdf.return_value = []

    report = asyncio.run(service.ingest_directory(tmp_path))

    assert report == IngestReport(skipped_files=("blank.pdf",))
    service._vector_repository.upsert.assert_not_called()


@patch("app.rag.service.load_pdf")
def test_ingest_directory_collects_errors(mock_load_pdf, service, tmp_path: Path):
    good_pdf = tmp_path / "good.pdf"
    bad_pdf = tmp_path / "bad.pdf"
    good_pdf.write_bytes(b"%PDF-1.4")
    bad_pdf.write_bytes(b"%PDF-1.4")

    def load_pdf_side_effect(path: Path):
        if path.name == "good.pdf":
            return [MagicMock(text="Content", page_number=1, source="good.pdf")]
        raise FileNotFoundError("PDF not found")

    mock_load_pdf.side_effect = load_pdf_side_effect

    report = asyncio.run(service.ingest_directory(tmp_path))

    assert report.files_processed == 1
    assert report.chunks_indexed == 1
    assert report.errors == ("bad.pdf: PDF not found",)


def test_ingest_file_ensures_collection_before_index(service, tmp_path: Path):
    pdf_path = tmp_path / "manual.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    with patch("app.rag.service.load_pdf") as mock_load_pdf:
        mock_load_pdf.return_value = [
            MagicMock(text="Setup guide", page_number=1, source="manual.pdf")
        ]
        indexed = asyncio.run(service.ingest_file(pdf_path))

    assert indexed == 1
    service._vector_repository.ensure_collection.assert_called_once_with(1536)


def test_search_returns_retrieved_chunks(service, vector_repository, embedding_provider):
    embedding_provider.embed = AsyncMock(return_value=[[0.5, 0.6]])
    vector_repository.search.return_value = [
        MagicMock(text="Reset steps", source="manual.pdf", score=0.91, page_number=2)
    ]

    chunks = asyncio.run(service.search("reset printer", top_k=3))

    embedding_provider.embed.assert_awaited_once_with(["reset printer"])
    vector_repository.search.assert_called_once_with(
        [0.5, 0.6],
        top_k=3,
        score_threshold=DEFAULT_SEARCH_SCORE_THRESHOLD,
    )
    assert chunks == [
        RetrievedChunk(
            text="Reset steps",
            source="manual.pdf",
            page_number=2,
            score=0.91,
        )
    ]


def test_search_uses_explicit_score_threshold(service, vector_repository, embedding_provider):
    embedding_provider.embed = AsyncMock(return_value=[[0.5, 0.6]])
    vector_repository.search.return_value = []

    asyncio.run(service.search("reset printer", top_k=3, score_threshold=0.45))

    vector_repository.search.assert_called_once_with(
        [0.5, 0.6],
        top_k=3,
        score_threshold=0.45,
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

    point = service._to_vector_point(
        doc_id="manual.pdf",
        chunk=chunk,
        vector=[0.1, 0.2],
    )

    assert point.vector == [0.1, 0.2]
    assert point.payload == {
        "text": "Reset steps",
        "source": "manual.pdf",
        "page_number": 2,
        "chunk_index": 0,
        "doc_id": "manual.pdf",
    }
    assert point.id == service._to_vector_point(
        doc_id="manual.pdf",
        chunk=chunk,
        vector=[9.9, 9.9],
    ).id


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
