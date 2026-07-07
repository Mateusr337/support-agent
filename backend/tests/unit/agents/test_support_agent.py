import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.agents.registry import AGENTS, UnknownAgentError, build_agent
from app.agents.support import SupportAgent
from app.agents.support.prompts import SYSTEM_PROMPT
from app.core.llm.base import ChatStreamEvent, Message, ToolCallRequest
from app.rag.manifest import DocumentManifestEntry
from app.tools.base import RetrievedChunk, ToolContext
from app.tools.registry import ToolDeps, build_tool_set
from app.tools.search_documents import DEFAULT_TOP_K, SearchDocumentsTool


class FakeSearcher:
    def __init__(self, chunks: list[RetrievedChunk] | None = None) -> None:
        self._chunks = chunks or []
        self.last_query: str | None = None
        self.last_top_k: int | None = None
        self.last_score_threshold: float | None = None
        self.last_product_name: str | None = None
        self.last_product_type: str | None = None

    async def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        score_threshold: float | None = None,
        product_name: str | None = None,
        product_type: str | None = None,
        **kwargs,
    ) -> list[RetrievedChunk]:
        self.last_query = query
        self.last_top_k = top_k
        self.last_score_threshold = score_threshold
        self.last_product_name = product_name
        self.last_product_type = product_type
        return self._chunks


def _build_test_agent(
    llm: MagicMock,
    searcher: FakeSearcher,
) -> tuple[SupportAgent, FakeSearcher]:
    config = AGENTS["support"]
    tools = build_tool_set(config.tool_names, ToolDeps(searcher=searcher))
    return SupportAgent(llm=llm, config=config, tools=tools), searcher


def test_reply_runs_tool_loop_and_returns_final_answer():
    captured_messages: list[list[Message]] = []
    stream_calls = 0

    async def fake_chat_stream(messages, **kwargs):
        nonlocal stream_calls
        stream_calls += 1
        captured_messages.append(list(messages))
        if kwargs.get("tools"):
            yield ChatStreamEvent(
                tool_calls=(
                    ToolCallRequest(
                        id="call_1",
                        name="search_documents",
                        arguments={"query": "How do I reset my printer?"},
                    ),
                ),
            )
            return
        yield ChatStreamEvent(content="Reset the printer.")

    llm = MagicMock()
    llm.chat_stream = fake_chat_stream
    searcher = FakeSearcher(
        chunks=[
            RetrievedChunk(
                text="Press and hold the power button.",
                source="manual.pdf",
                page_number=4,
            )
        ]
    )
    agent, searcher = _build_test_agent(llm, searcher)
    history = [Message(role="user", content="Hi"), Message(role="assistant", content="Hello")]

    result = asyncio.run(
        agent.reply(
            "How do I reset my printer?",
            history=history,
            temperature=0.1,
        )
    )

    assert result == "Reset the printer."
    assert searcher.last_query == "How do I reset my printer?"
    assert searcher.last_top_k == DEFAULT_TOP_K
    assert stream_calls == 3

    first_messages = captured_messages[0]
    assert first_messages[0].role == "system"
    assert first_messages[0].content == SYSTEM_PROMPT
    assert first_messages[1:3] == history
    assert first_messages[-1].content == "How do I reset my printer?"


def test_reply_stream_emits_tool_call_and_tokens():
    stream_calls = 0

    async def fake_chat_stream(messages, **kwargs):
        nonlocal stream_calls
        stream_calls += 1
        if kwargs.get("tools"):
            yield ChatStreamEvent(
                tool_calls=(
                    ToolCallRequest(
                        id="call_1",
                        name="search_documents",
                        arguments={"query": "battery specs"},
                    ),
                ),
            )
            return
        yield ChatStreamEvent(content="The ")
        yield ChatStreamEvent(content="battery.")

    llm = MagicMock()
    llm.chat_stream = fake_chat_stream
    agent, _ = _build_test_agent(llm, FakeSearcher())

    async def collect_events():
        events = []
        async for event in agent.reply_stream("What battery?"):
            events.append(event)
        return events

    events = asyncio.run(collect_events())

    assert events == [
        {"type": "tool_call", "name": "search_documents"},
        {"type": "tool_call", "name": "search_documents"},
        {"type": "token", "content": "The "},
        {"type": "token", "content": "battery."},
    ]
    assert stream_calls == 3


def test_reply_stream_emits_tokens_for_direct_answer():
    stream_calls = 0

    async def fake_chat_stream(messages, **kwargs):
        nonlocal stream_calls
        stream_calls += 1
        yield ChatStreamEvent(content="Hello! How can I help?")

    llm = MagicMock()
    llm.chat_stream = fake_chat_stream
    agent, searcher = _build_test_agent(llm, FakeSearcher())

    async def collect_events():
        events = []
        async for event in agent.reply_stream("Hi"):
            events.append(event)
        return events

    events = asyncio.run(collect_events())

    assert events == [{"type": "token", "content": "Hello! How can I help?"}]
    assert searcher.last_query is None
    assert stream_calls == 1


