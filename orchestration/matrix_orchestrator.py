from __future__ import annotations

import json
import re
import traceback
from pathlib import Path

import yaml

from orchestration.protocol import RoutingDecision
from orchestration.registry import AgentRegistry
from shared.llm_client import BedrockClient
from shared.logger import get_agent_logger
from shared.models import AgentResult, AgentStatus

# Load routing rules
_RULES_PATH = Path(__file__).parent.parent / "config" / "routing_rules.yml"
_RULES: dict = {}
if _RULES_PATH.exists():
    with open(_RULES_PATH) as f:
        _RULES = yaml.safe_load(f) or {}

# Load Merovingian's prompt
_PROMPTS_PATH = Path(__file__).parent.parent / "config" / "agent_prompts.yml"
_MEROVINGIAN_PROMPT = ""
if _PROMPTS_PATH.exists():
    with open(_PROMPTS_PATH) as f:
        prompts = yaml.safe_load(f) or {}
        _MEROVINGIAN_PROMPT = prompts.get("merovingian", {}).get("prompt", "")


class MatrixOrchestrator:
    """Current orchestration implementation using Merovingian + keyword routing."""

    def __init__(
        self,
        registry: AgentRegistry,
        llm_client: BedrockClient | None = None,
    ):
        self._registry = registry
        self._llm_client = llm_client
        self._logger = get_agent_logger("Merovingian")
        self._keyword_routes = _RULES.get("keyword_routes", {})
        self._fallback = _RULES.get("fallback_agent", "trinity")
        self._default_priority = _RULES.get("default_priority", 5)

    async def route_task(self, task: dict) -> RoutingDecision:
        """Route a task to the appropriate agent(s)."""
        content = task.get("content", "").lower()

        # Fast path: keyword matching
        for _route_name, route_config in self._keyword_routes.items():
            keywords = route_config.get("keywords", [])
            if any(kw in content for kw in keywords):
                agent_name = route_config["agent"].capitalize()
                self._logger.info(f"Keyword route -> {agent_name}")
                return RoutingDecision(
                    agents=[agent_name], priority=self._default_priority
                )

        # Slow path: LLM routing via Merovingian
        if self._llm_client and _MEROVINGIAN_PROMPT:
            try:
                response = await self._llm_client.chat(
                    system_prompt=_MEROVINGIAN_PROMPT,
                    messages=[{"role": "user", "content": content}],
                )
                # Extract JSON from response — handle LLM wrapping it in text
                json_str = response.strip()
                json_match = re.search(r"\{.*\}", json_str, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                parsed = json.loads(json_str)
                agents = [a.capitalize() for a in parsed.get("agents", [])]
                if agents:
                    return RoutingDecision(
                        agents=agents,
                        parallel=parsed.get("parallel", False),
                        priority=parsed.get("priority", self._default_priority),
                    )
            except (json.JSONDecodeError, KeyError, Exception) as e:
                self._logger.warning(f"LLM routing failed: {e}, using fallback")

        # Fallback to Trinity
        self._logger.info("Falling back to Trinity")
        return RoutingDecision.fallback()

    async def dispatch(self, agent_name: str, task: dict) -> AgentResult:
        """Dispatch a task to a specific agent."""
        agent = self._registry.get(agent_name)
        if not agent:
            return AgentResult(
                agent=agent_name,
                status="error",
                content="",
                error=f"Agent '{agent_name}' not found in registry",
            )

        try:
            agent.status = "ACTIVE"
            result = await agent.execute(task)
            agent.status = "IDLE"
            return result
        except Exception as e:
            agent.status = "ERROR"
            self._logger.error(f"{agent_name} crashed: {traceback.format_exc()}")
            return AgentResult(
                agent=agent_name,
                status="error",
                content="",
                error=str(e),
            )

    async def broadcast(self, message: dict) -> list[AgentResult]:
        """Send a message to all registered agents."""
        results = []
        for name, agent in self._registry.list_all().items():
            try:
                result = await agent.execute(message)
                results.append(result)
            except Exception as e:
                results.append(
                    AgentResult(agent=name, status="error", content="", error=str(e))
                )
        return results

    async def get_agent_statuses(self) -> dict[str, AgentStatus]:
        """Get status of all registered agents."""
        statuses = {}
        for name, status_dict in self._registry.get_statuses().items():
            statuses[name] = AgentStatus(**status_dict)
        return statuses
