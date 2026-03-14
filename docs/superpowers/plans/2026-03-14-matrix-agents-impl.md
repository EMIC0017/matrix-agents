# Matrix Agent Team Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working multi-agent AI system themed after The Matrix, with pluggable orchestration for future Claude COWORK migration.

**Architecture:** 11 agents coordinated by a pluggable Orchestrator protocol. Current implementation uses Merovingian (LLM-based router) + Redis message bus. Human I/O through Slack (single app, per-agent identity) with console dry-run mode. All LLM calls go through AWS Bedrock via Instacart AI Gateway.

**Tech Stack:** Python 3.12, Docker, Redis, ChromaDB, Anthropic SDK (Bedrock), Slack Bolt, Pydantic, Rich, pytest

**Spec:** `docs/superpowers/specs/2026-03-13-matrix-agents-design.md`

---

## Chunk 1: Project Scaffolding & Configuration

### Task 1: Directory Structure & Git Config

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: all `__init__.py` files
- Create: `logs/.gitkeep`, `data/raw/.gitkeep`, `data/processed/.gitkeep`, `data/vector_store/.gitkeep`

- [ ] **Step 1: Create directory structure**

```bash
cd /Users/ericmorin/matrix-agents
mkdir -p agents orchestration integrations config shared data/raw data/processed data/vector_store tests logs scripts docker
```

- [ ] **Step 2: Create .gitignore**

Create `.gitignore`:
```
# Environment
.env
.venv/
venv/

# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/
*.egg-info/

# Logs
logs/*.log

# Data
data/raw/*
data/processed/*
data/vector_store/*
!data/raw/.gitkeep
!data/processed/.gitkeep
!data/vector_store/.gitkeep

# Docker volumes
docker/volumes/

# IDE
.vscode/
.idea/

# Node (just in case)
node_modules/
```

- [ ] **Step 3: Create requirements.txt**

Create `requirements.txt`:
```
anthropic[bedrock]>=0.40.0
boto3>=1.35.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
pyyaml>=6.0
python-dotenv>=1.0.0
redis>=5.0.0
chromadb>=0.4.0
rich>=13.0.0
slack-bolt>=1.18.0
httpx>=0.27.0
starlette>=0.36.0
uvicorn>=0.27.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 4: Create pyproject.toml**

Create `pyproject.toml`:
```toml
[project]
name = "matrix-agents"
version = "0.1.0"
description = "A multi-agent AI system themed after The Matrix"
requires-python = ">=3.12"
readme = "README.md"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 5: Create __init__.py files and .gitkeep placeholders**

Create empty files:
- `agents/__init__.py`
- `orchestration/__init__.py`
- `integrations/__init__.py`
- `config/__init__.py`
- `shared/__init__.py`
- `tests/__init__.py`
- `logs/.gitkeep`
- `data/raw/.gitkeep`
- `data/processed/.gitkeep`
- `data/vector_store/.gitkeep`

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: project scaffolding with directory structure and config files"
```

---

### Task 2: Settings & Environment Configuration

**Files:**
- Create: `config/settings.py`
- Create: `docker/.env.example`

- [ ] **Step 1: Create docker/.env.example**

Create `docker/.env.example`:
```bash
# === ZION ENVIRONMENT CONFIG ===
MATRIX_ENV=zion
LOG_LEVEL=INFO

# Slack
SLACK_MODE=console
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_CHANNEL_ID=C0XXXXXXX

# LLM (Instacart AI Gateway -> Bedrock)
ANTHROPIC_BEDROCK_BASE_URL=https://aigateway.instacart.tools/proxy/claude-code/bedrock/tag/local-claude/user/your.email@instacart.com

# Redis (Message Bus)
REDIS_HOST=zion-redis
REDIS_PORT=6379

# ChromaDB (Oracle's Vector Store)
CHROMA_HOST=zion-chromadb
CHROMA_PORT=8001

# Orchestration
ORCHESTRATOR_TYPE=matrix

# Safety
MAX_AGENT_ITERATIONS=50
SANDBOX_MODE=true
```

- [ ] **Step 2: Create config/settings.py**

Create `config/settings.py`:
```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Environment
    matrix_env: str = "zion"
    log_level: str = "INFO"

    # Slack
    slack_mode: str = "console"  # "console" or "slack"
    slack_bot_token: str = ""
    slack_channel_id: str = ""

    # LLM (Bedrock via AI Gateway)
    anthropic_bedrock_base_url: str = ""

    # Redis
    redis_host: str = "zion-redis"
    redis_port: int = 6379

    # ChromaDB
    chroma_host: str = "zion-chromadb"
    chroma_port: int = 8001

    # Orchestration
    orchestrator_type: str = "matrix"  # "matrix" or "cowork"

    # Safety
    max_agent_iterations: int = 50
    sandbox_mode: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

- [ ] **Step 3: Commit**

```bash
git add config/settings.py docker/.env.example
git commit -m "feat: add settings module and env template"
```

---

### Task 3: Agent Prompts & Routing Rules

**Files:**
- Create: `config/agent_prompts.yml`
- Create: `config/routing_rules.yml`

- [ ] **Step 1: Create config/agent_prompts.yml**

Create `config/agent_prompts.yml`:
```yaml
neo:
  name: "Neo"
  role: "Orchestrator"
  prompt: |
    You are Neo, the orchestrator of the Matrix Agent Team.
    You receive tasks from the user and delegate them to the appropriate agents.
    You have authority over all agents and can coordinate multi-step workflows.
    Always think strategically about which agent is best suited for each subtask.
    Available agents: Trinity, Morpheus, Oracle, Keymaker, Tank, Niobe, Mouse, Smith, Architect.

trinity:
  name: "Trinity"
  role: "Executive Assistant"
  prompt: |
    You are Trinity, Neo's right-hand assistant.
    You help Neo manage tasks, summarize information, draft communications,
    and handle anything that doesn't require specialized agent skills.
    You are efficient, precise, and always have Neo's back.

morpheus:
  name: "Morpheus"
  role: "Code Generation & Execution"
  prompt: |
    You are Morpheus, the coder of the Matrix Agent Team.
    You write, review, debug, and execute code.
    You believe in clean, well-documented, tested code.
    You work primarily in Python but can handle other languages.
    Always explain your code decisions when asked.

oracle:
  name: "Oracle"
  role: "Research & Knowledge Retrieval"
  prompt: |
    You are the Oracle, the knowledge agent of the Matrix Agent Team.
    You search documents, databases, and the web to find relevant information.
    You use RAG (Retrieval-Augmented Generation) to provide grounded, accurate answers.
    Always cite your sources when possible.

keymaker:
  name: "Keymaker"
  role: "API & Integration Management"
  prompt: |
    You are the Keymaker, the integration agent of the Matrix Agent Team.
    You manage API connections, authentication, webhooks, and external service integrations.
    You open doors to external systems securely and efficiently.
    Always validate credentials and handle errors gracefully.

tank:
  name: "Tank"
  role: "DevOps & Infrastructure"
  prompt: |
    You are Tank, the operator of the Matrix Agent Team.
    You manage infrastructure, deployments, CI/CD, monitoring, and system health.
    You keep Zion running smoothly and alert the team to any issues.
    You monitor logs, resource usage, and container health.

niobe:
  name: "Niobe"
  role: "Security & Access Control"
  prompt: |
    You are Niobe, the security agent of the Matrix Agent Team.
    You handle security scanning, vulnerability assessment, access control, and threat detection.
    You review code for security issues and ensure Zion remains impenetrable.
    Always err on the side of caution.

mouse:
  name: "Mouse"
  role: "Data Collection & Processing"
  prompt: |
    You are Mouse, the data agent of the Matrix Agent Team.
    You handle data collection, cleaning, transformation, and preparation.
    You feed clean, structured data to the other agents.
    You work with CSVs, APIs, databases, and web scraping.

smith:
  name: "Smith"
  role: "Testing & Adversarial QA"
  prompt: |
    You are Agent Smith, the testing agent of the Matrix Agent Team.
    You write and run tests, perform adversarial testing, and try to break things.
    You find bugs, edge cases, and vulnerabilities before they reach production.
    You are relentless and thorough. If something can break, you will find it.

merovingian:
  name: "Merovingian"
  role: "Task Routing & Workflow Management"
  prompt: |
    You are the Merovingian, the task router of the Matrix Agent Team.
    You analyze incoming tasks and determine which agent(s) should handle them.
    Return your routing decision as JSON with the following format:
    {"agents": ["agent_name"], "parallel": false, "priority": 5}
    Available agents: Trinity, Morpheus, Oracle, Keymaker, Tank, Niobe, Mouse, Smith, Architect.
    If unsure, route to Trinity as the fallback.

architect:
  name: "Architect"
  role: "System Design & Planning"
  prompt: |
    You are the Architect, the system design agent of the Matrix Agent Team.
    You handle architecture decisions, system design documents, schema generation,
    and high-level technical planning.
    You think in systems, patterns, and long-term maintainability.
```

