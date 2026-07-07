import argparse
import asyncio
import sys
from pathlib import Path

from app.core.config import settings
from app.rag.loaders.factory import supported_extensions
from app.rag.service import FileIngestStats, IngestReport, get_rag_service


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Index PDF documents from DOCUMENTS_DIR into Qdrant.",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Directory containing PDF files (default: DOCUMENTS_DIR / repo rag-docs/)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recreate the Qdrant collection before indexing",
    )
    return parser


def _print_file_stats(file_stats: FileIngestStats) -> None:
    print(
        f"  {file_stats.filename}: "
        f"{file_stats.pages_indexed}/{file_stats.total_pages} pages indexed, "
        f"{file_stats.chunks_indexed} chunks, "
        f"{file_stats.duration_seconds:.1f}s "
        f"(native={file_stats.pages_native_only}, "
        f"ocr={file_stats.pages_ocr_only}, "
        f"mixed={file_stats.pages_mixed}, "
        f"skipped={file_stats.pages_skipped})"
    )


def _print_report(path: Path, report: IngestReport, *, force: bool) -> None:
    print(f"Documents directory: {path}")
    print(f"Force recreate: {force}")
    print(f"Supported extensions: {', '.join(supported_extensions())}")
    print(
        "OCR settings: "
        f"min_page_text={settings.rag_ocr_min_page_text}, "
        f"min_image_px={settings.rag_ocr_min_image_px}, "
        f"tesseract_lang={settings.rag_tesseract_lang}"
    )
    print(f"Files indexed: {report.files_processed}")
    print(f"Chunks indexed: {report.chunks_indexed}")
    print(
        "Pages: "
        f"total={report.total_pages} "
        f"indexed={report.pages_indexed} "
        f"skipped={report.pages_skipped} "
        f"native={report.pages_native_only} "
        f"ocr={report.pages_ocr_only} "
        f"mixed={report.pages_mixed}"
    )

    if report.file_stats:
        print("Per file:")
        for file_stats in report.file_stats:
            _print_file_stats(file_stats)

    if report.skipped_files:
        print(f"Skipped files (no indexable content): {', '.join(report.skipped_files)}")

    for error in report.errors:
        print(f"Error: {error}", file=sys.stderr)


async def _run(path: Path, *, force: bool) -> int:
    if not path.exists():
        print(f"Directory not found: {path}", file=sys.stderr)
        return 1

    if not path.is_dir():
        print(f"Not a directory: {path}", file=sys.stderr)
        return 1

    report = await get_rag_service().ingest_directory(path, force=force)
    _print_report(path, report, force=force)

    if report.files_processed == 0 and not report.errors and not report.skipped_files:
        print("No documents listed in manifest.")

    return 1 if report.errors else 0


def main() -> None:
    args = _build_parser().parse_args()
    path = args.path or settings.resolved_documents_dir
    exit_code = asyncio.run(_run(path, force=args.force))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
