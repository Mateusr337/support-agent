from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

from app.core.config import settings
from app.rag.manifest import DocumentManifestEntry, load_manifest
from app.tools.base import Tool
from app.tools.search_documents import DocumentSearcher, SearchDocumentsTool


@lru_cache
def _load_manifest_entries() -> tuple[DocumentManifestEntry, ...]:
    try:
        return load_manifest(settings.resolved_documents_dir)
    except (FileNotFoundError, ValueError):
        return ()


class UnknownToolError(Exception):
    pass


@dataclass(frozen=True)
class ToolDeps:
    searcher: DocumentSearcher


ToolFactory = Callable[[ToolDeps], Tool]

_TOOL_FACTORIES: dict[str, ToolFactory] = {
    "search_documents": lambda deps: SearchDocumentsTool(
        deps.searcher,
        manifest_entries=_load_manifest_entries(),
    ),
}


def build_tool_set(names: tuple[str, ...], deps: ToolDeps) -> dict[str, Tool]:
    tools: dict[str, Tool] = {}
    for name in names:
        factory = _TOOL_FACTORIES.get(name)
        if factory is None:
            raise UnknownToolError(f"Unknown tool: {name}")
        tools[name] = factory(deps)
    return tools
