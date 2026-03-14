import asyncio
import sys

from rich.console import Console
from rich.table import Table

from agents.architect import Architect
from agents.keymaker import Keymaker
from agents.morpheus import Morpheus
from agents.mouse import Mouse
from agents.niobe import Niobe
from agents.oracle import Oracle
from agents.smith import Smith
from agents.tank import Tank
from agents.trinity import Trinity
from config.settings import settings
from integrations.slack_adapter import SlackAdapter
from orchestration.matrix_orchestrator import MatrixOrchestrator
from orchestration.registry import AgentRegistry
from shared.llm_client import BedrockClient
from shared.logger import get_agent_logger
from shared.utils import MATRIX_BANNER

console = Console()
logger = get_agent_logger("Neo")

META_COMMANDS = {"/status", "/agents", "/health", "/help", "/quit", "/exit"}


def build_registry(llm_client: BedrockClient) -> AgentRegistry:
    registry = AgentRegistry()
    agents = [
        Trinity(llm_client=llm_client),
        Morpheus(llm_client=llm_client),
        Oracle(llm_client=llm_client),
        Keymaker(llm_client=llm_client),
        Tank(llm_client=llm_client),
        Niobe(llm_client=llm_client),
        Mouse(llm_client=llm_client),
        Smith(llm_client=llm_client),
        Architect(llm_client=llm_client),
    ]
    for agent in agents:
        registry.register(agent)
    return registry


async def handle_meta_command(
    command: str, orchestrator: MatrixOrchestrator, adapter: SlackAdapter
) -> bool:
    if command in ("/quit", "/exit"):
        await adapter.post_message("Neo", "You are now leaving the Matrix.")
        return True

    if command == "/help":
        help_text = (
            "Available commands:\n"
            "  /status  - Show status of all agents\n"
            "  /agents  - List all agents with roles\n"
            "  /health  - Run health checks\n"
            "  /help    - Show this message\n"
            "  /quit    - Exit the Matrix"
        )
        await adapter.post_message("Neo", help_text)
        return False

    if command == "/agents":
        statuses = await orchestrator.get_agent_statuses()
        table = Table(title="Matrix Agent Roster")
        table.add_column("Agent", style="cyan")
        table.add_column("Role", style="green")
        table.add_column("Status", style="yellow")
        for name, status in statuses.items():
            table.add_row(name, status.role, status.status)
        console.print(table)
        return False

    if command == "/status":
        statuses = await orchestrator.get_agent_statuses()
        lines = [f"  {name}: {s.status}" for name, s in statuses.items()]
        await adapter.post_message("Neo", "Agent Status:\n" + "\n".join(lines))
        return False

    if command == "/health":
        await adapter.post_message("Neo", "Health check: all agents responding.")
        return False

    return False


async def process_task(
    content: str,
    orchestrator: MatrixOrchestrator,
    adapter: SlackAdapter,
    thread_id: str | None = None,
) -> None:
    task = {"content": content, "action": "user_request"}

    decision = await orchestrator.route_task(task)
    agents_str = ", ".join(decision.agents)
    await adapter.post_message("Neo", f"Routing to: {agents_str}", thread_id)

    for agent_name in decision.agents:
        result = await orchestrator.dispatch(agent_name, task)
        if result.status == "error":
            await adapter.post_message(
                agent_name, f"Error: {result.error}", thread_id
            )
        else:
            await adapter.post_message(agent_name, result.content, thread_id)


async def console_loop(
    orchestrator: MatrixOrchestrator, adapter: SlackAdapter
) -> None:
    console.print(MATRIX_BANNER, style="green")
    console.print("[bold green]Neo is online. Type a task or /help for commands.[/]")
    console.print()

    while True:
        try:
            user_input = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("You> ")
            )
        except (EOFError, KeyboardInterrupt):
            await adapter.post_message("Neo", "You are now leaving the Matrix.")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input.lower() in META_COMMANDS:
            should_exit = await handle_meta_command(
                user_input.lower(), orchestrator, adapter
            )
            if should_exit:
                break
        else:
            await process_task(user_input, orchestrator, adapter)

        console.print()


async def main() -> None:
    logger.info("Initializing Neo...")

    llm_client = BedrockClient()
    registry = build_registry(llm_client)
    orchestrator = MatrixOrchestrator(registry=registry, llm_client=llm_client)
    adapter = SlackAdapter()

    if settings.slack_mode == "console":
        await console_loop(orchestrator, adapter)
    else:
        async def on_slack_message(text: str, thread_id: str | None) -> None:
            if text.strip().lower() in META_COMMANDS:
                await handle_meta_command(text.strip().lower(), orchestrator, adapter)
            else:
                await process_task(text, orchestrator, adapter, thread_id)

        adapter.on_message(on_slack_message)
        logger.info("Neo is online in Slack mode.")
        await adapter.start()

    logger.info("Neo signing off.")


if __name__ == "__main__":
    asyncio.run(main())
