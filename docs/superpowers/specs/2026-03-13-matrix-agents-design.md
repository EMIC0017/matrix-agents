# Matrix Agent Team — Design Specification

**Date:** 2026-03-13
**Status:** Approved
**Author:** Eric Morin + Claude

## 1. Overview

A multi-agent AI system themed after The Matrix. Eleven agents run inside a Docker environment called Zion, coordinated by a pluggable orchestration layer designed to be replaced by Claude COWORK when available. Human interaction happens through Slack (with a console dry-run mode for development).

### Goals

- Working prototype with real agent execution via AWS Bedrock (Instacart AI Gateway)
- Clean orchestration seam so COWORK can replace the custom routing/dispatch layer
- Slack-based human interface with per-agent visual identity
- Docker-first infrastructure with Redis message bus and ChromaDB vector store

### Non-Goals

- Production-grade security hardening (prototype phase)
- Multi-provider LLM support (Bedrock only)
- Web UI or REST API (Slack is the interface)

## 2. Architecture

### 2.1 High-Level Flow

```
Human posts in Slack (or types in console)
    |
    v
SlackAdapter (single Slack app, per-agent identity overrides)
    |
    v
Neo (receives input, delegates to orchestrator)
    |
    v
Orchestrator Protocol  <-- the COWORK seam
    |
    +-- TODAY: MatrixOrchestrator
    |     +-- Merovingian (LLM-based routing)
    |     +-- Redis MessageBus (dispatch)
    |
    +-- FUTURE: CoworkOrchestrator
    |     +-- COWORK SDK
    |
    v
Agent.execute(task)  <-- agents are the same either way
    |
    v
Results flow back through Neo -> SlackAdapter -> Slack channel
```

### 2.2 Orchestration Protocol (COWORK Seam)

The critical abstraction. Neo talks to an `Orchestrator` protocol, never directly to agents or the message bus.

```python
class Orchestrator(Protocol):
    async def route_task(self, task: dict) -> RoutingDecision
    async def dispatch(self, agent_name: str, task: dict) -> dict
    async def broadcast(self, message: dict) -> list[dict]
    async def get_agent_statuses(self) -> dict[str, AgentStatus]
```

- `RoutingDecision`: dataclass with target agent(s), priority, parallel vs sequential execution
- `MatrixOrchestrator`: current implementation using Merovingian + Redis
- `CoworkOrchestrator`: future implementation using COWORK SDK
- Swap point: `ORCHESTRATOR_TYPE` env var in `settings.py`

Note: `broadcast()` is used by Neo for system-wide announcements (e.g., `/status` queries all agents, shutdown notifications). It is not used for task routing.

### 2.4 COWORK Configuration (Future)

When COWORK SDK becomes available, a `CoworkOrchestrator` will implement the same protocol. COWORK-specific environment variables (SDK endpoint, auth tokens, agent mapping) will be added to `.env.example` at that time. The existing agent prompts, identities, and infrastructure will carry over unchanged.

### 2.3 What Stays vs. What Gets Replaced at COWORK Migration

**Stays:**
- Agent identities, system prompts, and Slack presence
- Docker infrastructure (Zion, Redis, ChromaDB)
- SlackAdapter and integrations layer
- Config, logging, shell scripts

**Gets replaced:**
- `orchestration/matrix_orchestrator.py` -> `CoworkOrchestrator`
- `shared/llm_client.py` -> COWORK's LLM handling
- Possibly `shared/message_bus.py` -> COWORK's agent communication

## 3. Project Structure

