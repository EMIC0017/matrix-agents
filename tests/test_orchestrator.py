from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestration.matrix_orchestrator import MatrixOrchestrator
from orchestration.protocol import Orchestrator, RoutingDecision
from orchestration.registry import AgentRegistry
from shared.models import AgentResult


class TestMatrixOrchestrator:
    def _make_orchestrator(self):
        registry = AgentRegistry()
        trinity = MagicMock()
        trinity.name = "Trinity"
        trinity.status = "IDLE"
        trinity.get_status.return_value = {
            "name": "Trinity",
            "role": "Assistant",
            "status": "IDLE",
        }
        trinity.execute = AsyncMock(
            return_value=AgentResult(
                agent="Trinity", status="success", content="Done."
            )
        )
        registry.register(trinity)
        return MatrixOrchestrator(registry=registry, llm_client=AsyncMock())

    def test_implements_protocol(self):
        orchestrator = self._make_orchestrator()
        assert isinstance(orchestrator, Orchestrator)

    @pytest.mark.asyncio
    async def test_dispatch_calls_agent_execute(self):
        orchestrator = self._make_orchestrator()
        result = await orchestrator.dispatch("Trinity", {"action": "test"})
        assert result.agent == "Trinity"
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_dispatch_unknown_agent_returns_error(self):
        orchestrator = self._make_orchestrator()
        result = await orchestrator.dispatch("Unknown", {"action": "test"})
        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_route_task_keyword_match(self):
        orchestrator = self._make_orchestrator()
        decision = await orchestrator.route_task(
            {"content": "write some code for me"}
        )
        assert isinstance(decision, RoutingDecision)
        assert "Morpheus" in decision.agents

    @pytest.mark.asyncio
    async def test_route_task_fallback_to_trinity(self):
        orchestrator = self._make_orchestrator()
        decision = await orchestrator.route_task(
            {"content": "something completely unrelated xyz"}
        )
        assert "Trinity" in decision.agents

    @pytest.mark.asyncio
    async def test_get_agent_statuses(self):
        orchestrator = self._make_orchestrator()
        statuses = await orchestrator.get_agent_statuses()
        assert "Trinity" in statuses
