from app.core.config import settings
from app.rag.embeddings.base import EmbeddingProvider
from app.rag.embeddings.openai import OpenAIEmbeddingProvider


def get_embedding_provider() -> EmbeddingProvider:
    if settings.embedding_provider == "openai":
        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required when EMBEDDING_PROVIDER is openai"
            )

        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.embedding_model,
        )

    raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")
