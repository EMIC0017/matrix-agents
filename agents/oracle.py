from agents.base_agent import MatrixAgent
from shared.models import AgentResult


class Oracle(MatrixAgent):
    """Oracle - Research & Knowledge Retrieval specialist with Brain-augmented search."""

    def __init__(self, **kwargs):
        super().__init__(name="Oracle", role="Research & Knowledge Retrieval", **kwargs)

    async def execute(self, task: dict) -> AgentResult:
        self.log("info", f"Received task: {task.get('action', 'unknown')}")
        try:
            content = task.get("content", "")

            # Search brain for relevant context
            context = ""
            if self.brain:
                results = await self.brain.search(content, n_results=3)
                if results:
                    context_lines = [f"- {r['content']}" for r in results]
                    context = "Relevant from Matrix Brain:\n" + "\n".join(context_lines)

            prompt = f"Research the following and provide a thorough answer:\n\n{content}"
            if context:
                prompt = f"{context}\n\n---\n\n{prompt}"

            response = await self.call_llm([{"role": "user", "content": prompt}])

            # Capture research result back to brain
            if self.brain:
                await self.brain.capture(
                    response[:500], source="Oracle",
                    metadata={"category": "reference"},
                )

            return AgentResult(agent=self.name, status="success", content=response)
        except Exception as e:
            self.log("error", f"Execution failed: {e}")
            return AgentResult(agent=self.name, status="error", content="", error=str(e))