```
matrix-agents/
+-- docker/
|   +-- Dockerfile              # Python 3.12-slim, MATRIX_ENV=zion
|   +-- docker-compose.yml      # zion-core, zion-redis, zion-chromadb
|   +-- .env.example            # Bedrock gateway, Redis, Chroma, Slack config
+-- agents/
|   +-- __init__.py
|   +-- base_agent.py           # MatrixAgent abstract base class
|   +-- neo.py                  # Entry point, delegates to Orchestrator
|   +-- trinity.py              # Executive Assistant
|   +-- morpheus.py             # Code Generation
|   +-- oracle.py               # Research / RAG
|   +-- keymaker.py             # API & Integrations
|   +-- tank.py                 # DevOps / Infrastructure
|   +-- niobe.py                # Security
|   +-- mouse.py                # Data Collection & Processing
|   +-- smith.py                # Testing / Adversarial QA
|   +-- architect.py            # System Design & Planning
+-- orchestration/
|   +-- __init__.py
|   +-- protocol.py             # Orchestrator Protocol (the COWORK seam)
|   +-- matrix_orchestrator.py  # Current impl: Merovingian + Redis
|   +-- registry.py             # Agent registry (name -> instance lookup)
+-- integrations/
|   +-- __init__.py
|   +-- slack_adapter.py        # Slack bot (or console dry-run)
+-- config/
|   +-- settings.py             # Central config loader (Pydantic Settings)
|   +-- agent_prompts.yml       # System prompts per agent
|   +-- routing_rules.yml       # Merovingian's routing config
+-- shared/
|   +-- __init__.py
|   +-- message_bus.py          # Redis pub/sub inter-agent comms
|   +-- llm_client.py           # Bedrock gateway client wrapper
|   +-- logger.py               # Color-coded "OperatorLog"
|   +-- utils.py
+-- data/
|   +-- raw/                    # Mouse's raw data landing zone
|   +-- processed/
|   +-- vector_store/           # ChromaDB persistence
+-- tests/
|   +-- __init__.py
|   +-- test_agents.py
|   +-- test_message_bus.py
|   +-- test_orchestrator.py
|   +-- test_slack_adapter.py
|   +-- test_llm_client.py
+-- logs/
|   +-- .gitkeep
+-- scripts/
|   +-- start_zion.sh           # Matrix ASCII banner, Docker boot
|   +-- stop_zion.sh            # Graceful shutdown
|   +-- health_check.sh         # Service health checks
+-- requirements.txt
+-- pyproject.toml
+-- README.md
+-- .gitignore
```

## 4. Components

### 4.1 Base Agent (`agents/base_agent.py`)

Abstract base class `MatrixAgent`:

- **Properties:** `name`, `role`, `system_prompt` (loaded from YAML), `status` (IDLE/ACTIVE/WAITING/ERROR)
- **Abstract method:** `async execute(task: dict) -> dict`
- **Convenience methods:** `log()`, `get_status()`, `call_llm(messages)` (delegates to BedrockClient)
- Agents do not know about the orchestrator, Slack, or message bus — they cannot communicate directly with each other. All inter-agent coordination flows through the orchestrator.
- Uses Python `abc` module; Pydantic for message validation

**Agent result schema** (Pydantic model `AgentResult`):
```python
class AgentResult(BaseModel):
    agent: str          # Agent name
    status: str         # "success" | "error" | "partial"
    content: str        # Main response text
    data: dict = {}     # Structured data (optional, agent-specific)
    error: str | None   # Error message if status == "error"
```

**Neo execution flow:**
1. Receive input from SlackAdapter
2. Check for meta-commands (`/status`, `/agents`, `/health`, `/help`) — handle directly
3. Delegate to `orchestrator.route_task()` to get `RoutingDecision`
4. Call `orchestrator.dispatch()` for each target agent (parallel or sequential per routing decision)
5. If dispatch returns error, log and report to user (do not retry automatically)
6. Format combined results and return via SlackAdapter

### 4.2 Agent Roster

#### Tier 1 — Core Orchestration

| Agent | Role | Prototype Behavior |
|-------|------|--------------------|
| **Neo** | Orchestrator / Entry Point | Receives input via SlackAdapter, delegates to orchestrator, presents results. Handles meta-commands (`/status`, `/agents`, `/health`, `/help`). |
| **Merovingian** | Task Router | Lives inside `MatrixOrchestrator`. Uses LLM to analyze tasks and return routing decisions. Configured via `routing_rules.yml`. Not in agent registry. Internal only — no Slack presence. |

#### Tier 2 — Primary Workers

| Agent | Role | Prototype Behavior |
|-------|------|--------------------|
| **Trinity** | Executive Assistant | General-purpose assistant. Summarizes, drafts, handles unspecialized tasks. Fallback agent. |
| **Morpheus** | Code Generation | Receives coding tasks, uses code-focused prompts, returns code + explanation. |
| **Oracle** | Research / RAG | Queries ChromaDB vector store, retrieves context, answers grounded questions. |

#### Tier 3 — Specialists

