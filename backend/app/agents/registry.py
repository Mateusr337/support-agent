from app.agents.base import AgentConfig
from app.agents.support.agent import SupportAgent
from app.agents.support.prompts import SYSTEM_PROMPT
from app.core.llm.base import LLMProvider
from app.rag.service import get_rag_service
from app.tools.registry import ToolDeps, build_tool_set


class UnknownAgentError(Exception):
    pass


AGENTS: dict[str, AgentConfig] = {
    "support": AgentConfig(
        name="support",
        prompt=SYSTEM_PROMPT,
        tools=("search_documents",),
    ),
}


def build_agent(name: str, llm: LLMProvider) -> SupportAgent:
    config = AGENTS.get(name)
    if config is None:
        raise UnknownAgentError(f"Unknown agent: {name}")

    tools = build_tool_set(
        config.tool_names,
        ToolDeps(searcher=get_rag_service()),
    )
    return SupportAgent(llm=llm, config=config, tools=tools)
