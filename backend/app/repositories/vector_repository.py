from dataclasses import dataclass

from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.qdrant import get_qdrant_client


@dataclass(frozen=True)
class VectorChunkPayload:
    text: str
    source: str
    page_number: int
    chunk_index: int
    doc_id: str
    content_type: str
    product_name: str
    product_type: str

    def to_dict(self) -> dict[str, str | int]:
        return {
            "text": self.text,
            "source": self.source,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "doc_id": self.doc_id,
            "content_type": self.content_type,
            "product_name": self.product_name,
            "product_type": self.product_type,
        }


@dataclass(frozen=True)
class VectorPoint:
    id: str
    vector: list[float]
    payload: VectorChunkPayload


@dataclass(frozen=True)
class ScoredPoint:
    text: str
    source: str | None
    score: float
    page_number: int | None = None
    product_name: str | None = None
    product_type: str | None = None


def _optional_str(payload: dict, key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _build_search_filter(
    *,
    product_name: str | None = None,
    product_type: str | None = None,
) -> Filter | None:
    conditions: list[FieldCondition] = []
    if product_name:
        conditions.append(
            FieldCondition(
                key="product_name",
                match=MatchValue(value=product_name),
            )
        )
    if product_type:
        conditions.append(
            FieldCondition(
                key="product_type",
                match=MatchValue(value=product_type),
            )
        )
    if not conditions:
        return None
    return Filter(must=conditions)


class VectorRepository:
    def __init__(self, collection_name: str) -> None:
        if not collection_name.strip():
            raise ValueError("collection_name must not be empty")

        self._client = get_qdrant_client()
        self._collection = collection_name

    @property
    def collection_name(self) -> str:
        return self._collection

    def ensure_collection(self, vector_size: int) -> None:
        existing = {collection.name for collection in self._client.get_collections().collections}
        if self._collection in existing:
            return

        self._client.create_collection(
            collection_name=self._collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    def recreate_collection(self, vector_size: int) -> None:
        existing = {collection.name for collection in self._client.get_collections().collections}
        if self._collection in existing:
            self._client.delete_collection(collection_name=self._collection)

        self._client.create_collection(
            collection_name=self._collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    def upsert(self, points: list[VectorPoint]) -> None:
        if not points:
            return

        self._client.upsert(
            collection_name=self._collection,
            points=[
                PointStruct(id=point.id, vector=point.vector, payload=point.payload.to_dict())
                for point in points
            ],
        )

    def search(
        self,
        query_vector: list[float],
        *,
        top_k: int = 5,
        score_threshold: float | None = None,
        product_name: str | None = None,
        product_type: str | None = None,
    ) -> list[ScoredPoint]:
        hits = self._client.search(
            collection_name=self._collection,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=_build_search_filter(
                product_name=product_name,
                product_type=product_type,
            ),
        )

        results: list[ScoredPoint] = []
        for hit in hits:
            payload = hit.payload or {}
            results.append(
                ScoredPoint(
                    text=str(payload.get("text", "")),
                    source=payload.get("source"),
                    score=hit.score,
                    page_number=payload.get("page_number"),
                    product_name=_optional_str(payload, "product_name"),
                    product_type=_optional_str(payload, "product_type"),
                )
            )
        return results

    def delete_by_doc_id(self, doc_id: str) -> None:
        self._client.delete(
            collection_name=self._collection,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match=MatchValue(value=doc_id),
                    )
                ]
            ),
        )
