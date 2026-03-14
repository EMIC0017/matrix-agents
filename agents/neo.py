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


def build_registry(llm_client: BedrockClient, brain=None) -> AgentRegistry:
    registry = AgentRegistry()
    agents = [
        Trinity(llm_client=llm_client, brain=brain),
        Morpheus(llm_client=llm_client, brain=brain),
        Oracle(llm_client=llm_client, brain=brain),
        Keymaker(llm_client=llm_client, brain=brain),
        Tank(llm_client=llm_client, brain=brain),
        Niobe(llm_client=llm_client, brain=brain),
        Mouse(llm_client=llm_client, brain=brain),
        Smith(llm_client=llm_client, brain=brain),
        Architect(llm_client=llm_client, brain=brain),
    ]
    for agent in agents:
        registry.register(agent)
    return registry


async def handle_meta_command(
    command: str, orchestrator: MatrixOrchestrator, adapter: SlackAdapter,
    brain=None,
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
            "  /capture <text>  - Save a thought to Matrix Brain\n"
            "  /brain   - Show brain stats\n"
            "  /brain search <query>  - Search the brain\n"
            "  /help    - Show this message\n"
            "  /quit    - Exit the Matrix"
        )
        await adapter.post_message("Neo", help_text)
        return False

    # /capture <text>
    if command.startswith("/capture"):
        text = command[8:].strip()
        if not text:
            await adapter.post_message("Neo", "Usage: /capture <your thought>")
            return False
        if brain:
            from shared.brain_extractor import BrainExtractor
            extractor = BrainExtractor(llm_client=BedrockClient())
            thought_id = await extractor.capture_enriched(brain, text, source="console")
            stats = await brain.stats()
            await adapter.post_message(
                "Neo", f"Captured to Matrix Brain (ID: {thought_id[:8]}...) "
                       f"| Total: {stats['count']} thoughts"
            )
        else:
            await adapter.post_message("Neo", "Brain not available.")
        return False

    # /brain or /brain search <query>
    if command.startswith("/brain"):
        if not brain:
            await adapter.post_message("Neo", "Brain not available.")
            return False
        args = command[6:].strip()
        if args.startswith("search "):
            query = args[7:].strip()
            results = await brain.search(query, n_results=5)
            if results:
                lines = []
                for r in results:
                    cat = r["metadata"].get("category", "?")
                    lines.append(f"  [{cat}] {r['content'][:80]}")
                await adapter.post_message("Neo", "Brain search results:\n" + "\n".join(lines))
            else:
                await adapter.post_message("Neo", "No results found.")
        else:
            stats = await brain.stats()
            lines = [f"Thoughts: {stats['count']}"]
            if stats["categories"]:
                cats = ", ".join(f"{k}: {v}" for k, v in stats["categories"].items())
                lines.append(f"Categories: {cats}")
            await adapter.post_message("Neo", "Matrix Brain:\n" + "\n".join(lines))
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
    orchestrator: MatrixOrchestrator, adapter: SlackAdapter, brain=None
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

        cmd_lower = user_input.lower()
        is_command = cmd_lower in META_COMMANDS or cmd_lower.startswith("/capture") or cmd_lower.startswith("/brain")
        if is_command:
            should_exit = await handle_meta_command(
                cmd_lower, orchestrator, adapter, brain=brain
            )
            if should_exit:
                break
        else:
            await process_task(user_input, orchestrator, adapter)

        console.print()


async def main() -> None:
    logger.info("Initializing Neo...")

    from shared.brain import MatrixBrain
    brain = MatrixBrain(mode=settings.brain_mode, data_path=settings.brain_data_path)
    logger.info(f"Matrix Brain online ({settings.brain_mode} mode)")

    llm_client = BedrockClient()
    registry = build_registry(llm_client, brain=brain)
    orchestrator = MatrixOrchestrator(registry=registry, llm_client=llm_client)
    adapter = SlackAdapter()

    if settings.slack_mode == "console":
        await console_loop(orchestrator, adapter, brain=brain)
    else:
        async def on_slack_message(text: str, thread_id: str | None) -> None:
            cmd = text.strip().lower()
            is_command = cmd in META_COMMANDS or cmd.startswith("/capture") or cmd.startswith("/brain")
            if is_command:
                await handle_meta_command(cmd, orchestrator, adapter, brain=brain)
            else:
                await process_task(text, orchestrator, adapter, thread_id)

        async def on_slack_capture(text: str, user: str, thread_ts: str) -> None:
            from shared.brain_extractor import BrainExtractor
            extractor = BrainExtractor(llm_client=llm_client)
            thought_id = await extractor.capture_enriched(brain, text, source=f"slack:{user}")
            stats = await brain.stats()
            results = await brain.search(text, n_results=1)
            meta = results[0]["metadata"] if results else {}
            cat = meta.get("category", "uncategorized")
            summary = meta.get("summary", text[:50])
            await adapter.post_message(
                "Neo",
                f"Captured as {cat} — {summary}\nTotal: {stats['count']} thoughts",
                thread_id=thread_ts,
            )

        adapter.on_message(on_slack_message)
        adapter.on_capture(on_slack_capture)
        logger.info("Neo is online in Slack mode.")
        await adapter.start()

    logger.info("Neo signing off.")


if __name__ == "__main__":
    asyncio.run(main())
