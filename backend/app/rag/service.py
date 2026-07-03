from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.core.config import settings
from app.rag.chunking import TextChunk, chunk_pages
from app.rag.embeddings.base import EmbeddingProvider
from app.rag.embeddings.factory import get_embedding_provider
from app.rag.loaders.pdf import load_pdf
from app.repositories.vector_repository import VectorPoint, VectorRepository
from app.tools.base import RetrievedChunk


@dataclass(frozen=True)
class IngestReport:
    files_processed: int = 0
    chunks_indexed: int = 0
    skipped_files: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


class RagService:
    def __init__(
        self,
        vector_repository: VectorRepository,
        embedding_provider: EmbeddingProvider,
        *,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        embed_batch_size: int = 32,
        search_score_threshold: float | None = 0.5,
    ) -> None:
        self._vector_repository = vector_repository
        self._embedding_provider = embedding_provider
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._embed_batch_size = embed_batch_size
        self._search_score_threshold = search_score_threshold

    async def ingest_directory(self, path: Path, *, force: bool = False) -> IngestReport:
        if not path.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")

        vector_size = self._embedding_provider.dimension
        if force:
            self._vector_repository.recreate_collection(vector_size)
        else:
            self._vector_repository.ensure_collection(vector_size)

        pdf_files = sorted(path.glob("*.pdf"))
        if not pdf_files:
            return IngestReport()

        files_processed = 0
        chunks_indexed = 0
        skipped_files: list[str] = []
        errors: list[str] = []

        for pdf_path in pdf_files:
            try:
                indexed = await self._index_pdf(pdf_path)
            except Exception as exc:
                errors.append(f"{pdf_path.name}: {exc}")
                continue

            if indexed == 0:
                skipped_files.append(pdf_path.name)
                continue

            files_processed += 1
            chunks_indexed += indexed

        return IngestReport(
            files_processed=files_processed,
            chunks_indexed=chunks_indexed,
            skipped_files=tuple(skipped_files),
            errors=tuple(errors),
        )

    async def ingest_file(self, path: Path) -> int:
        self._vector_repository.ensure_collection(self._embedding_provider.dimension)
        return await self._index_pdf(Path(path))

    async def search(self, query: str, *, top_k: int = 5) -> list[RetrievedChunk]:
        vectors = await self._embedding_provider.embed([query])
        if not vectors:
            return []

        hits = self._vector_repository.search(
            vectors[0],
            top_k=top_k,
            score_threshold=self._search_score_threshold,
        )
        return [
            RetrievedChunk(text=hit.text, source=hit.source)
            for hit in hits
            if hit.text
        ]

    async def _index_pdf(self, pdf_path: Path) -> int:
        pages = load_pdf(pdf_path)
        chunks = chunk_pages(
            pages,
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
        )
        if not chunks:
            return 0

        doc_id = pdf_path.name
        self._vector_repository.delete_by_doc_id(doc_id)

        indexed = 0
        for start in range(0, len(chunks), self._embed_batch_size):
            batch = chunks[start : start + self._embed_batch_size]
            vectors = await self._embedding_provider.embed([chunk.text for chunk in batch])
            points = [
                self._to_vector_point(doc_id=doc_id, chunk=chunk, vector=vector)
                for chunk, vector in zip(batch, vectors, strict=True)
            ]
            self._vector_repository.upsert(points)
            indexed += len(points)

        return indexed

    def _to_vector_point(
        self,
        *,
        doc_id: str,
        chunk: TextChunk,
        vector: list[float],
    ) -> VectorPoint:
        point_id = str(uuid5(NAMESPACE_URL, f"{doc_id}:{chunk.chunk_index}"))
        return VectorPoint(
            id=point_id,
            vector=vector,
            payload={
                "text": chunk.text,
                "source": chunk.source,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "doc_id": doc_id,
            },
        )


@lru_cache
def get_rag_service() -> RagService:
    return RagService(
        vector_repository=VectorRepository(collection_name=settings.qdrant_collection),
        embedding_provider=get_embedding_provider(),
    )
