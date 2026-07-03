import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from app.rag.service import IngestReport
from app.scripts import ingest_documents


@patch("app.scripts.ingest_documents.get_rag_service")
def test_main_uses_default_documents_dir(mock_get_rag_service, tmp_path: Path, capsys):
    documents_dir = tmp_path / "documents"
    documents_dir.mkdir()
    mock_service = MagicMock()
    mock_service.ingest_directory = AsyncMock(
        return_value=IngestReport(files_processed=1, chunks_indexed=3)
    )
    mock_get_rag_service.return_value = mock_service

    with patch.object(ingest_documents.settings, "documents_dir", str(documents_dir)):
        with patch.object(ingest_documents.sys, "argv", ["ingest_documents"]):
            with patch.object(ingest_documents.sys, "exit") as mock_exit:
                ingest_documents.main()

    mock_service.ingest_directory.assert_awaited_once_with(documents_dir, force=False)
    mock_exit.assert_called_once_with(0)
    output = capsys.readouterr().out
    assert "Files indexed: 1" in output
    assert "Chunks indexed: 3" in output


@patch("app.scripts.ingest_documents.get_rag_service")
def test_main_accepts_custom_path_and_force(mock_get_rag_service, tmp_path: Path):
    custom_dir = tmp_path / "custom"
    custom_dir.mkdir()
    mock_service = MagicMock()
    mock_service.ingest_directory = AsyncMock(return_value=IngestReport())
    mock_get_rag_service.return_value = mock_service

    with patch.object(
        ingest_documents.sys,
        "argv",
        ["ingest_documents", "--path", str(custom_dir), "--force"],
    ):
        with patch.object(ingest_documents.sys, "exit") as mock_exit:
            ingest_documents.main()

    mock_service.ingest_directory.assert_awaited_once_with(custom_dir, force=True)
    mock_exit.assert_called_once_with(0)


@patch("app.scripts.ingest_documents.get_rag_service")
def test_main_exits_with_error_when_directory_missing(mock_get_rag_service, tmp_path: Path):
    missing_dir = tmp_path / "missing"

    with patch.object(
        ingest_documents.sys,
        "argv",
        ["ingest_documents", "--path", str(missing_dir)],
    ):
        with patch.object(ingest_documents.sys, "exit") as mock_exit:
            ingest_documents.main()

    mock_get_rag_service.assert_not_called()
    mock_exit.assert_called_once_with(1)


@patch("app.scripts.ingest_documents.get_rag_service")
def test_main_exits_with_error_when_ingest_has_errors(mock_get_rag_service, tmp_path: Path):
    documents_dir = tmp_path / "documents"
    documents_dir.mkdir()
    mock_service = MagicMock()
    mock_service.ingest_directory = AsyncMock(
        return_value=IngestReport(errors=("bad.pdf: failed",))
    )
    mock_get_rag_service.return_value = mock_service

    with patch.object(
        ingest_documents.sys,
        "argv",
        ["ingest_documents", "--path", str(documents_dir)],
    ):
        with patch.object(ingest_documents.sys, "exit") as mock_exit:
            ingest_documents.main()

    mock_exit.assert_called_once_with(1)
