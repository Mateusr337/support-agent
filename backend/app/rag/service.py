import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.core.config import settings
from app.rag.chunking import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    TextChunk,
    chunk_pages,
)
from app.rag.embeddings.base import EmbeddingProvider
from app.rag.embeddings.factory import get_embedding_provider
from app.rag.loaders.base import DocumentLoader
from app.rag.loaders.factory import get_document_loader_for_path
from app.rag.manifest import DocumentManifestEntry, find_manifest_entry, load_manifest
from app.repositories.vector_repository import VectorChunkPayload, VectorPoint, VectorRepository
from app.tools.base import RetrievedChunk


@dataclass(frozen=True)
class FileIngestStats:
    filename: str
    total_pages: int
    pages_indexed: int
    pages_skipped: int
    pages_native_only: int
    pages_ocr_only: int
    pages_mixed: int
    chunks_indexed: int
    duration_seconds: float


@dataclass(frozen=True)
class IngestReport:
    files_processed: int = 0
    chunks_indexed: int = 0
    total_pages: int = 0
    pages_indexed: int = 0
    pages_skipped: int = 0
    pages_native_only: int = 0
    pages_ocr_only: int = 0
    pages_mixed: int = 0
    skipped_files: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    file_stats: tuple[FileIngestStats, ...] = ()