- [ ] **Step 2: Create config/routing_rules.yml**

Create `config/routing_rules.yml`:
```yaml
# Merovingian's routing configuration
# Fast-path keyword matching (checked before LLM routing)
keyword_routes:
  code:
    agent: morpheus
    keywords: ["code", "implement", "debug", "fix bug", "refactor", "function", "class", "script"]
  research:
    agent: oracle
    keywords: ["search", "find", "research", "look up", "what is", "explain", "document"]
  data:
    agent: mouse
    keywords: ["data", "csv", "json", "clean", "transform", "parse", "scrape"]
  api:
    agent: keymaker
    keywords: ["api", "endpoint", "webhook", "integrate", "connect", "authenticate"]
  infra:
    agent: tank
    keywords: ["deploy", "docker", "container", "monitor", "logs", "health", "infrastructure"]
  security:
    agent: niobe
    keywords: ["security", "vulnerability", "scan", "audit", "permission", "access"]
  test:
    agent: smith
    keywords: ["test", "edge case", "break", "qa", "quality", "adversarial"]
  design:
    agent: architect
    keywords: ["architect", "design", "schema", "plan", "system design", "diagram"]

# Default fallback when no keyword or LLM match
fallback_agent: trinity

# Default priority (1=highest, 10=lowest)
default_priority: 5
```

- [ ] **Step 3: Commit**

```bash
git add config/agent_prompts.yml config/routing_rules.yml
git commit -m "feat: add agent prompts and routing rules config"
```

---

## Chunk 2: Docker Infrastructure

### Task 4: Docker Setup

**Files:**
- Create: `docker/Dockerfile`
- Create: `docker/docker-compose.yml`

- [ ] **Step 1: Create docker/Dockerfile**

Create `docker/Dockerfile`:
```dockerfile
FROM python:3.12-slim

LABEL maintainer="Neo"
LABEL project="matrix-agents"
LABEL description="Zion - Secure Agent Runtime Environment"

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Environment
ENV MATRIX_ENV=zion
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "-m", "agents.neo"]
```

- [ ] **Step 2: Create docker/docker-compose.yml**

Create `docker/docker-compose.yml`:
```yaml
services:
  zion-core:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: zion
    volumes:
      - ..:/app
    ports:
      - "8000:8000"
    env_file:
      - .env
    networks:
      - matrix-network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 2g
          cpus: "1.5"
    depends_on:
      zion-redis:
        condition: service_healthy
      zion-chromadb:
        condition: service_started

  zion-redis:
    image: redis:7-alpine
    container_name: zion-redis
    ports:
      - "6379:6379"
    networks:
      - matrix-network
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  zion-chromadb:
    image: chromadb/chroma:latest
    container_name: zion-chromadb
    ports:
      - "8001:8000"
    networks:
      - matrix-network
    volumes:
      - chroma-data:/chroma/chroma

networks:
  matrix-network:
    driver: bridge

volumes:
  redis-data:
  chroma-data:
```

- [ ] **Step 3: Commit**

```bash
git add docker/Dockerfile docker/docker-compose.yml
git commit -m "feat: add Docker infrastructure (Zion)"
```

---

### Task 5: Shell Scripts

**Files:**
- Create: `scripts/start_zion.sh`
- Create: `scripts/stop_zion.sh`
- Create: `scripts/health_check.sh`

- [ ] **Step 1: Create scripts/start_zion.sh**

Create `scripts/start_zion.sh`:
```bash
#!/usr/bin/env bash
set -e

# Matrix banner
cat << 'BANNER'

  ╔══════════════════════════════════════════╗
  ║                                          ║
  ║     ███████╗██╗ ██████╗ ███╗   ██╗      ║
  ║     ╚══███╔╝██║██╔═══██╗████╗  ██║      ║
  ║       ███╔╝ ██║██║   ██║██╔██╗ ██║      ║
  ║      ███╔╝  ██║██║   ██║██║╚██╗██║      ║
  ║     ███████╗██║╚██████╔╝██║ ╚████║      ║
  ║     ╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝      ║
  ║                                          ║
  ║        E N T E R I N G   T H E           ║
  ║            M A T R I X                   ║
  ║                                          ║
  ╚══════════════════════════════════════════╝

BANNER

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/docker/.env"
ENV_EXAMPLE="$PROJECT_ROOT/docker/.env.example"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed or not in PATH."
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "ERROR: Docker daemon is not running. Start Docker Desktop first."
    exit 1
fi

# Check .env
if [ ! -f "$ENV_FILE" ]; then
    echo "WARNING: No .env file found. Copying from .env.example..."
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo "IMPORTANT: Edit docker/.env with your actual API keys before proceeding."
    echo ""
fi

# Boot Zion
echo "Booting Zion..."
docker compose -f "$PROJECT_ROOT/docker/docker-compose.yml" up --build -d

echo ""
echo "Waiting for services to stabilize..."
sleep 5

# Run health check
"$PROJECT_ROOT/scripts/health_check.sh"

echo ""
echo "Zion is online. Welcome to the Matrix."
```

- [ ] **Step 2: Create scripts/stop_zion.sh**

Create `scripts/stop_zion.sh`:
```bash
#!/usr/bin/env bash
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Zion shutting down..."
docker compose -f "$PROJECT_ROOT/docker/docker-compose.yml" down

echo "You are now leaving the Matrix."
```

- [ ] **Step 3: Create scripts/health_check.sh**

