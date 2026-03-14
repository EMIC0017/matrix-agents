from agents.base_agent import MatrixAgent
from shared.models import AgentResult


class Trinity(MatrixAgent):
    """Trinity - Executive Assistant. Fallback agent for general tasks."""

    def __init__(self, **kwargs):
        super().__init__(name="Trinity", role="Executive Assistant", **kwargs)

    async def execute(self, task: dict) -> AgentResult:
        self.log("info", f"Received task: {task.get('action', 'unknown')}")
        try:
            content = task.get("content", "")
            response = await self.call_llm(
                [{"role": "user", "content": content}]
            )
            return AgentResult(agent=self.name, status="success", content=response)
        except Exception as e:
            self.log("error", f"Execution failed: {e}")
            return AgentResult(
                agent=self.name, status="error", content="", error=str(e)
            )
