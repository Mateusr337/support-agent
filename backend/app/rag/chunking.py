from dataclasses import dataclass

from app.rag.loaders.pdf import DocumentPage


@dataclass(frozen=True)
class TextChunk:
    text: str
    source: str
    page_number: int
    chunk_index: int


def chunk_text(
    text: str,
    *,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[str]:
    _validate_chunk_params(chunk_size, chunk_overlap)

    normalized = text.strip()
    if not normalized:
        return []
    if len(normalized) <= chunk_size:
        return [normalized]

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        if end < len(normalized):
            end = _find_break_point(normalized, start, end)

        piece = normalized[start:end].strip()
        if piece:
            chunks.append(piece)

        if end >= len(normalized):
            break

        next_start = end - chunk_overlap
        if next_start <= start:
            next_start = end
        start = next_start

    return chunks


def chunk_pages(
    pages: list[DocumentPage],
    *,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[TextChunk]:
    _validate_chunk_params(chunk_size, chunk_overlap)

    chunks: list[TextChunk] = []
    chunk_index = 0

    for page in pages:
        for text in chunk_text(
            page.text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        ):
            chunks.append(
                TextChunk(
                    text=text,
                    source=page.source,
                    page_number=page.page_number,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1

    return chunks


def _validate_chunk_params(chunk_size: int, chunk_overlap: int) -> None:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be >= 0 and < chunk_size")


def _find_break_point(text: str, start: int, end: int) -> int:
    segment = text[start:end]
    min_break = len(segment) // 2

    for separator in ("\n\n", "\n", " "):
        index = segment.rfind(separator)
        if index >= min_break:
            return start + index + len(separator)

    return end
