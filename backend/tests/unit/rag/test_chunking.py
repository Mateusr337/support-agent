import pytest

from app.rag.chunking import TextChunk, chunk_pages, chunk_text
from app.rag.loaders.pdf import DocumentPage


def test_chunk_text_returns_single_chunk_for_short_text():
    text = "Reset the printer by holding the power button."

    assert chunk_text(text) == [text]


def test_chunk_text_returns_empty_list_for_blank_text():
    assert chunk_text("   ") == []


def test_chunk_text_splits_long_text_with_overlap():
    text = "word " * 300

    chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)

    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)
    assert chunks[0][-20:] in chunks[1]


def test_chunk_text_prefers_breaking_at_paragraph_boundary():
    first = "A" * 80
    second = "B" * 80
    text = f"{first}\n\n{second}"

    chunks = chunk_text(text, chunk_size=100, chunk_overlap=0)

    assert chunks == [first, second]


def test_chunk_text_raises_for_invalid_chunk_size():
    with pytest.raises(ValueError, match="chunk_size must be positive"):
        chunk_text("hello", chunk_size=0)


def test_chunk_text_raises_for_invalid_chunk_overlap():
    with pytest.raises(ValueError, match="chunk_overlap"):
        chunk_text("hello", chunk_size=100, chunk_overlap=100)


def test_chunk_pages_assigns_metadata_and_indexes():
    pages = [
        DocumentPage(text="Alpha paragraph.", page_number=1, source="manual.pdf"),
        DocumentPage(text="Beta paragraph.", page_number=2, source="manual.pdf"),
    ]

    chunks = chunk_pages(pages, chunk_size=1000, chunk_overlap=0)

    assert chunks == [
        TextChunk(
            text="Alpha paragraph.",
            source="manual.pdf",
            page_number=1,
            chunk_index=0,
        ),
        TextChunk(
            text="Beta paragraph.",
            source="manual.pdf",
            page_number=2,
            chunk_index=1,
        ),
    ]


def test_chunk_pages_splits_large_pages():
    page = DocumentPage(
        text="segment " * 200,
        page_number=1,
        source="manual.pdf",
    )

    chunks = chunk_pages([page], chunk_size=100, chunk_overlap=20)

    assert len(chunks) > 1
    assert all(chunk.source == "manual.pdf" for chunk in chunks)
    assert all(chunk.page_number == 1 for chunk in chunks)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
