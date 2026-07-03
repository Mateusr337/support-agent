import logging

from openai import AsyncOpenAI

from app.core.llm.base import Message

logger = logging.getLogger(__name__)


def _format_messages_for_log(messages: list[Message]) -> str:
    lines: list[str] = []
    for index, message in enumerate(messages, start=1):
        lines.append(f"  [{index}] {message.role}: {message.content}")
    return "\n".join(lines)


class OpenAILLMProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def chat(self, messages: list[Message], *, temperature: float = 0.2) -> str:
        payload = [
            {"role": message.role, "content": message.content} for message in messages
        ]
        logger.info(
            "LLM request\n"
            "  model=%s\n"
            "  temperature=%s\n"
            "  message_count=%d\n"
            "%s",
            self._model,
            temperature,
            len(messages),
            _format_messages_for_log(messages),
        )

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=payload,
            temperature=temperature,
        )
        content = response.choices[0].message.content
        if content is None:
            raise RuntimeError("OpenAI returned an empty response")

        logger.info(
            "LLM response\n  model=%s\n  content: %s",
            self._model,
            content,
        )
        return content
