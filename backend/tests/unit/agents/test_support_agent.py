import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.agents.support_agent import RetrievedChunk, SupportAgent
from app.core.llm.base import Message


class FakeRetriever:
    def __init__(self, chunks: list[RetrievedChunk] | None = None) -> None:
        self._chunks = chunks or []
        self.last_query: str | None = None
        self.last_top_k: int | None = None

    async def search(self, query: str, *, top_k: int = 5) -> list[RetrievedChunk]:
        self.last_query = query
        self.last_top_k = top_k
        return self._chunks


def test_reply_calls_llm_with_context_and_history():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value="Reset the printer.")
    retriever = FakeRetriever(
        chunks=[RetrievedChunk(text="Press and hold the power button.", source="manual.pdf")]
    )
    agent = SupportAgent(llm=llm, retriever=retriever)
    history = [Message(role="user", content="Hi"), Message(role="assistant", content="Hello")]

    result = asyncio.run(
        agent.reply(
            "How do I reset my printer?",
            history=history,
            top_k=3,
            temperature=0.1,
        )
    )

    assert result == "Reset the printer."
    assert retriever.last_query == "How do I reset my printer?"
    assert retriever.last_top_k == 3
    llm.chat.assert_awaited_once()
    call_kwargs = llm.chat.await_args.kwargs
    assert call_kwargs["temperature"] == 0.1
    messages = llm.chat.await_args.args[0]
    assert messages[0].role == "system"
    assert "manual.pdf" in messages[0].content
    assert messages[1:-1] == history
    assert messages[-1].content == "How do I reset my printer?"


def test_reply_uses_empty_context_when_retriever_returns_no_chunks():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value="I can help with that.")
    agent = SupportAgent(llm=llm, retriever=FakeRetriever())

    asyncio.run(agent.reply("Help me"))

    messages = llm.chat.await_args.args[0]
    assert "No relevant documents were found." in messages[0].content


def test_reply_passes_audit_context_to_llm():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value="Done")
    audit_log = MagicMock()
    session_id = uuid4()
    turn_id = uuid4()
    agent = SupportAgent(llm=llm, retriever=FakeRetriever())

    asyncio.run(
        agent.reply(
            "Question",
            turn_id=turn_id,
            session_id=session_id,
            user_id=7,
            audit_log=audit_log,
        )
    )

    llm.chat.assert_awaited_once_with(
        llm.chat.await_args.args[0],
        temperature=0.2,
        audit_log=audit_log,
        session_id=session_id,
        user_id=7,
        turn_id=turn_id,
    )