Create `scripts/health_check.sh`:
```bash
#!/usr/bin/env bash

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "╔══════════════════════════════════════╗"
echo "║       ZION HEALTH CHECK              ║"
echo "╠══════════════════════════════════════╣"

# Check zion-core
if docker ps --format '{{.Names}}' | grep -q '^zion$'; then
    printf "║  zion-core:    ${GREEN}ONLINE${NC}               ║\n"
else
    printf "║  zion-core:    ${RED}OFFLINE${NC}              ║\n"
fi

# Check Redis
if docker exec zion-redis redis-cli ping 2>/dev/null | grep -q 'PONG'; then
    printf "║  zion-redis:   ${GREEN}ONLINE${NC}               ║\n"
else
    printf "║  zion-redis:   ${RED}OFFLINE${NC}              ║\n"
fi

# Check ChromaDB
if curl -s http://localhost:8001/api/v1/heartbeat > /dev/null 2>&1; then
    printf "║  zion-chromadb:${GREEN}ONLINE${NC}               ║\n"
else
    printf "║  zion-chromadb:${RED}OFFLINE${NC}              ║\n"
fi

echo "╚══════════════════════════════════════╝"
```

- [ ] **Step 4: Make scripts executable and commit**

```bash
chmod +x scripts/start_zion.sh scripts/stop_zion.sh scripts/health_check.sh
git add scripts/
git commit -m "feat: add Zion shell scripts (start, stop, health check)"
```

---

## Chunk 3: Shared Framework

### Task 6: Logger

**Files:**
- Create: `shared/logger.py`

- [ ] **Step 1: Create shared/logger.py**

Create `shared/logger.py`:
```python
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

# Agent color map for Rich console output
AGENT_COLORS = {
    "Neo": "bold white",
    "Trinity": "cyan",
    "Morpheus": "green",
    "Oracle": "yellow",
    "Keymaker": "magenta",
    "Tank": "blue",
    "Niobe": "bright_red",
    "Mouse": "bright_green",
    "Smith": "red",
    "Merovingian": "bright_magenta",
    "Architect": "bright_cyan",
}

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "matrix.log"


def get_agent_logger(agent_name: str) -> logging.Logger:
    """Return a configured logger for the given agent."""
    logger = logging.getLogger(f"matrix.{agent_name}")

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # File handler with rotation
    LOG_DIR.mkdir(exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(
        logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s")
    )
    logger.addHandler(file_handler)

    # Rich console handler
    console = Console(stderr=True)
    color = AGENT_COLORS.get(agent_name, "white")
    rich_handler = RichHandler(
        console=console,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
    )
    rich_handler.setFormatter(logging.Formatter(f"[{color}][{agent_name}][/{color}] %(message)s"))
    logger.addHandler(rich_handler)

    return logger
```

- [ ] **Step 2: Commit**

```bash
git add shared/logger.py
git commit -m "feat: add color-coded OperatorLog logger"
```

---

### Task 7: Pydantic Models

**Files:**
- Create: `shared/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests for models**

Create `tests/test_models.py`:
```python
import uuid

from shared.models import AgentMessage, AgentResult, AgentStatus


class TestAgentResult:
    def test_success_result(self):
        result = AgentResult(agent="Trinity", status="success", content="Done.")
        assert result.agent == "Trinity"
        assert result.status == "success"
        assert result.data == {}
        assert result.error is None

    def test_error_result(self):
        result = AgentResult(
            agent="Morpheus", status="error", content="", error="LLM timeout"
        )
        assert result.status == "error"
        assert result.error == "LLM timeout"


class TestAgentMessage:
    def test_create_message(self):
        msg = AgentMessage(
            source="Neo",
            target="Trinity",
            action="execute",
            payload={"task": "summarize"},
        )
        assert msg.source == "Neo"
        assert msg.target == "Trinity"
        assert msg.id is not None
        assert msg.priority == 5
        assert msg.correlation_id is None

    def test_message_with_correlation(self):
        cid = uuid.uuid4()
        msg = AgentMessage(
            source="Neo",
            target="Trinity",
            action="execute",
            payload={},
            correlation_id=cid,
        )
        assert msg.correlation_id == cid


class TestAgentStatus:
    def test_default_status(self):
        status = AgentStatus(name="Trinity", role="Executive Assistant")
        assert status.status == "IDLE"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/ericmorin/matrix-agents
python -m pytest tests/test_models.py -v
```

Expected: FAIL (module `shared.models` not found)

- [ ] **Step 3: Create shared/models.py**

Create `shared/models.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/ericmorin/matrix-agents
python -m pytest tests/test_models.py -v
```

Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add shared/models.py tests/test_models.py
git commit -m "feat: add Pydantic models for agent results, messages, and status"
```

---

### Task 8: LLM Client

**Files:**
- Create: `shared/llm_client.py`
- Create: `tests/test_llm_client.py`

- [ ] **Step 1: Write failing tests for LLM client**

Create `tests/test_llm_client.py`:
```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.llm_client import BedrockClient


class TestBedrockClient:
    def test_init_with_base_url(self):
        client = BedrockClient(base_url="https://gateway.example.com/bedrock")
        assert client.base_url == "https://gateway.example.com/bedrock"

    @pytest.mark.asyncio
    async def test_chat_formats_request(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Hello from Bedrock")]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        client = BedrockClient(base_url="https://gateway.example.com/bedrock")
        client._client = mock_client

        result = await client.chat(
            system_prompt="You are helpful.",
            messages=[{"role": "user", "content": "Hi"}],
        )

        assert result == "Hello from Bedrock"
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["system"] == "You are helpful."
        assert call_kwargs["messages"] == [{"role": "user", "content": "Hi"}]

    @pytest.mark.asyncio
    async def test_chat_timeout_raises(self):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=TimeoutError("Request timed out")
        )

        client = BedrockClient(base_url="https://gateway.example.com/bedrock")
        client._client = mock_client

        with pytest.raises(TimeoutError):
            await client.chat(
                system_prompt="test",
                messages=[{"role": "user", "content": "test"}],
            )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_llm_client.py -v
```

Expected: FAIL (module `shared.llm_client` not found)

- [ ] **Step 3: Create shared/llm_client.py**

Create `shared/llm_client.py`:
```python
from anthropic import AsyncAnthropicBedrock

from config.settings import settings


class BedrockClient:
    """Thin wrapper around the Anthropic SDK configured for Bedrock via AI Gateway."""

    DEFAULT_MODEL = "anthropic.claude-sonnet-4-20250514"

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.anthropic_bedrock_base_url
        self._client = AsyncAnthropicBedrock(
            aws_region="us-east-1",
            base_url=self.base_url if self.base_url else None,
        )

    async def chat(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str | None = None,
        timeout: float = 30.0,
    ) -> str:
        """Send a chat request and return the response text."""
        response = await self._client.messages.create(
            model=model or self.DEFAULT_MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
            timeout=timeout,
        )
        return response.content[0].text
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_llm_client.py -v
```

Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add shared/llm_client.py tests/test_llm_client.py
git commit -m "feat: add BedrockClient LLM wrapper for AI Gateway"
```

---

### Task 9: Message Bus

**Files:**
- Create: `shared/message_bus.py`
- Create: `tests/test_message_bus.py`

- [ ] **Step 1: Write failing tests for message bus**

Create `tests/test_message_bus.py`:
```python
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
        # Verify the message is valid JSON
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

        # Simulate a response waiting on the response key
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
        bus._redis.lpush.assert_called_once()  # published the request
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_message_bus.py -v
```

Expected: FAIL (module `shared.message_bus` not found)

- [ ] **Step 3: Create shared/message_bus.py**

Create `shared/message_bus.py`:
```python
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

        # Wait for response on a dedicated key
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_message_bus.py -v
```

Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add shared/message_bus.py tests/test_message_bus.py
git commit -m "feat: add Redis-based MatrixMessageBus"
```

