from unittest.mock import MagicMock, patch

import pytest
from qdrant_client.models import Distance, VectorParams

from app.repositories.vector_repository import ScoredPoint, VectorChunkPayload, VectorPoint, VectorRepository


@pytest.fixture()
def mock_client():
    return MagicMock()


@pytest.fixture()
def repository(mock_client):
    with patch(
        "app.repositories.vector_repository.get_qdrant_client",
        return_value=mock_client,
    ):
        yield VectorRepository(collection_name="support_documents")


def test_collection_name_is_required(repository):
    assert repository.collection_name == "support_documents"


def test_collection_name_rejects_empty_string(mock_client):
    with patch(
        "app.repositories.vector_repository.get_qdrant_client",
        return_value=mock_client,
    ):
        with pytest.raises(ValueError, match="collection_name must not be empty"):
            VectorRepository(collection_name="  ")


def test_collection_name_accepts_explicit_value(mock_client):
    with patch(
        "app.repositories.vector_repository.get_qdrant_client",
        return_value=mock_client,
    ):
        repository = VectorRepository(collection_name="custom_collection")

    assert repository.collection_name == "custom_collection"


def test_ensure_collection_creates_when_missing(repository, mock_client):
    mock_client.get_collections.return_value.collections = []

    repository.ensure_collection(1536)

    mock_client.create_collection.assert_called_once_with(
        collection_name="support_documents",
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    )


def test_ensure_collection_skips_when_exists(repository, mock_client):
    existing = MagicMock()
    existing.name = "support_documents"
    mock_client.get_collections.return_value.collections = [existing]

    repository.ensure_collection(1536)

    mock_client.create_collection.assert_not_called()


def test_recreate_collection_deletes_and_creates(repository, mock_client):
    existing = MagicMock()
    existing.name = "support_documents"
    mock_client.get_collections.return_value.collections = [existing]

    repository.recreate_collection(1536)

    mock_client.delete_collection.assert_called_once_with(collection_name="support_documents")
    mock_client.create_collection.assert_called_once_with(
        collection_name="support_documents",
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    )


def test_recreate_collection_creates_when_missing(repository, mock_client):
    mock_client.get_collections.return_value.collections = []

    repository.recreate_collection(1536)

    mock_client.delete_collection.assert_not_called()
    mock_client.create_collection.assert_called_once()


def test_upsert_builds_point_structs(repository, mock_client):
    points = [
        VectorPoint(
            id="point-1",
            vector=[0.1, 0.2],
            payload=VectorChunkPayload(
                text="Reset steps",
                source="manual.pdf",
                page_number=1,
                chunk_index=0,
                doc_id="manual.pdf",
                content_type="native",
                product_name="OMEN Laptop",
                product_type="laptop",
            ),
        )
    ]

    repository.upsert(points)

    mock_client.upsert.assert_called_once()
    call_kwargs = mock_client.upsert.call_args.kwargs
    assert call_kwargs["collection_name"] == "support_documents"
    assert len(call_kwargs["points"]) == 1
    assert call_kwargs["points"][0].id == "point-1"
    assert call_kwargs["points"][0].vector == [0.1, 0.2]
    assert call_kwargs["points"][0].payload == {
        "text": "Reset steps",
        "source": "manual.pdf",
        "page_number": 1,
        "chunk_index": 0,
        "doc_id": "manual.pdf",
        "content_type": "native",
        "product_name": "OMEN Laptop",
        "product_type": "laptop",
    }


def test_upsert_skips_when_empty(repository, mock_client):
    repository.upsert([])

    mock_client.upsert.assert_not_called()


def test_search_maps_payload_to_scored_points(repository, mock_client):
    hit = MagicMock()
    hit.score = 0.91
    hit.payload = {
        "text": "Press the power button.",
        "source": "manual.pdf",
        "page_number": 3,
        "product_name": "OMEN Laptop",
        "product_type": "laptop",
    }
    mock_client.search.return_value = [hit]

    results = repository.search([0.1, 0.2], top_k=3, score_threshold=0.5)

    mock_client.search.assert_called_once_with(
        collection_name="support_documents",
        query_vector=[0.1, 0.2],
        limit=3,
        score_threshold=0.5,
        query_filter=None,
    )
    assert results == [
        ScoredPoint(
            text="Press the power button.",
            source="manual.pdf",
            score=0.91,
            page_number=3,
            product_name="OMEN Laptop",
            product_type="laptop",
        )
    ]


def test_search_omits_product_metadata_when_missing(repository, mock_client):
    hit = MagicMock()
    hit.score = 0.75
    hit.payload = {
        "text": "Legacy chunk",
        "source": "manual.pdf",
        "page_number": 1,
    }
    mock_client.search.return_value = [hit]

    results = repository.search([0.1, 0.2])

    assert results == [
        ScoredPoint(
            text="Legacy chunk",
            source="manual.pdf",
            score=0.75,
            page_number=1,
            product_name=None,
            product_type=None,
        )
    ]


def test_search_ignores_blank_product_metadata(repository, mock_client):
    hit = MagicMock()
    hit.score = 0.75
    hit.payload = {
        "text": "Legacy chunk",
        "source": "manual.pdf",
        "page_number": 1,
        "product_name": "   ",
        "product_type": "",
    }
    mock_client.search.return_value = [hit]

    results = repository.search([0.1, 0.2])

    assert results[0].product_name is None
    assert results[0].product_type is None


def test_search_returns_empty_list_when_no_hits(repository, mock_client):
    mock_client.search.return_value = []

    results = repository.search([0.1, 0.2])

    assert results == []


def test_search_applies_product_filters(repository, mock_client):
    mock_client.search.return_value = []

    repository.search(
        [0.1, 0.2],
        product_name="HP ENVY 6000 All-in-One series",
        product_type="printer",
    )

    call_kwargs = mock_client.search.call_args.kwargs
    point_filter = call_kwargs["query_filter"]
    assert point_filter.must[0].key == "product_name"
    assert point_filter.must[0].match.value == "HP ENVY 6000 All-in-One series"
    assert point_filter.must[1].key == "product_type"
    assert point_filter.must[1].match.value == "printer"


def test_search_applies_single_product_filter(repository, mock_client):
    mock_client.search.return_value = []

    repository.search([0.1, 0.2], product_type="laptop")

    point_filter = mock_client.search.call_args.kwargs["query_filter"]
    assert len(point_filter.must) == 1
    assert point_filter.must[0].key == "product_type"
    assert point_filter.must[0].match.value == "laptop"


def test_delete_by_doc_id_uses_payload_filter(repository, mock_client):
    repository.delete_by_doc_id("manual.pdf")

    mock_client.delete.assert_called_once()
    call_kwargs = mock_client.delete.call_args.kwargs
    assert call_kwargs["collection_name"] == "support_documents"
    point_filter = call_kwargs["points_selector"]
    assert point_filter.must[0].key == "doc_id"
    assert point_filter.must[0].match.value == "manual.pdf"