class RagService:
    def __init__(
        self,
        vector_repository: VectorRepository,
        embedding_provider: EmbeddingProvider,
        *,
        loader_for_path: Callable[[Path], DocumentLoader] | None = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        embed_batch_size: int = 32,
    ) -> None:
        self._vector_repository = vector_repository
        self._embedding_provider = embedding_provider
        self._loader_for_path = loader_for_path or get_document_loader_for_path
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._embed_batch_size = embed_batch_size

    async def ingest_directory(self, path: Path, *, force: bool = False) -> IngestReport:
        if not path.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")

        vector_size = self._embedding_provider.dimension
        if force:
            self._vector_repository.recreate_collection(vector_size)
        else:
            self._vector_repository.ensure_collection(vector_size)

        try:
            entries = load_manifest(path)
        except (FileNotFoundError, ValueError) as exc:
            return IngestReport(errors=(str(exc),))

        if not entries:
            return IngestReport()

        files_processed = 0
        chunks_indexed = 0
        total_pages = 0
        pages_indexed = 0
        pages_skipped = 0
        pages_native_only = 0
        pages_ocr_only = 0
        pages_mixed = 0
        skipped_files: list[str] = []
        errors: list[str] = []
        file_stats: list[FileIngestStats] = []

        for entry in entries:
            file_path = path / entry.filename
            if not file_path.is_file():
                errors.append(f"{entry.filename}: file not found")
                continue

            try:
                file_report = await self._index_document(file_path, entry)
            except Exception as exc:
                errors.append(f"{entry.filename}: {exc}")
                continue

            if file_report.chunks_indexed == 0:
                skipped_files.append(entry.filename)
                file_stats.append(file_report)
                total_pages += file_report.total_pages
                pages_skipped += file_report.pages_skipped
                continue

            files_processed += 1
            chunks_indexed += file_report.chunks_indexed
            total_pages += file_report.total_pages
            pages_indexed += file_report.pages_indexed
            pages_skipped += file_report.pages_skipped
            pages_native_only += file_report.pages_native_only
            pages_ocr_only += file_report.pages_ocr_only
            pages_mixed += file_report.pages_mixed
            file_stats.append(file_report)

        return IngestReport(
            files_processed=files_processed,
            chunks_indexed=chunks_indexed,
            total_pages=total_pages,
            pages_indexed=pages_indexed,
            pages_skipped=pages_skipped,
            pages_native_only=pages_native_only,
            pages_ocr_only=pages_ocr_only,
            pages_mixed=pages_mixed,
            skipped_files=tuple(skipped_files),
            errors=tuple(errors),
            file_stats=tuple(file_stats),
        )

    async def ingest_file(self, path: Path) -> int:
        path = Path(path)
        self._vector_repository.ensure_collection(self._embedding_provider.dimension)
        entry = self._resolve_manifest_entry(path)
        report = await self._index_document(path, entry)
        return report.chunks_indexed

    async def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        score_threshold: float | None = None,
        product_name: str | None = None,
        product_type: str | None = None,
    ) -> list[RetrievedChunk]:
        vectors = await self._embedding_provider.embed([query])
        if not vectors:
            return []

        hits = self._vector_repository.search(
            vectors[0],
            top_k=top_k,
            score_threshold=score_threshold,
            product_name=product_name,
            product_type=product_type,
        )
        chunks = [
            RetrievedChunk(
                text=hit.text,
                source=hit.source,
                page_number=hit.page_number,
                score=hit.score,
                product_name=hit.product_name,
                product_type=hit.product_type,
            )
            for hit in hits
            if hit.text
        ]

        return chunks

    def _resolve_manifest_entry(self, path: Path) -> DocumentManifestEntry:
        try:
            entries = load_manifest(path.parent)
            entry = find_manifest_entry(entries, path.name)
            if entry is not None:
                return entry
        except (FileNotFoundError, ValueError):
            pass
        return DocumentManifestEntry.from_path(path)

    async def _index_document(
        self,
        file_path: Path,
        entry: DocumentManifestEntry,
    ) -> FileIngestStats:
        started = time.perf_counter()
        loader = self._loader_for_path(file_path)
        load_result = loader.load(file_path)

        chunks = chunk_pages(
            list(load_result.pages),
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
        )
        duration_seconds = time.perf_counter() - started

        if not chunks:
            return FileIngestStats(
                filename=entry.filename,
                total_pages=load_result.total_pages,
                pages_indexed=load_result.pages_indexed,
                pages_skipped=load_result.pages_skipped,
                pages_native_only=load_result.pages_native_only,
                pages_ocr_only=load_result.pages_ocr_only,
                pages_mixed=load_result.pages_mixed,
                chunks_indexed=0,
                duration_seconds=duration_seconds,
            )

        doc_id = entry.filename
        self._vector_repository.delete_by_doc_id(doc_id)

        indexed = 0
        for start in range(0, len(chunks), self._embed_batch_size):
            batch = chunks[start : start + self._embed_batch_size]
            vectors = await self._embedding_provider.embed([chunk.text for chunk in batch])
            points = [
                self._to_vector_point(doc_id=doc_id, entry=entry, chunk=chunk, vector=vector)
                for chunk, vector in zip(batch, vectors, strict=True)
            ]
            self._vector_repository.upsert(points)
            indexed += len(points)

        duration_seconds = time.perf_counter() - started
        return FileIngestStats(
            filename=entry.filename,
            total_pages=load_result.total_pages,
            pages_indexed=load_result.pages_indexed,
            pages_skipped=load_result.pages_skipped,
            pages_native_only=load_result.pages_native_only,
            pages_ocr_only=load_result.pages_ocr_only,
            pages_mixed=load_result.pages_mixed,
            chunks_indexed=indexed,
            duration_seconds=duration_seconds,
        )

    @staticmethod
    def _enrich_chunk_text(
        *,
        product_name: str,
        product_type: str,
        text: str,
    ) -> str:
        return f"Source: {product_name} (product type: {product_type})\n\n{text}"

    def _to_vector_point(
        self,
        *,
        doc_id: str,
        entry: DocumentManifestEntry,
        chunk: TextChunk,
        vector: list[float],
    ) -> VectorPoint:
        point_id = str(uuid5(NAMESPACE_URL, f"{doc_id}:{chunk.chunk_index}"))
        enriched_text = self._enrich_chunk_text(
            product_name=entry.product_name,
            product_type=entry.product_type,
            text=chunk.text,
        )
        return VectorPoint(
            id=point_id,
            vector=vector,
            payload=VectorChunkPayload(
                text=enriched_text,
                source=chunk.source,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                doc_id=doc_id,
                content_type=chunk.content_type,
                product_name=entry.product_name,
                product_type=entry.product_type,
            ),
        )


@lru_cache
def get_rag_service() -> RagService:
    return RagService(
        vector_repository=VectorRepository(collection_name=settings.qdrant_collection),
        embedding_provider=get_embedding_provider(),
    )
