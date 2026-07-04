from unittest.mock import MagicMock, patch

import pytest

from app.agents.registry import AGENTS, UnknownAgentError, build_agent
from app.agents.support import SupportAgent


def test_agents_catalog_contains_support():
    assert "support" in AGENTS
    assert AGENTS["support"].name == "support"


@patch("app.agents.registry.get_rag_service")
def test_build_agent_returns_support_agent(mock_get_rag_service):
    mock_get_rag_service.return_value = MagicMock()
    agent = build_agent("support", MagicMock())

    assert isinstance(agent, SupportAgent)


def test_build_agent_raises_for_unknown_agent():
    with pytest.raises(UnknownAgentError, match="Unknown agent: missing"):
        build_agent("missing", MagicMock())
