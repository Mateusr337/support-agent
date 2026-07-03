from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Message:
    role: str
    content: str


class LLMProvider(Protocol):
    async def chat(self, messages: list[Message], *, temperature: float = 0.2) -> str: ...
