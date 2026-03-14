from unittest.mock import AsyncMock, patch

import pytest

from agents.trinity import Trinity
from agents.morpheus import Morpheus
from agents.oracle import Oracle
from agents.keymaker import Keymaker
from agents.tank import Tank
from agents.niobe import Niobe
from agents.mouse import Mouse
from agents.smith import Smith
from agents.architect import Architect
from shared.models import AgentResult


AGENT_CLASSES = [
    (Trinity, "Trinity", "Executive Assistant"),
    (Morpheus, "Morpheus", "Code Generation & Execution"),
    (Oracle, "Oracle", "Research & Knowledge Retrieval"),
    (Keymaker, "Keymaker", "API & Integration Management"),
    (Tank, "Tank", "DevOps & Infrastructure"),
    (Niobe, "Niobe", "Security & Access Control"),
    (Mouse, "Mouse", "Data Collection & Processing"),
    (Smith, "Smith", "Testing & Adversarial QA"),
    (Architect, "Architect", "System Design & Planning"),
]


class TestAllAgents:
    @pytest.mark.parametrize("cls,name,role", AGENT_CLASSES)
    def test_agent_instantiation(self, cls, name, role):
        agent = cls()
        assert agent.name == name

    @pytest.mark.parametrize("cls,name,role", AGENT_CLASSES)
    @pytest.mark.asyncio
    async def test_agent_execute_returns_result(self, cls, name, role):
        agent = cls()
        agent.call_llm = AsyncMock(return_value=f"Response from {name}")
        result = await agent.execute({"content": "test task", "action": "test"})
        assert isinstance(result, AgentResult)
        assert result.agent == name
        assert result.status == "success"

    @pytest.mark.parametrize("cls,name,role", AGENT_CLASSES)
    @pytest.mark.asyncio
    async def test_agent_execute_handles_llm_error(self, cls, name, role):
        agent = cls()
        agent.call_llm = AsyncMock(side_effect=Exception("LLM timeout"))
        result = await agent.execute({"content": "test", "action": "test"})
        assert result.status == "error"
        assert result.error is not None
