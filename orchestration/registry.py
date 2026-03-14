from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.base_agent import MatrixAgent


class AgentRegistry:
    """Name-to-instance lookup for registered agents."""

    def __init__(self):
        self._agents: dict[str, MatrixAgent] = {}

    def register(self, agent: MatrixAgent) -> None:
        """Register an agent by its name."""
        self._agents[agent.name] = agent

    def get(self, name: str) -> MatrixAgent | None:
        """Get an agent by name, or None if not found."""
        return self._agents.get(name)

    def list_all(self) -> dict[str, MatrixAgent]:
        """Return all registered agents."""
        return dict(self._agents)

    def get_statuses(self) -> dict[str, dict]:
        """Return status of all registered agents."""
        return {name: agent.get_status() for name, agent in self._agents.items()}
