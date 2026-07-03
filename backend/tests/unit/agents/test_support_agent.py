import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.agents.prompts import SYSTEM_PROMPT
from app.agents.base import AgentConfig
from app.agents.registry import AGENTS, UnknownAgentError, build_agent
from app.agents.support_agent import SupportAgent
from app.core.llm.base import Message
from app.tools.base import RetrievedChunk, ToolContext
from app.tools.registry import ToolDeps, build_tool_set
from app.tools.search_documents import SearchDocumentsTool


class FakeSearcher:
    def __init__(self, chunks: list[RetrievedChunk] | None = None) -> None:
        self._chunks = chunks or []
        self.last_query: str | None = None
        self.last_top_k: int | None = None

    async def search(self, query: str, *, top_k: int = 5) -> list[RetrievedChunk]:
        self.last_query = query
        self.last_top_k = top_k
        return self._chunks


def _build_test_agent(
    llm: MagicMock,
    searcher: FakeSearcher,
    *,
    top_k: int = 5,
) -> tuple[SupportAgent, FakeSearcher]:
    config = AGENTS["support"]
    tools = build_tool_set(config.tool_names, ToolDeps(searcher=searcher))
    return SupportAgent(llm=llm, config=config, tools=tools), searcher


def test_reply_calls_llm_with_context_and_history():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value="Reset the printer.")
    searcher = FakeSearcher(
        chunks=[RetrievedChunk(text="Press and hold the power button.", source="manual.pdf")]
    )
    agent, searcher = _build_test_agent(llm, searcher)
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
    assert searcher.last_query == "How do I reset my printer?"
    assert searcher.last_top_k == 3
    llm.chat.assert_awaited_once()
    call_kwargs = llm.chat.await_args.kwargs
    assert call_kwargs["temperature"] == 0.1
    messages = llm.chat.await_args.args[0]
    assert messages[0].role == "system"
    assert "manual.pdf" in messages[0].content
    assert messages[1:-1] == history
    assert messages[-1].content == "How do I reset my printer?"


def test_reply_uses_empty_context_when_search_returns_no_chunks():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value="I can help with that.")
    agent, _ = _build_test_agent(llm, FakeSearcher())

    asyncio.run(agent.reply("Help me"))

    messages = llm.chat.await_args.args[0]
    assert "No relevant documents were found." in messages[0].content


def test_reply_passes_audit_context_to_llm():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value="Done")
    audit_log = MagicMock()
    session_id = uuid4()
    turn_id = uuid4()
    agent, _ = _build_test_agent(llm, FakeSearcher())

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


def test_search_documents_tool_logs_rag_call():
    audit_log = MagicMock()
    tool = SearchDocumentsTool(
        FakeSearcher([RetrievedChunk(text="Reset steps", source="manual.pdf")])
    )

    asyncio.run(
        tool.run(
            {"query": "reset printer", "top_k": 2},
            context=ToolContext(
                turn_id=uuid4(),
                session_id=uuid4(),
                user_id=1,
                audit_log=audit_log,
            ),
        )
    )

    audit_log.info.assert_called_once()
    call_kwargs = audit_log.info.call_args.kwargs
    assert call_kwargs["type"] == "rag_call"
    assert call_kwargs["data"]["query"] == "reset printer"


@patch("app.agents.registry.get_rag_service")
def test_build_agent_returns_support_agent_with_config(mock_get_rag_service):
    mock_get_rag_service.return_value = MagicMock()
    llm = MagicMock()
    agent = build_agent("support", llm)

    assert isinstance(agent, SupportAgent)
    assert agent._config == AGENTS["support"]


def test_build_agent_raises_for_unknown_name():
    try:
        build_agent("unknown", MagicMock())
        raised = False
    except UnknownAgentError:
        raised = True

    assert raised


def test_support_agent_config_uses_system_prompt():
    config = AGENTS["support"]

    assert config.prompt == SYSTEM_PROMPT
    assert config.tool_names == ("search_documents",)
    assert config.tools[0].invocation == "always"
    assert config.loop_mode == "single_shot"
