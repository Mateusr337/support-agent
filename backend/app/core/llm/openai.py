from openai import AsyncOpenAI

from app.core.llm.base import Message


class OpenAILLMProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def chat(self, messages: list[Message], *, temperature: float = 0.2) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": message.role, "content": message.content} for message in messages],
            temperature=temperature,
        )
        content = response.choices[0].message.content
        if content is None:
            raise RuntimeError("OpenAI returned an empty response")
        return content
