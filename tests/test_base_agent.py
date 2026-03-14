import pytest

from agents.base_agent import MatrixAgent
from shared.models import AgentResult


class StubAgent(MatrixAgent):
    """Concrete test agent."""

    async def execute(self, task: dict) -> AgentResult:
        return AgentResult(
            agent=self.name, status="success", content="stub response"
        )


class TestMatrixAgent:
    def test_init_loads_prompt(self):
        agent = StubAgent(name="Trinity", role="Executive Assistant")
        assert agent.name == "Trinity"
        assert agent.role == "Executive Assistant"
        assert agent.status == "IDLE"
        assert "Trinity" in agent.system_prompt

    def test_get_status(self):
        agent = StubAgent(name="Trinity", role="Executive Assistant")
        status = agent.get_status()
        assert status["name"] == "Trinity"
        assert status["status"] == "IDLE"

    @pytest.mark.asyncio
    async def test_execute_returns_agent_result(self):
        agent = StubAgent(name="Trinity", role="Executive Assistant")
        result = await agent.execute({"action": "test"})
        assert isinstance(result, AgentResult)
        assert result.agent == "Trinity"

    def test_unknown_agent_gets_empty_prompt(self):
        agent = StubAgent(name="UnknownAgent", role="Test")
        assert agent.system_prompt == ""
