from dataclasses import dataclass
from typing import Callable

from app.tools.base import Tool
from app.tools.search_documents import DocumentSearcher, SearchDocumentsTool


class UnknownToolError(Exception):
    pass


@dataclass(frozen=True)
class ToolDeps:
    searcher: DocumentSearcher


ToolFactory = Callable[[ToolDeps], Tool]

_TOOL_FACTORIES: dict[str, ToolFactory] = {
    "search_documents": lambda deps: SearchDocumentsTool(deps.searcher),
}


def build_tool_set(names: tuple[str, ...], deps: ToolDeps) -> dict[str, Tool]:
    tools: dict[str, Tool] = {}
    for name in names:
        factory = _TOOL_FACTORIES.get(name)
        if factory is None:
            raise UnknownToolError(f"Unknown tool: {name}")
        tools[name] = factory(deps)
    return tools
