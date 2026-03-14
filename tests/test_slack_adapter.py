from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from integrations.slack_adapter import SlackAdapter


class TestSlackAdapterConsoleMode:
    def test_init_console_mode(self):
        adapter = SlackAdapter(mode="console")
        assert adapter.mode == "console"

    def test_format_agent_message(self):
        adapter = SlackAdapter(mode="console")
        formatted = adapter.format_agent_message("Trinity", "Task complete.")
        assert "Trinity" in formatted
        assert "Task complete." in formatted

    @pytest.mark.asyncio
    async def test_post_message_console(self, capsys):
        adapter = SlackAdapter(mode="console")
        await adapter.post_message("Trinity", "Hello from Trinity.", thread_id=None)
        captured = capsys.readouterr()
        assert "Trinity" in captured.out
        assert "Hello from Trinity." in captured.out

    @pytest.mark.asyncio
    async def test_post_message_threaded_console(self, capsys):
        adapter = SlackAdapter(mode="console")
        await adapter.post_message(
            "Morpheus", "Code review done.", thread_id="thread-1"
        )
        captured = capsys.readouterr()
        assert "->" in captured.out
        assert "Morpheus" in captured.out


class TestSlackAdapterSlackMode:
    def test_init_slack_mode_requires_token(self):
        with pytest.raises(ValueError, match="SLACK_BOT_TOKEN"):
            SlackAdapter(mode="slack", bot_token="", channel_id="C123")