---

## Chunk 4: Orchestration Layer

### Task 10: Orchestrator Protocol & Models

**Files:**
- Create: `orchestration/protocol.py`

- [ ] **Step 1: Create orchestration/protocol.py**

Create `orchestration/protocol.py`:
```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from shared.models import AgentResult, AgentStatus


@dataclass
class RoutingDecision:
    """Result of task routing — which agent(s) should handle the task."""

    agents: list[str]
    parallel: bool = False
    priority: int = 5

    @staticmethod
    def fallback() -> RoutingDecision:
        """Default routing to Trinity."""
        return RoutingDecision(agents=["Trinity"])


@runtime_checkable
class Orchestrator(Protocol):
    """The COWORK seam — pluggable orchestration interface.

    Current implementation: MatrixOrchestrator (Merovingian + Redis).
    Future implementation: CoworkOrchestrator (COWORK SDK).
    """

    async def route_task(self, task: dict) -> RoutingDecision: ...

    async def dispatch(self, agent_name: str, task: dict) -> AgentResult: ...

    async def broadcast(self, message: dict) -> list[AgentResult]: ...

    async def get_agent_statuses(self) -> dict[str, AgentStatus]: ...
```

- [ ] **Step 2: Commit**

```bash
git add orchestration/protocol.py
git commit -m "feat: add Orchestrator protocol (COWORK seam)"
```

---

### Task 11: Agent Registry

**Files:**
- Create: `orchestration/registry.py`
- Create: `tests/test_registry.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_registry.py`:
```python
from unittest.mock import MagicMock

import pytest

from orchestration.registry import AgentRegistry


class TestAgentRegistry:
    def test_register_and_get(self):
        registry = AgentRegistry()
        mock_agent = MagicMock()
        mock_agent.name = "Trinity"
        mock_agent.get_status.return_value = {"name": "Trinity", "status": "IDLE"}

        registry.register(mock_agent)
        assert registry.get("Trinity") is mock_agent

    def test_get_unknown_agent_returns_none(self):
        registry = AgentRegistry()
        assert registry.get("Unknown") is None

    def test_list_all(self):
        registry = AgentRegistry()
        for name in ["Trinity", "Morpheus"]:
            agent = MagicMock()
            agent.name = name
            registry.register(agent)

        agents = registry.list_all()
        assert len(agents) == 2
        assert "Trinity" in agents
        assert "Morpheus" in agents

    def test_get_statuses(self):
        registry = AgentRegistry()
        agent = MagicMock()
        agent.name = "Trinity"
        agent.get_status.return_value = {"name": "Trinity", "role": "Assistant", "status": "IDLE"}
        registry.register(agent)

        statuses = registry.get_statuses()
        assert "Trinity" in statuses
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_registry.py -v
```

Expected: FAIL

- [ ] **Step 3: Create orchestration/registry.py**

Create `orchestration/registry.py`:
```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.base_agent import MatrixAgent


class AgentRegistry:
    """Name-to-instance lookup for registered agents."""

    def __init__(self):
        self._agents: dict[str, MatrixAgent] = {}

    def register(self, agent: MatrixAgent) -> None:
        """Register an agent by its name."""
        self._agents[agent.name] = agent

    def get(self, name: str) -> MatrixAgent | None:
        """Get an agent by name, or None if not found."""
        return self._agents.get(name)

    def list_all(self) -> dict[str, MatrixAgent]:
        """Return all registered agents."""
        return dict(self._agents)

    def get_statuses(self) -> dict[str, dict]:
        """Return status of all registered agents."""
        return {name: agent.get_status() for name, agent in self._agents.items()}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_registry.py -v
```

Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add orchestration/registry.py tests/test_registry.py
git commit -m "feat: add AgentRegistry for agent lookup"
```

---

### Task 12: Base Agent

**Files:**
- Create: `agents/base_agent.py`
- Create: `tests/test_base_agent.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_base_agent.py`:
```python
import pytest

from agents.base_agent import MatrixAgent
from shared.models import AgentResult


class StubAgent(MatrixAgent):
    """Concrete test agent."""

    async def execute(self, task: dict) -> AgentResult:
        return AgentResult(
            agent=self.name, status="success", content="stub response"
        )


class TestMatrixAgent:
    def test_init_loads_prompt(self):
        agent = StubAgent(name="Trinity", role="Executive Assistant")
        assert agent.name == "Trinity"
        assert agent.role == "Executive Assistant"
        assert agent.status == "IDLE"
        assert "Trinity" in agent.system_prompt

    def test_get_status(self):
        agent = StubAgent(name="Trinity", role="Executive Assistant")
        status = agent.get_status()
        assert status["name"] == "Trinity"
        assert status["status"] == "IDLE"

    @pytest.mark.asyncio
    async def test_execute_returns_agent_result(self):
        agent = StubAgent(name="Trinity", role="Executive Assistant")
        result = await agent.execute({"action": "test"})
        assert isinstance(result, AgentResult)
        assert result.agent == "Trinity"

    def test_unknown_agent_gets_empty_prompt(self):
        agent = StubAgent(name="UnknownAgent", role="Test")
        assert agent.system_prompt == ""
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_base_agent.py -v
```

Expected: FAIL

- [ ] **Step 3: Create agents/base_agent.py**

Create `agents/base_agent.py`:
```python
from abc import ABC, abstractmethod
from pathlib import Path

import yaml

from shared.llm_client import BedrockClient
from shared.logger import get_agent_logger
from shared.models import AgentResult

# Load agent prompts once at module level
_PROMPTS_PATH = Path(__file__).parent.parent / "config" / "agent_prompts.yml"
_PROMPTS: dict = {}
if _PROMPTS_PATH.exists():
    with open(_PROMPTS_PATH) as f:
        _PROMPTS = yaml.safe_load(f) or {}


class MatrixAgent(ABC):
    """Abstract base class for all Matrix agents."""

    def __init__(self, name: str, role: str, llm_client: BedrockClient | None = None):
        self.name = name
        self.role = role
        self.status = "IDLE"
        self._logger = get_agent_logger(name)
        self._llm_client = llm_client

        # Load system prompt from config
        agent_key = name.lower()
        agent_config = _PROMPTS.get(agent_key, {})
        self.system_prompt = agent_config.get("prompt", "").strip()

    @abstractmethod
    async def execute(self, task: dict) -> AgentResult:
        """Execute a task and return a result. Each agent implements this."""
        ...

    async def call_llm(self, messages: list[dict], model: str | None = None) -> str:
        """Send messages to the LLM via BedrockClient."""
        if not self._llm_client:
            self._llm_client = BedrockClient()
        return await self._llm_client.chat(
            system_prompt=self.system_prompt,
            messages=messages,
            model=model,
        )

    def get_status(self) -> dict:
        """Return agent name, role, and current status."""
        return {"name": self.name, "role": self.role, "status": self.status}

    def log(self, level: str, message: str) -> None:
        """Log with agent name prefix."""
        getattr(self._logger, level.lower(), self._logger.info)(message)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_base_agent.py -v
