import time
from typing import Protocol

from app.rag.manifest import (
    DocumentManifestEntry,
    format_indexed_products,
    resolve_product_filters,
)
from app.tools.base import RetrievedChunk, ToolContext, ToolDefinition, ToolResult

DEFAULT_TOP_K = 7


def _optional_filter(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class DocumentSearcher(Protocol):
    async def search(
        self,
        query: str,
        *,
        top_k: int = DEFAULT_TOP_K,
        score_threshold: float | None = None,
        product_name: str | None = None,
        product_type: str | None = None,
    ) -> list[RetrievedChunk]: ...


class SearchDocumentsTool:
    def __init__(
        self,
        searcher: DocumentSearcher,
        *,
        manifest_entries: tuple[DocumentManifestEntry, ...] = (),
        default_top_k: int = DEFAULT_TOP_K,
        default_score_threshold: float | None = None,
    ) -> None:
        self._searcher = searcher
        self._manifest_entries = manifest_entries
        self._default_top_k = default_top_k
        self._default_score_threshold = default_score_threshold

    @property
    def definition(self) -> ToolDefinition:
        indexed_products = format_indexed_products(self._manifest_entries)

        return ToolDefinition(
            name="search_documents",
            description=(
                "Retrieve relevant passages from indexed HP product manuals. "
                "Use for HP product questions about specs, setup, troubleshooting, safety, "
                "parts, or warranty — even when the user asks casually or vaguely. "
                "Skip for greetings or non-product chat. "
                "The query must be a rich semantic search string, not a keyword. "
                "Combine: (1) the user's full question, (2) product/model name, "
                "(3) topic synonyms and spec terms, (4) manual section terms such as "
                "product description, specifications, spare parts, setup, safety, "
                "Customer Self-Repair, or troubleshooting. "
                "If the first search returns nothing useful, call again with broader "
                "synonyms and section terms before giving up. "
                "Use product and product_type filters when the product is known; omit "
                "when unknown or searching across products."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Rich semantic search query sent to the embedding model. "
                            "Must restate the user's question, name the product/model, "
                            "and include synonyms plus manual vocabulary (product description, "
                            "specifications, spare parts, setup, safety, Customer Self-Repair). "
                            "Good: 'OMEN 17.3 gaming laptop battery type capacity Whr cell "
                            "count polymer spare part product description'. "
                            "Bad: 'battery', 'RAM', 'TPM'."
                        ),
                    },
                    "product": {
                        "type": "string",
                        "description": (
                            "Optional product filter. Use an exact indexed product name "
                            "when possible; a close user-facing name is also accepted. "
                            "Omit when unknown or searching across products."
                            + (f" {indexed_products}" if indexed_products else "")
                        ),
                    },
                    "product_type": {
                        "type": "string",
                        "description": (
                            "Optional category filter: 'laptop' or 'printer'. "
                            "Omit when unknown or searching across product types."
                        ),
                    },
                },
                "required": ["query"],
            },
        )

    async def run(self, arguments: dict, *, context: ToolContext) -> ToolResult:
        query = arguments["query"]
        top_k = arguments.get("top_k", self._default_top_k)
        score_threshold = arguments.get("score_threshold", self._default_score_threshold)
        raw_product = _optional_filter(arguments.get("product"))
        raw_product_type = _optional_filter(arguments.get("product_type"))
        product_name, product_type = resolve_product_filters(
            product=raw_product,
            product_type=raw_product_type,
            entries=self._manifest_entries,
        )

        if context.audit_log is not None:
            context.audit_log.info(
                session_id=context.session_id,
                user_id=context.user_id,
                turn_id=context.turn_id,
                type="Tool Call",
                message="Document search invoked",
                data={
                    "query": query,
                    "top_k": top_k,
                    "score_threshold": score_threshold,
                    "product": product_name,
                    "product_type": product_type,
                    "raw_product": raw_product,
                },
            )

        start = time.perf_counter()
        chunks = await self._searcher.search(
            query,
            top_k=top_k,
            score_threshold=score_threshold,
            product_name=product_name,
            product_type=product_type,
        )
        if not chunks and product_name is not None:
            chunks = await self._searcher.search(
                query,
                top_k=top_k,
                score_threshold=score_threshold,
                product_name=None,
                product_type=product_type,
            )
        latency_ms = round((time.perf_counter() - start) * 1000)

        if context.audit_log is not None:
            context.audit_log.info(
                session_id=context.session_id,
                user_id=context.user_id,
                turn_id=context.turn_id,
                type="Tool Result",
                message="Document search completed",
                data={
                    "query": query,
                    "top_k": top_k,
                    "score_threshold": score_threshold,
                    "product": product_name,
                    "product_type": product_type,
                    "result_count": len(chunks),
                    "latency_ms": latency_ms,
                    "results": [
                        {
                            "source": chunk.source,
                            "page_number": chunk.page_number,
                            "score": chunk.score,
                            "product_name": chunk.product_name,
                            "product_type": chunk.product_type,
                            "text": chunk.text,
                        }
                        for chunk in chunks
                    ],
                },
            )

        return ToolResult(
            content=self._format_chunks(chunks),
            data={"chunk_count": len(chunks)},
        )

    def _format_chunks(self, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return "No relevant documents were found."

        parts: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            parts.append(f"{self._format_chunk_header(index, chunk)}\n{chunk.text}")
        return "\n\n".join(parts)

    def _format_chunk_header(self, index: int, chunk: RetrievedChunk) -> str:
        if chunk.page_number is not None:
            return f"[{index}] p. {chunk.page_number}"
        return f"[{index}]"
