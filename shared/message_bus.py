import asyncio
import json
import uuid

import redis.asyncio as aioredis

from config.settings import settings
from shared.models import AgentMessage


class MatrixMessageBus:
    """Redis-based inter-agent communication using Lists + pub/sub."""

    def __init__(
        self,
        redis_host: str | None = None,
        redis_port: int | None = None,
        connect: bool = True,
    ):
        self.redis_host = redis_host or settings.redis_host
        self.redis_port = redis_port or settings.redis_port
        self._redis: aioredis.Redis | None = None
        if connect:
            self._redis = aioredis.Redis(
                host=self.redis_host, port=self.redis_port, decode_responses=True
            )

    async def publish(self, channel: str, message: AgentMessage) -> None:
        """Push a message onto an agent's task queue."""
        queue_key = f"agent:{channel}"
        await self._redis.lpush(queue_key, message.model_dump_json())

    async def subscribe(
        self, agent_name: str, callback, timeout: float = 0
    ) -> None:
        """Block-wait for a message on an agent's queue and invoke callback."""
        queue_key = f"agent:{agent_name}"
        result = await self._redis.brpop(queue_key, timeout=int(timeout))
        if result:
            _, raw = result
            msg = AgentMessage.model_validate_json(raw)
            await callback(msg)

    async def request_response(
        self, target_agent: str, message: AgentMessage, timeout: int = 30
    ) -> AgentMessage | None:
        """Send a message and wait for a correlated response."""
        correlation_id = message.correlation_id or uuid.uuid4()
        message.correlation_id = correlation_id

        response_key = f"response:{correlation_id}"
        await self.publish(target_agent, message)

        result = await self._redis.brpop(response_key, timeout=timeout)
        if result:
            _, raw = result
            return AgentMessage.model_validate_json(raw)
        return None

    async def respond(self, correlation_id: uuid.UUID, message: AgentMessage) -> None:
        """Post a response to a request_response call."""
        response_key = f"response:{correlation_id}"
        await self._redis.lpush(response_key, message.model_dump_json())

    async def get_pending_messages(self, agent_name: str) -> list[AgentMessage]:
        """Get all pending messages without removing them."""
        queue_key = f"agent:{agent_name}"
        count = await self._redis.llen(queue_key)
        if count == 0:
            return []
        raw_messages = await self._redis.lrange(queue_key, 0, -1)
        return [AgentMessage.model_validate_json(raw) for raw in raw_messages]

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._redis:
            await self._redis.close()