| Agent | Role | Prototype Behavior |
|-------|------|--------------------|
| **Keymaker** | API & Integrations | Makes HTTP requests via httpx, manages external service calls. |
| **Tank** | DevOps / Infrastructure | Reports container health, checks logs, monitors resources via Docker commands. |
| **Niobe** | Security | LLM-based security review of code snippets and configs. |
| **Mouse** | Data Processing | Basic data ingestion, cleaning, transformation (CSV/JSON). |
| **Smith** | Testing / QA | LLM generates test suggestions, finds edge cases, adversarial testing. |
| **Architect** | System Design | LLM-based architecture docs, schema proposals, design reviews. |

#### Agent Execute Pattern

All agents follow the same pattern:
1. Log receipt of task
2. Build messages array with system prompt + task context
3. Call `self.call_llm(messages)`
4. Parse/format the response
5. Return structured result dict

Differentiation comes from system prompts in `agent_prompts.yml`, not complex code. This makes COWORK migration easy — prompts carry over, `execute()` wrappers get replaced.

### 4.3 LLM Client (`shared/llm_client.py`)

`BedrockClient` — thin wrapper around the Anthropic SDK configured for Bedrock:

- Reads `ANTHROPIC_BEDROCK_BASE_URL` from environment (Instacart AI Gateway proxy — handles Bedrock auth internally, no AWS credentials needed)
- Single method: `async chat(system_prompt, messages, model) -> str`
- `messages` follows Anthropic Messages API format: `[{"role": "user", "content": "..."}]`
- All agents share one client instance
- Retired when COWORK brings its own LLM handling

### 4.4 Message Bus (`shared/message_bus.py`)

`MatrixMessageBus` — Redis-based inter-agent communication (used only by `MatrixOrchestrator`, not by agents directly):

- **Implementation:** Uses Redis Lists for task queues (LPUSH/BRPOP) with pub/sub for notifications. This avoids the fire-and-forget limitation of pure pub/sub and supports reliable request/response via `correlation_id`.
- **Message format** (Pydantic model `AgentMessage`):
  - `id`: UUID
  - `timestamp`: datetime
  - `source`: str (agent name)
  - `target`: str (agent name)
  - `action`: str (e.g., `"execute"`, `"status_check"`, `"shutdown"`)
  - `payload`: dict (task-specific data)
  - `priority`: int (1-10, where 1 is highest; used for queue ordering)
  - `correlation_id`: UUID | None (links request/response pairs; used for debugging and tracing)
- **Methods:** `publish()`, `subscribe()`, `request_response()` (async with timeout), `get_pending_messages()`
- May be retired or repurposed when COWORK replaces the orchestrator

### 4.5 Slack Adapter (`integrations/slack_adapter.py`)

Single Slack app with per-agent visual identity:

- **Two modes** via `SLACK_MODE` env var:
  - `slack`: Slack Bolt SDK, listens in designated channel, posts with per-agent `username` and `icon_emoji` overrides (requires `chat:write.customize` scope)
  - `console`: Reads from stdin, prints to terminal with Rich color-coding per agent
- **Agent identity map** in config: `{agent_name: {display_name, emoji, color}}`
- **Threading:** Responses threaded under original message (Slack) or indented with `  -> [AgentName]:` prefix (console)
- Thin I/O layer — does not make decisions, just translates between human channels and Neo
- See README for Slack app configuration steps (required scopes: `chat:write`, `chat:write.customize`, `channels:history`, `channels:read`)

### 4.6 Orchestration Registry (`orchestration/registry.py`)

`AgentRegistry` — name-to-instance lookup:

- Registers all agents at startup
- Provides `get(name)`, `list_all()`, `get_statuses()`
- Used by the orchestrator to resolve routing decisions to agent instances

## 5. Infrastructure

### 5.1 Docker Services

| Service | Image | Purpose | Port |
|---------|-------|---------|------|
| `zion-core` | Custom (Python 3.12-slim) | Agent runtime | 8000 |
| `zion-redis` | redis:7-alpine | Message bus / task queue | 6379 |
| `zion-chromadb` | chromadb/chroma:latest | Oracle's vector store | 8001 |

All on `matrix-network` bridge. `zion-core` has 2GB memory limit, 1.5 CPU limit (initial allocation; increase if profiling shows pressure).

### 5.2 ChromaDB Setup

- **Collection:** `oracle_knowledge` — Oracle's primary knowledge base
- **Embedding model:** Default ChromaDB embedding (all-MiniLM-L6-v2)
- **Metadata fields:** `source` (origin file/URL), `agent` (which agent ingested), `timestamp`
- **Ingestion:** Mouse processes raw data in `data/raw/`, writes to `data/processed/`, and upserts to ChromaDB. Oracle queries at execution time.
- Collection is created on first startup if it doesn't exist.

