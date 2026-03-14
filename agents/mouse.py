from agents.base_agent import MatrixAgent
from shared.models import AgentResult


class Mouse(MatrixAgent):
    """Mouse - Data Collection & Processing specialist."""

    def __init__(self, **kwargs):
        super().__init__(name="Mouse", role="Data Collection & Processing", **kwargs)

    async def execute(self, task: dict) -> AgentResult:
        self.log("info", f"Received task: {task.get('action', 'unknown')}")
        try:
            content = task.get("content", "")
            prompt = f"Help with the following data task:\n\n{content}"
            response = await self.call_llm([{"role": "user", "content": prompt}])
            return AgentResult(agent=self.name, status="success", content=response)
        except Exception as e:
            self.log("error", f"Execution failed: {e}")
            return AgentResult(agent=self.name, status="error", content="", error=str(e))