def test_reply_returns_direct_answer_when_llm_skips_tools():
    async def fake_chat_stream(messages, **kwargs):
        yield ChatStreamEvent(content="Hello! How can I help?")

    llm = MagicMock()
    llm.chat_stream = fake_chat_stream
    agent, searcher = _build_test_agent(llm, FakeSearcher())

    result = asyncio.run(agent.reply("Hi"))

    assert result == "Hello! How can I help?"
    assert searcher.last_query is None


def test_reply_stream_runs_multiple_tool_rounds_before_final_stream():
    stream_calls = 0

    async def fake_chat_stream(messages, **kwargs):
        nonlocal stream_calls
        stream_calls += 1
        if kwargs.get("tools"):
            query = "first query" if stream_calls == 1 else "refined query"
            yield ChatStreamEvent(
                tool_calls=(
                    ToolCallRequest(
                        id=f"call_{stream_calls}",
                        name="search_documents",
                        arguments={"query": query},
                    ),
                ),
            )
            return
        yield ChatStreamEvent(content="Final answer.")

    llm = MagicMock()
    llm.chat_stream = fake_chat_stream
    searcher = FakeSearcher()
    agent, searcher = _build_test_agent(llm, searcher)

    async def collect_events():
        events = []
        async for event in agent.reply_stream("Question"):
            events.append(event)
        return events

    events = asyncio.run(collect_events())

    assert events == [
        {"type": "tool_call", "name": "search_documents"},
        {"type": "tool_call", "name": "search_documents"},
        {"type": "token", "content": "Final answer."},
    ]
    assert stream_calls == 3
    assert searcher.last_query == "refined query"


def test_reply_stream_uses_final_iteration_without_tools():
    tools_passed: list[bool] = []

    async def fake_chat_stream(messages, **kwargs):
        tools_passed.append(kwargs.get("tools") is not None)
        if kwargs.get("tools"):
            yield ChatStreamEvent(
                tool_calls=(
                    ToolCallRequest(
                        id="call_1",
                        name="search_documents",
                        arguments={"query": "test"},
                    ),
                ),
            )
            return
        yield ChatStreamEvent(content="Done.")

    llm = MagicMock()
    llm.chat_stream = fake_chat_stream
    agent, _ = _build_test_agent(llm, FakeSearcher())

    asyncio.run(agent.reply("Question"))

    assert tools_passed == [True, True, False]


def test_reply_passes_audit_context_to_llm():
    audit_log = MagicMock()
    session_id = uuid4()
    turn_id = uuid4()
    captured_kwargs: dict = {}

    async def fake_chat_stream(messages, **kwargs):
        captured_kwargs.update(kwargs)
        yield ChatStreamEvent(content="Done")

    llm = MagicMock()
    llm.chat_stream = fake_chat_stream
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

    assert captured_kwargs["audit_log"] is audit_log
    assert captured_kwargs["session_id"] == session_id
    assert captured_kwargs["user_id"] == 7
    assert captured_kwargs["turn_id"] == turn_id
    assert captured_kwargs["temperature"] == 0.2


def test_search_documents_tool_uses_default_top_k():
    searcher = FakeSearcher()
    tool = SearchDocumentsTool(searcher)

    asyncio.run(tool.run({"query": "reset printer"}, context=ToolContext()))

    assert searcher.last_top_k == DEFAULT_TOP_K
    assert searcher.last_score_threshold is None


def test_search_documents_tool_uses_custom_score_threshold():
    searcher = FakeSearcher()
    tool = SearchDocumentsTool(searcher, default_score_threshold=0.35)

    asyncio.run(tool.run({"query": "reset printer"}, context=ToolContext()))

    assert searcher.last_score_threshold == 0.35


def test_search_documents_tool_passes_product_filters():
    entries = (
        DocumentManifestEntry(
            filename="HP ENVY 6000 All-in-One series.pdf",
            product_name="HP ENVY 6000 All-in-One series",
            product_type="printer",
        ),
    )
    searcher = FakeSearcher(
        chunks=[
            RetrievedChunk(
                text="Hold the Wi-Fi button for 3 seconds.",
                source="HP ENVY 6000 All-in-One series.pdf",
                page_number=12,
                score=0.9,
            )
        ]
    )
    tool = SearchDocumentsTool(searcher, manifest_entries=entries)

    asyncio.run(
        tool.run(
            {
                "query": "reset Wi-Fi",
                "product": "HP ENVY 6000 All-in-One series",
                "product_type": "printer",
            },
            context=ToolContext(),
        )
    )

    assert searcher.last_product_name == "HP ENVY 6000 All-in-One series"
    assert searcher.last_product_type == "printer"