### 5.3 Shell Scripts

- `start_zion.sh`: Matrix ASCII banner, Docker check, .env check, `docker compose up --build -d`, health check, status summary
- `stop_zion.sh`: Graceful `docker compose down`
- `health_check.sh`: Check each container, Redis ping, ChromaDB health endpoint, status table with green/red indicators

## 6. Configuration

### 6.1 Settings (`config/settings.py`)

Pydantic `Settings` model loaded from environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MATRIX_ENV` | `zion` | Environment name |
| `SLACK_MODE` | `console` | `slack` or `console` |
| `ANTHROPIC_BEDROCK_BASE_URL` | — | Instacart AI Gateway URL |
| `SLACK_BOT_TOKEN` | — | Slack bot token (required for slack mode) |
| `SLACK_CHANNEL_ID` | — | Target Slack channel |
| `REDIS_HOST` | `zion-redis` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |
| `CHROMA_HOST` | `zion-chromadb` | ChromaDB hostname |
| `CHROMA_PORT` | `8001` | ChromaDB port (mapped from container 8000 to host 8001) |
| `ORCHESTRATOR_TYPE` | `matrix` | `matrix` or `cowork` |
| `LOG_LEVEL` | `INFO` | Logging level |
| `MAX_AGENT_ITERATIONS` | `50` | Safety limit for future multi-turn agent loops; unused in v1 |
| `SANDBOX_MODE` | `true` | Restricts Keymaker (no DELETE/PUT) and Tank (read-only Docker commands) |

### 6.2 Agent Prompts (`config/agent_prompts.yml`)

YAML file mapping agent name to `{name, role, prompt}`. Each prompt defines the agent's personality, capabilities, and constraints. See Section 4.2 for roles.

### 6.3 Routing Rules (`config/routing_rules.yml`)

Configuration for the Merovingian's routing logic:
- Keyword-to-agent mappings (fast path)
- Fallback: LLM-based routing analysis
- Priority rules and parallel execution hints

## 7. Dependencies

```
anthropic[bedrock]
boto3
pydantic>=2.5.0
pyyaml>=6.0
python-dotenv>=1.0.0
redis>=5.0.0
chromadb>=0.4.0
rich>=13.0.0
slack-bolt>=1.18.0
httpx>=0.27.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

## 8. Testing Strategy

| Test File | Scope |
|-----------|-------|
| `test_agents.py` | Each agent instantiates, receives task, returns structured result |
| `test_message_bus.py` | Publish/subscribe, request/response with timeout |
| `test_orchestrator.py` | Routing returns valid agents, dispatch calls correct agent |
| `test_slack_adapter.py` | Console mode output, agent identity overrides |
| `test_llm_client.py` | Bedrock client request formatting (mocked, no real API calls) |

- Unit tests with mocked LLM and Redis
- `pytest-asyncio` for async execution
- Tests run locally and in Docker
- Lightweight coverage appropriate for prototype phase

## 9. Error Handling

Prototype-appropriate error handling — log, report, don't crash:

| Scenario | Behavior |
|----------|----------|
| Bedrock gateway timeout | `BedrockClient` raises after 30s timeout. Agent returns `AgentResult(status="error")`. Neo reports the error to the user via SlackAdapter. |
| Agent crashes mid-execution | Orchestrator catches exception, logs traceback, returns error result. Agent status set to ERROR. Other agents unaffected. |
| Redis connection lost | `MatrixOrchestrator` logs error and raises. Neo reports "internal communication failure" to user. System requires restart to reconnect. |
| Routing fails (no agent match) | Merovingian defaults to Trinity (the fallback agent) with a note that routing was uncertain. |
| Slack API error | SlackAdapter logs error. In Slack mode, retries once. In console mode, prints to stderr. |

No automatic retries for LLM calls (avoid runaway costs). No circuit breakers (prototype scope).

## 10. Execution Order

1. Project scaffolding (directory structure)
2. Configuration files (requirements, pyproject, gitignore)
3. Docker setup (Zion — Dockerfile, compose, env, scripts)
4. Base framework (base_agent, llm_client, message_bus, logger)
5. Orchestration layer (protocol, matrix_orchestrator, registry)
6. Integrations (slack_adapter with console mode)
7. Agent prompts and implementations
8. Neo's main loop
9. Tests
10. README
