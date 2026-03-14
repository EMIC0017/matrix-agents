from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from shared.models import AgentResult, AgentStatus


@dataclass
class RoutingDecision:
    """Result of task routing — which agent(s) should handle the task."""

    agents: list[str]
    parallel: bool = False
    priority: int = 5

    @staticmethod
    def fallback() -> RoutingDecision:
        """Default routing to Trinity."""
        return RoutingDecision(agents=["Trinity"])


@runtime_checkable
class Orchestrator(Protocol):
    """The COWORK seam — pluggable orchestration interface.

    Current implementation: MatrixOrchestrator (Merovingian + Redis).
    Future implementation: CoworkOrchestrator (COWORK SDK).
    """

    async def route_task(self, task: dict) -> RoutingDecision: ...

    async def dispatch(self, agent_name: str, task: dict) -> AgentResult: ...

    async def broadcast(self, message: dict) -> list[AgentResult]: ...

    async def get_agent_statuses(self) -> dict[str, AgentStatus]: ...