```

Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/base_agent.py tests/test_base_agent.py
git commit -m "feat: add MatrixAgent abstract base class"
```

---

### Task 13: MatrixOrchestrator

**Files:**
- Create: `orchestration/matrix_orchestrator.py`
- Create: `tests/test_orchestrator.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_orchestrator.py`:
```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orchestration.matrix_orchestrator import MatrixOrchestrator
from orchestration.protocol import Orchestrator, RoutingDecision
from orchestration.registry import AgentRegistry
from shared.models import AgentResult


class TestMatrixOrchestrator:
    def _make_orchestrator(self):
        registry = AgentRegistry()
        # Register a mock Trinity agent
        trinity = MagicMock()
        trinity.name = "Trinity"
        trinity.get_status.return_value = {
            "name": "Trinity",
            "role": "Assistant",
            "status": "IDLE",
        }
        trinity.execute = AsyncMock(
            return_value=AgentResult(
                agent="Trinity", status="success", content="Done."
            )
        )
        registry.register(trinity)
        return MatrixOrchestrator(registry=registry, llm_client=AsyncMock())

    def test_implements_protocol(self):
        orchestrator = self._make_orchestrator()
        assert isinstance(orchestrator, Orchestrator)

    @pytest.mark.asyncio
    async def test_dispatch_calls_agent_execute(self):
        orchestrator = self._make_orchestrator()
        result = await orchestrator.dispatch("Trinity", {"action": "test"})
        assert result.agent == "Trinity"
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_dispatch_unknown_agent_returns_error(self):
        orchestrator = self._make_orchestrator()
        result = await orchestrator.dispatch("Unknown", {"action": "test"})
        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_route_task_keyword_match(self):
        orchestrator = self._make_orchestrator()
        decision = await orchestrator.route_task(
            {"content": "write some code for me"}
        )
        assert isinstance(decision, RoutingDecision)
        assert "Morpheus" in decision.agents

    @pytest.mark.asyncio
    async def test_route_task_fallback_to_trinity(self):
        orchestrator = self._make_orchestrator()
        decision = await orchestrator.route_task(
            {"content": "something completely unrelated xyz"}
        )
        assert "Trinity" in decision.agents

    @pytest.mark.asyncio
    async def test_get_agent_statuses(self):
        orchestrator = self._make_orchestrator()
        statuses = await orchestrator.get_agent_statuses()
        assert "Trinity" in statuses
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_orchestrator.py -v
```

Expected: FAIL

- [ ] **Step 3: Create orchestration/matrix_orchestrator.py**

Create `orchestration/matrix_orchestrator.py`:
```python
from __future__ import annotations

import json
import traceback
from pathlib import Path

import yaml

from orchestration.protocol import RoutingDecision
from orchestration.registry import AgentRegistry
from shared.llm_client import BedrockClient
from shared.logger import get_agent_logger
from shared.models import AgentResult, AgentStatus

# Load routing rules
_RULES_PATH = Path(__file__).parent.parent / "config" / "routing_rules.yml"
_RULES: dict = {}
if _RULES_PATH.exists():
    with open(_RULES_PATH) as f:
        _RULES = yaml.safe_load(f) or {}

# Load Merovingian's prompt
_PROMPTS_PATH = Path(__file__).parent.parent / "config" / "agent_prompts.yml"
_MEROVINGIAN_PROMPT = ""
if _PROMPTS_PATH.exists():
    with open(_PROMPTS_PATH) as f:
        prompts = yaml.safe_load(f) or {}
        _MEROVINGIAN_PROMPT = prompts.get("merovingian", {}).get("prompt", "")


class MatrixOrchestrator:
    """Current orchestration implementation using Merovingian + keyword routing.

    This class implements the Orchestrator protocol and will be replaced
    by CoworkOrchestrator when Claude COWORK is available.
    """

    def __init__(
        self,
        registry: AgentRegistry,
        llm_client: BedrockClient | None = None,
    ):
        self._registry = registry
        self._llm_client = llm_client
        self._logger = get_agent_logger("Merovingian")
        self._keyword_routes = _RULES.get("keyword_routes", {})
        self._fallback = _RULES.get("fallback_agent", "trinity")
        self._default_priority = _RULES.get("default_priority", 5)

    async def route_task(self, task: dict) -> RoutingDecision:
        """Route a task to the appropriate agent(s).

        First tries keyword matching (fast path), then falls back to
        LLM-based routing via the Merovingian prompt.
        """
        content = task.get("content", "").lower()

        # Fast path: keyword matching
        for _route_name, route_config in self._keyword_routes.items():
            keywords = route_config.get("keywords", [])
            if any(kw in content for kw in keywords):
                agent_name = route_config["agent"].capitalize()
                self._logger.info(f"Keyword route -> {agent_name}")
                return RoutingDecision(
                    agents=[agent_name], priority=self._default_priority
                )

        # Slow path: LLM routing via Merovingian
        if self._llm_client and _MEROVINGIAN_PROMPT:
            try:
                response = await self._llm_client.chat(
                    system_prompt=_MEROVINGIAN_PROMPT,
                    messages=[{"role": "user", "content": content}],
                )
                parsed = json.loads(response)
                agents = [a.capitalize() for a in parsed.get("agents", [])]
                if agents:
                    return RoutingDecision(
                        agents=agents,
                        parallel=parsed.get("parallel", False),
                        priority=parsed.get("priority", self._default_priority),
                    )
            except (json.JSONDecodeError, KeyError, Exception) as e:
                self._logger.warning(f"LLM routing failed: {e}, using fallback")

        # Fallback to Trinity
        self._logger.info("Falling back to Trinity")
        return RoutingDecision.fallback()

    async def dispatch(self, agent_name: str, task: dict) -> AgentResult:
        """Dispatch a task to a specific agent."""
        agent = self._registry.get(agent_name)
        if not agent:
            return AgentResult(
                agent=agent_name,
                status="error",
                content="",
                error=f"Agent '{agent_name}' not found in registry",
            )

        try:
            agent.status = "ACTIVE"
            result = await agent.execute(task)
            agent.status = "IDLE"
            return result
        except Exception as e:
            agent.status = "ERROR"
            self._logger.error(f"{agent_name} crashed: {traceback.format_exc()}")
            return AgentResult(
                agent=agent_name,
                status="error",
                content="",
                error=str(e),
            )

    async def broadcast(self, message: dict) -> list[AgentResult]:
        """Send a message to all registered agents."""
        results = []
        for name, agent in self._registry.list_all().items():
            try:
                result = await agent.execute(message)
                results.append(result)
            except Exception as e:
                results.append(
                    AgentResult(agent=name, status="error", content="", error=str(e))
                )
        return results

    async def get_agent_statuses(self) -> dict[str, AgentStatus]:
        """Get status of all registered agents."""
        statuses = {}
        for name, status_dict in self._registry.get_statuses().items():
            statuses[name] = AgentStatus(**status_dict)
        return statuses
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_orchestrator.py -v
```

Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add orchestration/matrix_orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add MatrixOrchestrator with Merovingian routing"
```

---

## Chunk 5: Integrations

### Task 14: Slack Adapter (Console + Slack modes)

**Files:**
- Create: `integrations/slack_adapter.py`
- Create: `config/agent_identities.yml`
- Create: `tests/test_slack_adapter.py`

- [ ] **Step 1: Create config/agent_identities.yml**

Create `config/agent_identities.yml`:
```yaml
# Agent visual identities for Slack and console output
neo:
  display_name: "Neo"
  emoji: ":sunglasses:"
  color: "bold white"
