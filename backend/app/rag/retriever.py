from app.tools.base import RetrievedChunk


class NoOpRetriever:
    async def search(self, query: str, *, top_k: int = 5) -> list[RetrievedChunk]:
        return []