def test_search_documents_tool_resolves_colloquial_product_name():
    entries = (
        DocumentManifestEntry(
            filename="OMEN 17.3 inch Gaming Laptop PC.pdf",
            product_name="OMEN 17.3 inch Gaming Laptop PC",
            product_type="laptop",
        ),
    )
    searcher = FakeSearcher(
        chunks=[
            RetrievedChunk(
                text="6 cell, 83 Whr polymer battery.",
                source="OMEN 17.3 inch Gaming Laptop PC.pdf",
                page_number=5,
                score=0.92,
            )
        ]
    )
    tool = SearchDocumentsTool(searcher, manifest_entries=entries)

    asyncio.run(
        tool.run(
            {
                "query": "battery",
                "product": "HP OMEN 17.3",
                "product_type": "laptop",
            },
            context=ToolContext(),
        )
    )

    assert searcher.last_product_name == "OMEN 17.3 inch Gaming Laptop PC"
    assert searcher.last_query == "battery"


def test_search_documents_tool_retries_without_product_filter_when_empty():
    class EmptyThenResultsSearcher(FakeSearcher):
        def __init__(self) -> None:
            super().__init__()
            self.calls: list[tuple[str | None, str | None]] = []

        async def search(self, query, *, top_k=DEFAULT_TOP_K, score_threshold=None, product_name=None, product_type=None):
            self.calls.append((product_name, product_type))
            if product_name is not None:
                return []
            return [
                RetrievedChunk(
                    text="Battery details",
                    source="manual.pdf",
                    page_number=3,
                    score=0.88,
                )
            ]

    searcher = EmptyThenResultsSearcher()
    entries = (
        DocumentManifestEntry(
            filename="OMEN 17.3 inch Gaming Laptop PC.pdf",
            product_name="OMEN 17.3 inch Gaming Laptop PC",
            product_type="laptop",
        ),
    )
    tool = SearchDocumentsTool(searcher, manifest_entries=entries)

    result = asyncio.run(
        tool.run(
            {
                "query": "battery type",
                "product": "OMEN 17.3 inch Gaming Laptop PC",
                "product_type": "laptop",
            },
            context=ToolContext(),
        )
    )

    assert searcher.calls == [
        ("OMEN 17.3 inch Gaming Laptop PC", "laptop"),
        (None, "laptop"),
    ]
    assert "Battery details" in result.content


def test_search_documents_tool_ignores_blank_product_filters():
    searcher = FakeSearcher()
    tool = SearchDocumentsTool(searcher)

    asyncio.run(
        tool.run(
            {
                "query": "reset Wi-Fi",
                "product": "  ",
                "product_type": "",
            },
            context=ToolContext(),
        )
    )

    assert searcher.last_product_name is None
    assert searcher.last_product_type is None


def test_search_documents_tool_formats_page_number_in_header():
    tool = SearchDocumentsTool(
        FakeSearcher(
            [
                RetrievedChunk(
                    text="Reset steps",
                    source="manual.pdf",
                    page_number=2,
                    score=0.91,
                    product_name="OMEN Laptop",
                    product_type="laptop",
                )
            ]
        )
    )

    result = asyncio.run(tool.run({"query": "reset printer"}, context=ToolContext()))

    assert "[1] p. 2" in result.content


def test_search_documents_tool_logs_tool_call_and_result():
    audit_log = MagicMock()
    tool = SearchDocumentsTool(
        FakeSearcher(
            [
                RetrievedChunk(
                    text="Reset steps",
                    source="manual.pdf",
                    page_number=2,
                    score=0.91,
                )
            ]
        )
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

    assert audit_log.info.call_count == 2
    tool_call = audit_log.info.call_args_list[0].kwargs
    tool_result = audit_log.info.call_args_list[1].kwargs
    assert tool_call["type"] == "Tool Call"
    assert tool_call["data"]["query"] == "reset printer"
    assert tool_call["data"]["product"] is None
    assert tool_call["data"]["product_type"] is None
    assert tool_result["type"] == "Tool Result"
    assert tool_result["data"]["result_count"] == 1
    assert isinstance(tool_result["data"]["latency_ms"], int)
    assert tool_result["data"]["results"][0] == {
        "source": "manual.pdf",
        "page_number": 2,
        "score": 0.91,
        "product_name": None,
        "product_type": None,
        "text": "Reset steps",
    }


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
    assert config.max_tool_loop_iterations == 3