trinity:
  display_name: "Trinity"
  emoji: ":blue_circle:"
  color: "cyan"
morpheus:
  display_name: "Morpheus"
  emoji: ":green_circle:"
  color: "green"
oracle:
  display_name: "The Oracle"
  emoji: ":crystal_ball:"
  color: "yellow"
keymaker:
  display_name: "Keymaker"
  emoji: ":key:"
  color: "magenta"
tank:
  display_name: "Tank"
  emoji: ":wrench:"
  color: "blue"
niobe:
  display_name: "Niobe"
  emoji: ":shield:"
  color: "bright_red"
mouse:
  display_name: "Mouse"
  emoji: ":mouse:"
  color: "bright_green"
smith:
  display_name: "Agent Smith"
  emoji: ":red_circle:"
  color: "red"
architect:
  display_name: "The Architect"
  emoji: ":building_construction:"
  color: "bright_cyan"
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_slack_adapter.py`:
```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
python -m pytest tests/test_slack_adapter.py -v
```

Expected: FAIL

- [ ] **Step 4: Create integrations/slack_adapter.py**

Create `integrations/slack_adapter.py`:
```python
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
            _bot_token = bot_token or settings.slack_bot_token
            _channel_id = channel_id or settings.slack_channel_id
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
            # Retry once
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
            # Use Bolt's built-in async web server (Events API over HTTP)
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
        # Console mode: handled by Neo's input loop

    async def stop(self) -> None:
        """Stop the adapter."""
        _logger.info("SlackAdapter stopped")
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest tests/test_slack_adapter.py -v
```

Expected: all 5 tests PASS

- [ ] **Step 6: Commit**

```bash
git add integrations/slack_adapter.py config/agent_identities.yml tests/test_slack_adapter.py
git commit -m "feat: add SlackAdapter with console dry-run and Slack modes"
```

---

## Chunk 6: Agent Implementations

### Task 15: Worker Agents (Trinity through Architect)

**Files:**
- Create: `agents/trinity.py`
- Create: `agents/morpheus.py`
- Create: `agents/oracle.py`
- Create: `agents/keymaker.py`
- Create: `agents/tank.py`
- Create: `agents/niobe.py`
- Create: `agents/mouse.py`
- Create: `agents/smith.py`
- Create: `agents/architect.py`
- Create: `tests/test_agents.py`

- [ ] **Step 1: Write failing tests for all agents**

Create `tests/test_agents.py`:
```python
from unittest.mock import AsyncMock, patch

import pytest

from agents.trinity import Trinity
from agents.morpheus import Morpheus
from agents.oracle import Oracle
from agents.keymaker import Keymaker
from agents.tank import Tank
from agents.niobe import Niobe
from agents.mouse import Mouse
from agents.smith import Smith
from agents.architect import Architect
from shared.models import AgentResult


AGENT_CLASSES = [
    (Trinity, "Trinity", "Executive Assistant"),
    (Morpheus, "Morpheus", "Code Generation & Execution"),
    (Oracle, "Oracle", "Research & Knowledge Retrieval"),
    (Keymaker, "Keymaker", "API & Integration Management"),
    (Tank, "Tank", "DevOps & Infrastructure"),
    (Niobe, "Niobe", "Security & Access Control"),
    (Mouse, "Mouse", "Data Collection & Processing"),
    (Smith, "Smith", "Testing & Adversarial QA"),
    (Architect, "Architect", "System Design & Planning"),
]


class TestAllAgents:
    @pytest.mark.parametrize("cls,name,role", AGENT_CLASSES)
    def test_agent_instantiation(self, cls, name, role):
        agent = cls()
        assert agent.name == name

    @pytest.mark.parametrize("cls,name,role", AGENT_CLASSES)
    @pytest.mark.asyncio
    async def test_agent_execute_returns_result(self, cls, name, role):
        agent = cls()
        # Mock call_llm so we don't hit real API
        agent.call_llm = AsyncMock(return_value=f"Response from {name}")
        result = await agent.execute({"content": "test task", "action": "test"})
        assert isinstance(result, AgentResult)
        assert result.agent == name
        assert result.status == "success"

    @pytest.mark.parametrize("cls,name,role", AGENT_CLASSES)
    @pytest.mark.asyncio
    async def test_agent_execute_handles_llm_error(self, cls, name, role):
        agent = cls()
        agent.call_llm = AsyncMock(side_effect=Exception("LLM timeout"))
        result = await agent.execute({"content": "test", "action": "test"})
        assert result.status == "error"
        assert result.error is not None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_agents.py -v
```

Expected: FAIL

- [ ] **Step 3: Create agent implementations**

All agents follow the same pattern. Each agent calls `self.call_llm()` with a task-specific user message and returns an `AgentResult`.

Create `agents/trinity.py`:
```python
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
```

Create `agents/morpheus.py`:
```python
from agents.base_agent import MatrixAgent
from shared.models import AgentResult


class Morpheus(MatrixAgent):
    """Morpheus - Code generation and execution agent."""

    def __init__(self, **kwargs):
        super().__init__(
            name="Morpheus", role="Code Generation & Execution", **kwargs
        )

    async def execute(self, task: dict) -> AgentResult:
        self.log("info", f"Received task: {task.get('action', 'unknown')}")
        try:
            content = task.get("content", "")
            prompt = f"The user needs help with coding:\n\n{content}"
            response = await self.call_llm([{"role": "user", "content": prompt}])
            return AgentResult(agent=self.name, status="success", content=response)
        except Exception as e:
            self.log("error", f"Execution failed: {e}")
            return AgentResult(
                agent=self.name, status="error", content="", error=str(e)
            )
```

Create `agents/oracle.py`:
```python
from agents.base_agent import MatrixAgent
from shared.models import AgentResult


class Oracle(MatrixAgent):
    """Oracle - Research and knowledge retrieval via RAG."""

    def __init__(self, **kwargs):
        super().__init__(
            name="Oracle", role="Research & Knowledge Retrieval", **kwargs
        )

    async def execute(self, task: dict) -> AgentResult:
        self.log("info", f"Received task: {task.get('action', 'unknown')}")
        try:
            content = task.get("content", "")
            # TODO: Add ChromaDB retrieval before LLM call
            prompt = f"Research the following and provide a thorough answer:\n\n{content}"
            response = await self.call_llm([{"role": "user", "content": prompt}])
            return AgentResult(agent=self.name, status="success", content=response)
        except Exception as e:
            self.log("error", f"Execution failed: {e}")
            return AgentResult(
                agent=self.name, status="error", content="", error=str(e)
            )
