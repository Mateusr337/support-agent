from app.agents.support_agent import RetrievedChunk, Retriever


class NoOpRetriever:
    async def search(self, query: str, *, top_k: int = 5) -> list[RetrievedChunk]:
        return []
