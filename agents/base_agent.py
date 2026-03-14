from abc import ABC, abstractmethod
from pathlib import Path

import yaml

from shared.llm_client import BedrockClient
from shared.logger import get_agent_logger
from shared.models import AgentResult

# Load agent prompts once at module level
_PROMPTS_PATH = Path(__file__).parent.parent / "config" / "agent_prompts.yml"
_PROMPTS: dict = {}
if _PROMPTS_PATH.exists():
    with open(_PROMPTS_PATH) as f:
        _PROMPTS = yaml.safe_load(f) or {}


class MatrixAgent(ABC):
    """Abstract base class for all Matrix agents."""

    def __init__(self, name: str, role: str, llm_client: BedrockClient | None = None):
        self.name = name
        self.role = role
        self.status = "IDLE"
        self._logger = get_agent_logger(name)
        self._llm_client = llm_client

        # Load system prompt from config
        agent_key = name.lower()
        agent_config = _PROMPTS.get(agent_key, {})
        self.system_prompt = agent_config.get("prompt", "").strip()

    @abstractmethod
    async def execute(self, task: dict) -> AgentResult:
        """Execute a task and return a result. Each agent implements this."""
        ...

    async def call_llm(self, messages: list[dict], model: str | None = None) -> str:
        """Send messages to the LLM via BedrockClient."""
        if not self._llm_client:
            self._llm_client = BedrockClient()
        return await self._llm_client.chat(
            system_prompt=self.system_prompt,
            messages=messages,
            model=model,
        )

    def get_status(self) -> dict:
        """Return agent name, role, and current status."""
        return {"name": self.name, "role": self.role, "status": self.status}

    def log(self, level: str, message: str) -> None:
        """Log with agent name prefix."""
        getattr(self._logger, level.lower(), self._logger.info)(message)
