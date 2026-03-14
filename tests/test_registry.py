from unittest.mock import MagicMock

import pytest

from orchestration.registry import AgentRegistry


class TestAgentRegistry:
    def test_register_and_get(self):
        registry = AgentRegistry()
        mock_agent = MagicMock()
        mock_agent.name = "Trinity"
        mock_agent.get_status.return_value = {"name": "Trinity", "status": "IDLE"}

        registry.register(mock_agent)
        assert registry.get("Trinity") is mock_agent

    def test_get_unknown_agent_returns_none(self):
        registry = AgentRegistry()
        assert registry.get("Unknown") is None

    def test_list_all(self):
        registry = AgentRegistry()
        for name in ["Trinity", "Morpheus"]:
            agent = MagicMock()
            agent.name = name
            registry.register(agent)

        agents = registry.list_all()
        assert len(agents) == 2
        assert "Trinity" in agents
        assert "Morpheus" in agents

    def test_get_statuses(self):
        registry = AgentRegistry()
        agent = MagicMock()
        agent.name = "Trinity"
        agent.get_status.return_value = {"name": "Trinity", "role": "Assistant", "status": "IDLE"}
        registry.register(agent)

        statuses = registry.get_statuses()
        assert "Trinity" in statuses
