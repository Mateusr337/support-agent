from typing import Protocol

from app.tools.base import RetrievedChunk, ToolContext, ToolDefinition, ToolResult


class DocumentSearcher(Protocol):
    async def search(self, query: str, *, top_k: int = 5) -> list[RetrievedChunk]: ...


class SearchDocumentsTool:
    def __init__(self, searcher: DocumentSearcher) -> None:
        self._searcher = searcher

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="search_documents",
            description="Search HP product manuals for relevant passages.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer"},
                },
                "required": ["query"],
            },
        )

    async def run(self, arguments: dict, *, context: ToolContext) -> ToolResult:
        query = arguments["query"]
        top_k = arguments.get("top_k", 5)
        chunks = await self._searcher.search(query, top_k=top_k)

        if context.audit_log is not None:
            context.audit_log.info(
                session_id=context.session_id,
                user_id=context.user_id,
                turn_id=context.turn_id,
                type="rag_call",
                message="Document search completed",
                data={
                    "query": query,
                    "top_k": top_k,
                    "result_count": len(chunks),
                    "sources": [chunk.source for chunk in chunks if chunk.source],
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
            if chunk.source:
                header = f"[{index}] ({chunk.source})"
            parts.append(f"{header}\n{chunk.text}")
        return "\n\n".join(parts)