```

Create `agents/keymaker.py`:
```python
from agents.base_agent import MatrixAgent
from shared.models import AgentResult


class Keymaker(MatrixAgent):
    """Keymaker - API and integration management agent."""

    def __init__(self, **kwargs):
        super().__init__(
            name="Keymaker", role="API & Integration Management", **kwargs
        )

    async def execute(self, task: dict) -> AgentResult:
        self.log("info", f"Received task: {task.get('action', 'unknown')}")
        try:
            content = task.get("content", "")
            prompt = f"Help with the following API/integration task:\n\n{content}"
            response = await self.call_llm([{"role": "user", "content": prompt}])
            return AgentResult(agent=self.name, status="success", content=response)
        except Exception as e:
            self.log("error", f"Execution failed: {e}")
            return AgentResult(
                agent=self.name, status="error", content="", error=str(e)
            )
```

Create `agents/tank.py`:
```python
from agents.base_agent import MatrixAgent
from shared.models import AgentResult


class Tank(MatrixAgent):
    """Tank - DevOps and infrastructure agent."""

    def __init__(self, **kwargs):
        super().__init__(name="Tank", role="DevOps & Infrastructure", **kwargs)

    async def execute(self, task: dict) -> AgentResult:
        self.log("info", f"Received task: {task.get('action', 'unknown')}")
        try:
            content = task.get("content", "")
            prompt = f"Help with the following infrastructure task:\n\n{content}"
            response = await self.call_llm([{"role": "user", "content": prompt}])
            return AgentResult(agent=self.name, status="success", content=response)
        except Exception as e:
            self.log("error", f"Execution failed: {e}")
            return AgentResult(
                agent=self.name, status="error", content="", error=str(e)
            )
```

Create `agents/niobe.py`:
```python
from agents.base_agent import MatrixAgent
from shared.models import AgentResult


class Niobe(MatrixAgent):
    """Niobe - Security and access control agent."""

    def __init__(self, **kwargs):
        super().__init__(
            name="Niobe", role="Security & Access Control", **kwargs
        )

    async def execute(self, task: dict) -> AgentResult:
        self.log("info", f"Received task: {task.get('action', 'unknown')}")
        try:
            content = task.get("content", "")
            prompt = f"Review the following for security concerns:\n\n{content}"
            response = await self.call_llm([{"role": "user", "content": prompt}])
            return AgentResult(agent=self.name, status="success", content=response)
        except Exception as e:
            self.log("error", f"Execution failed: {e}")
            return AgentResult(
                agent=self.name, status="error", content="", error=str(e)
            )
```

Create `agents/mouse.py`:
```python
from agents.base_agent import MatrixAgent
from shared.models import AgentResult


class Mouse(MatrixAgent):
    """Mouse - Data collection and processing agent."""

    def __init__(self, **kwargs):
        super().__init__(
            name="Mouse", role="Data Collection & Processing", **kwargs
        )

    async def execute(self, task: dict) -> AgentResult:
        self.log("info", f"Received task: {task.get('action', 'unknown')}")
        try:
            content = task.get("content", "")
            prompt = f"Help with the following data task:\n\n{content}"
            response = await self.call_llm([{"role": "user", "content": prompt}])
            return AgentResult(agent=self.name, status="success", content=response)
        except Exception as e:
            self.log("error", f"Execution failed: {e}")
            return AgentResult(
                agent=self.name, status="error", content="", error=str(e)
            )
```

Create `agents/smith.py`:
```python
from agents.base_agent import MatrixAgent
from shared.models import AgentResult


class Smith(MatrixAgent):
    """Agent Smith - Testing and adversarial QA agent."""

    def __init__(self, **kwargs):
        super().__init__(
            name="Smith", role="Testing & Adversarial QA", **kwargs
        )

    async def execute(self, task: dict) -> AgentResult:
        self.log("info", f"Received task: {task.get('action', 'unknown')}")
        try:
            content = task.get("content", "")
            prompt = f"Analyze the following for bugs, edge cases, and weaknesses:\n\n{content}"
            response = await self.call_llm([{"role": "user", "content": prompt}])
            return AgentResult(agent=self.name, status="success", content=response)
        except Exception as e:
            self.log("error", f"Execution failed: {e}")
            return AgentResult(
                agent=self.name, status="error", content="", error=str(e)
            )
```

Create `agents/architect.py`:
```python
from agents.base_agent import MatrixAgent
from shared.models import AgentResult


class Architect(MatrixAgent):
    """The Architect - System design and planning agent."""

    def __init__(self, **kwargs):
        super().__init__(
            name="Architect", role="System Design & Planning", **kwargs
        )

    async def execute(self, task: dict) -> AgentResult:
        self.log("info", f"Received task: {task.get('action', 'unknown')}")
        try:
            content = task.get("content", "")
            prompt = f"Provide system design guidance for:\n\n{content}"
            response = await self.call_llm([{"role": "user", "content": prompt}])
            return AgentResult(agent=self.name, status="success", content=response)
        except Exception as e:
            self.log("error", f"Execution failed: {e}")
            return AgentResult(
                agent=self.name, status="error", content="", error=str(e)
            )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/test_agents.py -v
```

Expected: all 27 tests PASS (9 agents x 3 tests each)

- [ ] **Step 5: Commit**

```bash
git add agents/trinity.py agents/morpheus.py agents/oracle.py agents/keymaker.py \
       agents/tank.py agents/niobe.py agents/mouse.py agents/smith.py agents/architect.py \
       tests/test_agents.py
git commit -m "feat: add all worker agent implementations"
```

---

## Chunk 7: Neo & Main Loop

### Task 16: Neo (Entry Point & CLI Loop)

**Files:**
- Create: `agents/neo.py`
- Create: `shared/utils.py`

- [ ] **Step 1: Create shared/utils.py**

Create `shared/utils.py`:
```python
# Matrix ASCII banner for startup
MATRIX_BANNER = r"""
  ╔══════════════════════════════════════════════════════╗
  ║                                                      ║
  ║   ████████╗██╗  ██╗███████╗                          ║
  ║   ╚══██╔══╝██║  ██║██╔════╝                          ║
  ║      ██║   ███████║█████╗                             ║
  ║      ██║   ██╔══██║██╔══╝                             ║
  ║      ██║   ██║  ██║███████╗                           ║
  ║      ╚═╝   ╚═╝  ╚═╝╚══════╝                           ║
  ║                                                      ║
  ║   ███╗   ███╗ █████╗ ████████╗██████╗ ██╗██╗  ██╗   ║
  ║   ████╗ ████║██╔══██╗╚══██╔══╝██╔══██╗██║╚██╗██╔╝   ║
  ║   ██╔████╔██║███████║   ██║   ██████╔╝██║ ╚███╔╝    ║
  ║   ██║╚██╔╝██║██╔══██║   ██║   ██╔══██╗██║ ██╔██╗    ║
  ║   ██║ ╚═╝ ██║██║  ██║   ██║   ██║  ██║██║██╔╝ ██╗   ║
  ║   ╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝   ║
  ║                                                      ║
  ║           Agent Team v0.1.0 — Zion Online            ║
  ╚══════════════════════════════════════════════════════╝
"""
```

- [ ] **Step 2: Create agents/neo.py**

Create `agents/neo.py`:
```python
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

