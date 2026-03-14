import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.message_bus import MatrixMessageBus
from shared.models import AgentMessage


class TestMatrixMessageBus:
    def test_init(self):
        bus = MatrixMessageBus(redis_host="localhost", redis_port=6379, connect=False)
        assert bus.redis_host == "localhost"
        assert bus.redis_port == 6379

    @pytest.mark.asyncio
    async def test_publish_serializes_message(self):
        bus = MatrixMessageBus(redis_host="localhost", redis_port=6379, connect=False)
        bus._redis = AsyncMock()

        msg = AgentMessage(
            source="Neo", target="Trinity", action="execute", payload={"task": "hi"}
        )

        await bus.publish("Trinity", msg)

        bus._redis.lpush.assert_called_once()
        call_args = bus._redis.lpush.call_args
        assert call_args[0][0] == "agent:Trinity"
        parsed = json.loads(call_args[0][1])
        assert parsed["source"] == "Neo"

    @pytest.mark.asyncio
    async def test_get_pending_messages_empty(self):
        bus = MatrixMessageBus(redis_host="localhost", redis_port=6379, connect=False)
        bus._redis = AsyncMock()
        bus._redis.llen = AsyncMock(return_value=0)

        messages = await bus.get_pending_messages("Trinity")
        assert messages == []

    @pytest.mark.asyncio
    async def test_request_response_with_correlation(self):
        bus = MatrixMessageBus(redis_host="localhost", redis_port=6379, connect=False)
        bus._redis = AsyncMock()

        response_msg = AgentMessage(
            source="Trinity", target="Neo", action="execute", payload={"result": "ok"}
        )
        bus._redis.brpop = AsyncMock(
            return_value=("response:some-id", response_msg.model_dump_json())
        )

        request_msg = AgentMessage(
            source="Neo", target="Trinity", action="execute", payload={"task": "hi"}
        )
        result = await bus.request_response("Trinity", request_msg, timeout=5)

        assert result is not None
        assert result.source == "Trinity"
        bus._redis.lpush.assert_called_once()
