import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class AgentResult(BaseModel):
    """Result returned by an agent after executing a task."""

    agent: str
    status: str  # "success" | "error" | "partial"
    content: str
    data: dict = {}
    error: str | None = None


class AgentMessage(BaseModel):
    """Message format for inter-agent communication via the message bus."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str
    target: str
    action: str  # "execute", "status_check", "shutdown"
    payload: dict
    priority: int = 5  # 1 (highest) to 10 (lowest)
    correlation_id: uuid.UUID | None = None


class AgentStatus(BaseModel):
    """Status report for an agent."""

    name: str
    role: str
    status: str = "IDLE"  # IDLE, ACTIVE, WAITING, ERROR
