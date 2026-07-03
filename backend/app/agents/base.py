from dataclasses import dataclass
from typing import Literal

ToolInvocation = Literal["always", "on_demand"]
AgentLoopMode = Literal["single_shot", "tool_loop"]


@dataclass(frozen=True)
class ToolBinding:
    name: str
    invocation: ToolInvocation


@dataclass(frozen=True)
class AgentConfig:
    name: str
    prompt: str
    tools: tuple[ToolBinding, ...]
    loop_mode: AgentLoopMode = "single_shot"

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(binding.name for binding in self.tools)
