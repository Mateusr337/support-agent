from openai import AsyncOpenAI

_MODEL_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class OpenAIEmbeddingProvider:
    def __init__(self, api_key: str, model: str) -> None:
        if model not in _MODEL_DIMENSIONS:
            supported = ", ".join(sorted(_MODEL_DIMENSIONS))
            raise ValueError(
                f"Unsupported embedding model: {model}. Supported models: {supported}"
            )

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return _MODEL_DIMENSIONS[self._model]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
        )

        return [item.embedding for item in response.data]
