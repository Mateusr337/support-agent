from app.agents.base import AgentConfig, ToolBinding
from app.agents.prompts import SYSTEM_PROMPT
from app.agents.support_agent import SupportAgent
from app.core.llm.base import LLMProvider
from app.rag.service import get_rag_service
from app.tools.registry import ToolDeps, build_tool_set


class UnknownAgentError(Exception):
    pass


AGENTS: dict[str, AgentConfig] = {
    "support": AgentConfig(
        name="support",
        prompt=SYSTEM_PROMPT,
        tools=(ToolBinding("search_documents", "always"),),
        loop_mode="single_shot",
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
