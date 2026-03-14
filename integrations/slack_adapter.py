from __future__ import annotations

from pathlib import Path
from typing import Callable

import yaml
from rich.console import Console
from rich.text import Text

from config.settings import settings
from shared.logger import get_agent_logger

# Load agent identities
_IDENTITIES_PATH = Path(__file__).parent.parent / "config" / "agent_identities.yml"
_IDENTITIES: dict = {}
if _IDENTITIES_PATH.exists():
    with open(_IDENTITIES_PATH) as f:
        _IDENTITIES = yaml.safe_load(f) or {}

_logger = get_agent_logger("SlackAdapter")


class SlackAdapter:
    """Human-facing I/O layer. Supports Slack and console modes."""

    def __init__(
        self,
        mode: str | None = None,
        bot_token: str | None = None,
        channel_id: str | None = None,
    ):
        self.mode = mode or settings.slack_mode
        self._console = Console()
        self._slack_app = None
        self._on_message: Callable | None = None

        if self.mode == "slack":
            _bot_token = bot_token if bot_token is not None else settings.slack_bot_token
            _channel_id = channel_id if channel_id is not None else settings.slack_channel_id
            if not _bot_token:
                raise ValueError("SLACK_BOT_TOKEN is required for Slack mode")
            if not _channel_id:
                raise ValueError("SLACK_CHANNEL_ID is required for Slack mode")
            self._channel_id = _channel_id
            self._init_slack(_bot_token)

    def _init_slack(self, bot_token: str) -> None:
        """Initialize the Slack Bolt app."""
        from slack_bolt.async_app import AsyncApp

        self._slack_app = AsyncApp(token=bot_token)

        @self._slack_app.event("message")
        async def handle_message(event, say):
            if self._on_message and event.get("subtype") is None:
                text = event.get("text", "")
                thread_ts = event.get("ts")
                await self._on_message(text, thread_ts)

    def on_message(self, callback: Callable) -> None:
        """Register a callback for incoming messages."""
        self._on_message = callback

    def format_agent_message(self, agent_name: str, content: str) -> str:
        """Format a message with agent identity."""
        identity = _IDENTITIES.get(agent_name.lower(), {})
        display_name = identity.get("display_name", agent_name)
        return f"[{display_name}] {content}"

    async def post_message(
        self, agent_name: str, content: str, thread_id: str | None = None
    ) -> None:
        """Post a message as an agent."""
        if self.mode == "console":
            self._post_console(agent_name, content, thread_id)
        else:
            await self._post_slack(agent_name, content, thread_id)

    def _post_console(
        self, agent_name: str, content: str, thread_id: str | None
    ) -> None:
        """Print to console with agent identity and color."""
        identity = _IDENTITIES.get(agent_name.lower(), {})
        display_name = identity.get("display_name", agent_name)
        color = identity.get("color", "white")

        if thread_id:
            prefix = f"  -> [{display_name}]: "
        else:
            prefix = f"[{display_name}]: "

        text = Text()
        text.append(prefix, style=color)
        text.append(content)
        self._console.print(text)

    async def _post_slack(
        self, agent_name: str, content: str, thread_id: str | None
    ) -> None:
        """Post to Slack with agent identity overrides."""
        if not self._slack_app:
            return

        identity = _IDENTITIES.get(agent_name.lower(), {})
        display_name = identity.get("display_name", agent_name)
        emoji = identity.get("emoji", ":robot_face:")

        try:
            await self._slack_app.client.chat_postMessage(
                channel=self._channel_id,
                text=content,
                username=display_name,
                icon_emoji=emoji,
                thread_ts=thread_id,
            )
        except Exception as e:
            _logger.error(f"Slack post failed: {e}")
            try:
                await self._slack_app.client.chat_postMessage(
                    channel=self._channel_id,
                    text=content,
                    username=display_name,
                    icon_emoji=emoji,
                    thread_ts=thread_id,
                )
            except Exception:
                _logger.error(f"Slack retry failed: {e}")

    async def start(self) -> None:
        """Start listening for messages."""
        if self.mode == "slack" and self._slack_app:
            from slack_bolt.adapter.starlette.async_handler import AsyncSlackRequestHandler
            from starlette.applications import Starlette
            from starlette.routing import Route
            import uvicorn

            handler = AsyncSlackRequestHandler(self._slack_app)

            async def endpoint(req):
                return await handler.handle(req)

            app = Starlette(routes=[Route("/slack/events", endpoint=endpoint, methods=["POST"])])
            config = uvicorn.Config(app, host="0.0.0.0", port=3000)
            server = uvicorn.Server(config)
            await server.serve()

    async def stop(self) -> None:
        """Stop the adapter."""
        _logger.info("SlackAdapter stopped")
