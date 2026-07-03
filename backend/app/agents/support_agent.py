from dataclasses import dataclass
from typing import Protocol

from app.agents.prompts import SYSTEM_PROMPT
from app.core.llm.base import LLMProvider, Message


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    source: str | None = None


class Retriever(Protocol):
    async def search(self, query: str, *, top_k: int = 5) -> list[RetrievedChunk]: ...


class SupportAgent:
    def __init__(self, llm: LLMProvider, retriever: Retriever) -> None:
        self._llm = llm
        self._retriever = retriever

    async def reply(
        self,
        user_message: str,
        history: list[Message] | None = None,
        *,
        top_k: int = 5,
        temperature: float = 0.2,
    ) -> str:
        chunks = await self._retriever.search(user_message, top_k=top_k)
        context = self._format_context(chunks)
        messages = self._build_messages(user_message, history or [], context)
        return await self._llm.chat(messages, temperature=temperature)

    def _format_context(self, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return "No relevant documents were found."

        parts: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            header = f"[{index}]"
            if chunk.source:
                header = f"[{index}] ({chunk.source})"
            parts.append(f"{header}\n{chunk.text}")
        return "\n\n".join(parts)

    def _build_messages(
        self,
        user_message: str,
        history: list[Message],
        context: str,
    ) -> list[Message]:
        return [
            Message(role="system", content=SYSTEM_PROMPT.format(context=context)),
            *history,
            Message(role="user", content=user_message),
        ]
