from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    name: str
    prompt: str
    tools: tuple[str, ...]
    max_tool_loop_iterations: int = 2

    @property
    def tool_names(self) -> tuple[str, ...]:
        return self.tools
