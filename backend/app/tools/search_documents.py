from typing import Protocol

from app.tools.base import RetrievedChunk, ToolContext, ToolDefinition, ToolResult

DEFAULT_TOP_K = 10
DEFAULT_SCORE_THRESHOLD = 0.2


class DocumentSearcher(Protocol):
    async def search(
        self,
        query: str,
        *,
        top_k: int = DEFAULT_TOP_K,
        score_threshold: float | None = DEFAULT_SCORE_THRESHOLD,
    ) -> list[RetrievedChunk]: ...


class SearchDocumentsTool:
    def __init__(
        self,
        searcher: DocumentSearcher,
        *,
        default_top_k: int = DEFAULT_TOP_K,
        default_score_threshold: float | None = DEFAULT_SCORE_THRESHOLD,
    ) -> None:
        self._searcher = searcher
        self._default_top_k = default_top_k
        self._default_score_threshold = default_score_threshold

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_documents",
            description=(
                "Retrieve relevant passages from indexed HP product manuals. "
                "Use when the user asks about HP products, even in casual or vague wording "
                "(specs, setup, troubleshooting, safety, parts, or warranty). "
                "Skip for greetings or non-product chat."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Search query based on the user's question. "
                            "Include product name or model when the user mentions it; "
                            "otherwise use their everyday wording and topic. "
                            "Add technical terms only when the user already used them."
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
                },
            )

        chunks = await self._searcher.search(
            query,
            top_k=top_k,
            score_threshold=score_threshold,
        )

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
                    "result_count": len(chunks),
                    "results": [
                        {
                            "source": chunk.source,
                            "page_number": chunk.page_number,
                            "score": chunk.score,
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
            header = f"[{index}]"
            if chunk.source and chunk.page_number is not None:
                header = f"[{index}] ({chunk.source}, page {chunk.page_number})"
            elif chunk.source:
                header = f"[{index}] ({chunk.source})"
            parts.append(f"{header}\n{chunk.text}")
        return "\n\n".join(parts)