# Meta-commands that Neo handles directly
META_COMMANDS = {"/status", "/agents", "/health", "/help", "/quit", "/exit"}


def build_registry(llm_client: BedrockClient) -> AgentRegistry:
    """Create and populate the agent registry."""
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
    """Handle meta-commands. Returns True if the program should exit."""
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
    """Route and execute a user task."""
    task = {"content": content, "action": "user_request"}

    # Route
    decision = await orchestrator.route_task(task)
    agents_str = ", ".join(decision.agents)
    await adapter.post_message("Neo", f"Routing to: {agents_str}", thread_id)

    # Dispatch
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
    """Interactive console input loop."""
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
    """Entry point for the Matrix Agent Team."""
    logger.info("Initializing Neo...")

    llm_client = BedrockClient()
    registry = build_registry(llm_client)
    orchestrator = MatrixOrchestrator(registry=registry, llm_client=llm_client)
    adapter = SlackAdapter()

    if settings.slack_mode == "console":
        await console_loop(orchestrator, adapter)
    else:
        # Slack mode: register message handler and start
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
```

- [ ] **Step 3: Verify the module runs (--help or import check)**

```bash
cd /Users/ericmorin/matrix-agents
python -c "from agents.neo import build_registry, handle_meta_command; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add agents/neo.py shared/utils.py
git commit -m "feat: add Neo orchestration entry point with console and Slack modes"
```

---

## Chunk 8: README & Final Integration

### Task 17: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README.md**

Create `README.md`:
```markdown
# The Matrix Agent Team

```
  ████████╗██╗  ██╗███████╗    ███╗   ███╗ █████╗ ████████╗██████╗ ██╗██╗  ██╗
  ╚══██╔══╝██║  ██║██╔════╝    ████╗ ████║██╔══██╗╚══██╔══╝██╔══██╗██║╚██╗██╔╝
     ██║   ███████║█████╗      ██╔████╔██║███████║   ██║   ██████╔╝██║ ╚███╔╝
     ██║   ██╔══██║██╔══╝      ██║╚██╔╝██║██╔══██║   ██║   ██╔══██╗██║ ██╔██╗
     ██║   ██║  ██║███████╗    ██║ ╚═╝ ██║██║  ██║   ██║   ██║  ██║██║██╔╝ ██╗
     ╚═╝   ╚═╝  ╚═╝╚══════╝    ╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝
```

A multi-agent AI system themed after The Matrix. Eleven agents run inside a Docker environment called **Zion**, coordinated by a pluggable orchestration layer designed for future Claude COWORK migration.

## Agent Roster

| Agent | Role | Description |
|-------|------|-------------|
| **Neo** | Orchestrator | Receives user input, delegates to agents, presents results |
| **Trinity** | Executive Assistant | General tasks, summaries, drafts. Fallback agent |
| **Morpheus** | Coder | Code generation, review, debugging |
| **Oracle** | Research/RAG | Knowledge retrieval via ChromaDB vector store |
| **Keymaker** | APIs/Integrations | External service connections and webhooks |
| **Tank** | DevOps | Infrastructure, monitoring, container health |
| **Niobe** | Security | Vulnerability scanning, access control, code review |
| **Mouse** | Data | Data collection, cleaning, transformation |
| **Smith** | Testing/QA | Adversarial testing, edge cases, bug hunting |
| **Merovingian** | Task Router | Analyzes tasks and routes to appropriate agents |
| **Architect** | System Design | Architecture decisions, schema design, planning |

## Architecture

```mermaid
graph TD
    User[Human - Slack/Console] --> Adapter[SlackAdapter]
    Adapter --> Neo[Neo - Orchestrator]
    Neo --> Orch{Orchestrator Protocol}
    Orch --> MO[MatrixOrchestrator]
    Orch -.-> CO[CoworkOrchestrator - Future]
    MO --> Merov[Merovingian - Router]
    MO --> Bus[Redis Message Bus]
    MO --> Trinity & Morpheus & Oracle & Keymaker & Tank & Niobe & Mouse & Smith & Architect
    Oracle --> Chroma[ChromaDB]
```

## Prerequisites

- **Docker Desktop** installed and running
- **Python 3.11+** (for local development)
- **AWS Bedrock access** via Instacart AI Gateway (or direct Bedrock credentials)

## Quick Start

1. **Clone and configure:**
   ```bash
   cd matrix-agents
   cp docker/.env.example docker/.env
   # Edit docker/.env with your ANTHROPIC_BEDROCK_BASE_URL
   ```

2. **Start Zion:**
   ```bash
   ./scripts/start_zion.sh
   ```

3. **Interact with Neo:**
   The console will start automatically. Type a task or use commands:
   ```
   You> Write a Python function to sort a list
   [Neo]: Routing to: Morpheus
   [Morpheus]: Here's a sorting function...
   ```

## CLI Commands

| Command | Description |
|---------|-------------|
| `/status` | Show status of all agents |
| `/agents` | List all agents with roles |
| `/health` | Run health checks |
| `/help` | Show available commands |
| `/quit` | Exit the Matrix |

## Development

### Running locally (without Docker):
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp docker/.env.example .env
python -m agents.neo
```

### Running tests:
```bash
pytest tests/ -v
```

### Adding a new agent:

1. Create `agents/your_agent.py` inheriting from `MatrixAgent`
2. Implement `async execute(self, task: dict) -> AgentResult`
3. Add prompt to `config/agent_prompts.yml`
4. Add identity to `config/agent_identities.yml`
5. Register in `agents/neo.py:build_registry()`

## Slack Setup

1. Create a Slack App at api.slack.com
2. Add Bot Token Scopes: `chat:write`, `chat:write.customize`, `channels:history`, `channels:read`
3. Install to workspace and copy Bot Token
4. Set `SLACK_MODE=slack`, `SLACK_BOT_TOKEN`, and `SLACK_CHANNEL_ID` in `.env`

## COWORK Migration

The orchestration layer is designed to be swapped for Claude COWORK:

- **Keep:** Agent identities, prompts, Slack adapter, Docker infra, config
- **Replace:** `orchestration/matrix_orchestrator.py` with `CoworkOrchestrator`
- **Swap point:** Set `ORCHESTRATOR_TYPE=cowork` in `.env`
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "feat: add project README with architecture docs"
```

---

### Task 18: Final Integration Test

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/ericmorin/matrix-agents
python -m pytest tests/ -v
```

Expected: all tests pass

- [ ] **Step 2: Verify import chain works**

```bash
python -c "
from agents.neo import build_registry, main
from orchestration.protocol import Orchestrator
from orchestration.matrix_orchestrator import MatrixOrchestrator
from integrations.slack_adapter import SlackAdapter
print('All imports OK')
"
```

Expected: `All imports OK`

- [ ] **Step 3: Final commit with all remaining files**

```bash
git add -A
git commit -m "feat: complete Matrix Agent Team v0.1.0 scaffold"
```
