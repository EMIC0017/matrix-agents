# The Matrix Agent Team

```
  ████████╗██╗  ██╗███████╗    ███╗   ███╗ █████╗ ████████╗██████╗ ██╗██╗  ██╗
  ╚══██╔══╝██║  ██║██╔════╝    ████╗ ████║██╔══██╗╚══██╔══╝██╔══██╗██║╚██╗██╔╝
     ██║   ███████║█████╗      ██╔████╔██║███████║   ██║   ██████╔╝██║ ╚███╔╝
     ██║   ██╔══██║██╔══╝      ██║╚██╔╝██║██╔══██║   ██║   ██╔══██╗██║ ██╔██╗
     ██║   ██║  ██║███████╗    ██║ ╚═╝ ██║██║  ██║   ██║   ██║  ██║██║██╔╝ ██╗
     ╚═╝   ╚═╝  ╚═╝╚══════╝    ╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝
```

A multi-agent AI system themed after The Matrix. Eleven agents run inside a Docker environment called **Zion**, coordinated by a pluggable orchestration layer designed for easy integration with Claude COWORK or any other agentic framework.

## Table of Contents

- [Agent Roster](#agent-roster)
- [Architecture](#architecture)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Console Mode (No Docker)](#console-mode-no-docker)
  - [Full Zion Deployment (Docker)](#full-zion-deployment-docker)
- [Configuration](#configuration)
- [Usage](#usage)
- [Running Tests](#running-tests)
- [Slack Setup](#slack-setup)
- [Integration Guide](#integration-guide)
  - [The Orchestrator Protocol](#the-orchestrator-protocol)
  - [Integrating with Claude COWORK](#integrating-with-claude-cowork)
  - [Integrating with Other Agentic Frameworks](#integrating-with-other-agentic-frameworks)
  - [Using Agents Standalone](#using-agents-standalone)
  - [Swapping the LLM Provider](#swapping-the-llm-provider)
  - [Adding a New Agent](#adding-a-new-agent)
- [Project Structure](#project-structure)

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
| **Merovingian** | Task Router | Analyzes tasks and routes to appropriate agents (internal only) |
| **Architect** | System Design | Architecture decisions, schema design, planning |

## Architecture

```mermaid
graph TD
    User[Human - Slack/Console] --> Adapter[SlackAdapter]
    Adapter --> Neo[Neo - Orchestrator]
    Neo --> Orch{Orchestrator Protocol}
    Orch --> MO[MatrixOrchestrator]
    Orch -.-> CO[CoworkOrchestrator - Future]
    Orch -.-> Custom[YourOrchestrator]
    MO --> Merov[Merovingian - Router]
    MO --> Trinity & Morpheus & Oracle & Keymaker & Tank & Niobe & Mouse & Smith & Architect
    Oracle --> Chroma[ChromaDB]
```

The system is built around a **pluggable Orchestrator Protocol** — a 4-method Python interface that decouples agent execution from the routing/dispatch mechanism. The current implementation (`MatrixOrchestrator`) uses keyword matching and LLM-based routing via the Merovingian. This can be swapped for Claude COWORK, LangGraph, CrewAI, or any framework by implementing the same protocol.

---

## Installation

### Prerequisites

| Requirement | Version | Needed For |
|------------|---------|------------|
| **Python** | 3.12+ | All modes |
| **Docker Desktop** | Latest | Full Zion deployment (Redis, ChromaDB) |
| **LLM Access** | — | Any Claude-compatible API (see [Configuration](#configuration)) |

### Console Mode (No Docker)

The fastest way to get running. Console mode skips Redis and ChromaDB — the orchestrator calls agents directly in-process.

```bash
# 1. Clone the repo
git clone https://github.com/EMIC0017/matrix-agents.git
cd matrix-agents

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate    # macOS/Linux
# .venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your environment
cp docker/.env.example .env
```

Edit `.env` with your LLM provider settings. At minimum you need `ANTHROPIC_BEDROCK_BASE_URL`:

```bash
# .env — minimum for console mode
MATRIX_ENV=zion
SLACK_MODE=console
ANTHROPIC_BEDROCK_BASE_URL=https://your-bedrock-endpoint.example.com
```

See [Configuration](#configuration) for all LLM provider options.

```bash
# 5. Run Neo in console mode
python3 -m agents.neo
```

You should see the Matrix banner and a `You>` prompt. Type any task to send it to an agent, or `/help` for commands.

### Full Zion Deployment (Docker)

For the complete system with Redis message bus and ChromaDB vector store:

```bash
# 1. Clone and configure (same as above)
git clone https://github.com/EMIC0017/matrix-agents.git
cd matrix-agents
cp docker/.env.example .env
# Edit .env with your settings

# 2. Start Zion (builds and starts all containers)
./scripts/start_zion.sh

# 3. Stop Zion
./scripts/stop_zion.sh

# 4. Check health
./scripts/health_check.sh
```

Docker Compose starts three services:

| Service | Image | Purpose | Port |
|---------|-------|---------|------|
| `zion-core` | Custom (Python 3.12-slim) | Agent runtime | 8000 |
| `zion-redis` | redis:7-alpine | Message bus | 6379 |
| `zion-chromadb` | chromadb/chroma:latest | Vector store (Oracle) | 8001 |

---

## Configuration

All settings are loaded from environment variables (via `.env` file). Edit `.env` in the project root:

| Variable | Default | Description |
|----------|---------|-------------|
| `MATRIX_ENV` | `zion` | Environment name |
| `SLACK_MODE` | `console` | `console` for terminal, `slack` for Slack |
| `ANTHROPIC_BEDROCK_BASE_URL` | — | LLM API endpoint (see below) |
| `SLACK_BOT_TOKEN` | — | Slack bot token (Slack mode only) |
| `SLACK_CHANNEL_ID` | — | Target Slack channel (Slack mode only) |
| `REDIS_HOST` | `zion-redis` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |
| `CHROMA_HOST` | `zion-chromadb` | ChromaDB hostname |
| `CHROMA_PORT` | `8001` | ChromaDB port |
| `ORCHESTRATOR_TYPE` | `matrix` | Orchestrator to use (`matrix` or `cowork`) |
| `MAX_AGENT_ITERATIONS` | `50` | Safety limit for agent loops |
| `SANDBOX_MODE` | `true` | Restricts Keymaker and Tank capabilities |

### LLM Provider Setup

The system uses the Anthropic SDK's Bedrock client. Three common configurations:

**Option A: Instacart AI Gateway (proxy to Bedrock)**
```bash
ANTHROPIC_BEDROCK_BASE_URL=https://aigateway.instacart.tools/proxy/claude-code/bedrock/tag/local-claude/user/your.email@instacart.com
```
The gateway handles AWS auth — no credentials needed. Uses model aliases like `claude-sonnet-4`.

**Option B: AWS Bedrock directly**
```bash
ANTHROPIC_BEDROCK_BASE_URL=https://bedrock-runtime.us-east-1.amazonaws.com
```
Requires valid AWS credentials in your environment (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`). Update `shared/llm_client.py` to remove the dummy credentials and let boto3 resolve from environment.

**Option C: Anthropic API directly**
To use the Anthropic API instead of Bedrock, replace `BedrockClient` in `shared/llm_client.py` with the standard `AsyncAnthropic` client:

```python
from anthropic import AsyncAnthropic

class DirectClient:
    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(self):
        self._client = AsyncAnthropic()  # reads ANTHROPIC_API_KEY from env

    async def chat(self, system_prompt, messages, model=None, timeout=30.0):
        response = await self._client.messages.create(
            model=model or self.DEFAULT_MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
            timeout=timeout,
        )
        return response.content[0].text
```

Then set `ANTHROPIC_API_KEY` in your `.env`.

---

## Usage

### CLI Commands

| Command | Description |
|---------|-------------|
| `/status` | Show status of all agents |
| `/agents` | List all agents with roles |
| `/health` | Run health checks |
| `/help` | Show available commands |
| `/quit` | Exit the Matrix |

### Example Session

```
You> Write a Python function to sort a list
[Neo]: Routing to: Morpheus
[Morpheus]: Here's a sorting function...

You> Review this code for security issues: [paste code]
[Neo]: Routing to: Niobe
[Niobe]: I've identified the following concerns...

You> /agents
┌──────────────────────────────┐
│    Matrix Agent Roster       │
├──────────┬──────────┬────────┤
│ Agent    │ Role     │ Status │
│ Trinity  │ Exec Ast │ IDLE   │
│ Morpheus │ Coder    │ IDLE   │
│ ...      │ ...      │ ...    │
└──────────┴──────────┴────────┘
```

---

## Running Tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

58 tests cover all agents, models, orchestration, routing, and the Slack adapter. All tests use mocks — no LLM calls, Redis, or Docker required.

---

## Slack Setup

1. Create a Slack App at [api.slack.com/apps](https://api.slack.com/apps)
2. Add Bot Token Scopes: `chat:write`, `chat:write.customize`, `channels:history`, `channels:read`
3. Install to your workspace and copy the Bot Token
4. Update `.env`:
   ```bash
   SLACK_MODE=slack
   SLACK_BOT_TOKEN=xoxb-your-token
   SLACK_CHANNEL_ID=C0XXXXXXX
   ```
5. Invite the bot to your channel and restart Neo

Each agent posts with its own display name and emoji (configured in `config/agent_identities.yml`), using the `chat:write.customize` scope.

---

## Integration Guide

The system is designed to be extended and integrated with other orchestration frameworks. The key abstraction is the **Orchestrator Protocol**.

### The Orchestrator Protocol

All routing and dispatch flows through a single interface defined in `orchestration/protocol.py`:

```python
@runtime_checkable
class Orchestrator(Protocol):
    async def route_task(self, task: dict) -> RoutingDecision: ...
    async def dispatch(self, agent_name: str, task: dict) -> AgentResult: ...
    async def broadcast(self, message: dict) -> list[AgentResult]: ...
    async def get_agent_statuses(self) -> dict[str, AgentStatus]: ...
```

**`route_task(task)`** — Decides which agent(s) should handle a task. Returns a `RoutingDecision` with agent names, parallel/sequential flag, and priority.

**`dispatch(agent_name, task)`** — Sends a task to a specific agent and returns its result. The agent's `execute()` method is called.

**`broadcast(message)`** — Sends a message to all agents (used for system queries like `/status`).

**`get_agent_statuses()`** — Returns the current status of all registered agents.

**Data types:**

```python
@dataclass
class RoutingDecision:
    agents: list[str]       # Agent names to handle the task
    parallel: bool = False  # Execute in parallel or sequentially
    priority: int = 5       # 1 (highest) to 10 (lowest)

class AgentResult(BaseModel):
    agent: str              # Agent name
    status: str             # "success" | "error" | "partial"
    content: str            # Response text
    data: dict = {}         # Structured data (optional)
    error: str | None       # Error message if status == "error"
```

### Integrating with Claude COWORK

When COWORK becomes available, create a `CoworkOrchestrator` that implements the same protocol:

```python
# orchestration/cowork_orchestrator.py
from cowork import CoworkSDK  # hypothetical import

from orchestration.protocol import Orchestrator, RoutingDecision
from orchestration.registry import AgentRegistry
from shared.models import AgentResult, AgentStatus


class CoworkOrchestrator:
    """COWORK-based orchestration — replaces MatrixOrchestrator."""

    def __init__(self, registry: AgentRegistry, cowork_config: dict):
        self._registry = registry
        self._sdk = CoworkSDK(**cowork_config)

    async def route_task(self, task: dict) -> RoutingDecision:
        # Let COWORK decide which agent handles the task
        result = await self._sdk.route(task["content"])
        return RoutingDecision(
            agents=result.agent_names,
            parallel=result.parallel,
        )

    async def dispatch(self, agent_name: str, task: dict) -> AgentResult:
        agent = self._registry.get(agent_name)
        if not agent:
            return AgentResult(agent=agent_name, status="error",
                             content="", error=f"Agent '{agent_name}' not found")
        # COWORK may handle execution directly, or you can still call agent.execute()
        return await agent.execute(task)

    async def broadcast(self, message: dict) -> list[AgentResult]:
        results = []
        for name, agent in self._registry.list_all().items():
            results.append(await agent.execute(message))
        return results

    async def get_agent_statuses(self) -> dict[str, AgentStatus]:
        statuses = {}
        for name, info in self._registry.get_statuses().items():
            statuses[name] = AgentStatus(**info)
        return statuses
```

Then wire it up in `agents/neo.py`:

```python
# In neo.py main(), swap based on ORCHESTRATOR_TYPE:
if settings.orchestrator_type == "cowork":
    from orchestration.cowork_orchestrator import CoworkOrchestrator
    orchestrator = CoworkOrchestrator(registry=registry, cowork_config={...})
else:
    orchestrator = MatrixOrchestrator(registry=registry, llm_client=llm_client)
```

**What stays unchanged:** All 9 worker agents, their prompts, SlackAdapter, Docker infrastructure, config files, tests.

**What gets replaced:** Only the orchestrator implementation. The Merovingian routing logic is fully contained in `MatrixOrchestrator` and can be retired.

### Integrating with Other Agentic Frameworks

The same pattern works for LangGraph, CrewAI, AutoGen, or any multi-agent framework:

**LangGraph example:**
```python
class LangGraphOrchestrator:
    def __init__(self, registry: AgentRegistry):
        self._registry = registry
        self._graph = self._build_graph()

    def _build_graph(self):
        # Build your LangGraph state graph here
        # Map graph nodes to Matrix agents via self._registry
        ...

    async def route_task(self, task: dict) -> RoutingDecision:
        # Use the graph to determine routing
        result = await self._graph.ainvoke(task)
        return RoutingDecision(agents=result["target_agents"])

    async def dispatch(self, agent_name: str, task: dict) -> AgentResult:
        agent = self._registry.get(agent_name)
        return await agent.execute(task)

    # ... implement broadcast() and get_agent_statuses()
```

**CrewAI example:**
```python
class CrewOrchestrator:
    def __init__(self, registry: AgentRegistry):
        self._registry = registry
        # Map Matrix agents to CrewAI Agent objects

    async def route_task(self, task: dict) -> RoutingDecision:
        # Use CrewAI's task assignment
        ...

    async def dispatch(self, agent_name: str, task: dict) -> AgentResult:
        agent = self._registry.get(agent_name)
        return await agent.execute(task)
```

**Key integration points:**

1. **Orchestrator** (`orchestration/protocol.py`) — Implement the 4-method protocol
2. **Agent Registry** (`orchestration/registry.py`) — Provides `get(name)`, `list_all()`, `get_statuses()`
3. **Agent base class** (`agents/base_agent.py`) — All agents inherit `MatrixAgent` and implement `execute(task) -> AgentResult`
4. **LLM Client** (`shared/llm_client.py`) — Shared `BedrockClient` instance, replaceable

### Using Agents Standalone

You can use individual agents without the orchestration layer:

```python
import asyncio
from shared.llm_client import BedrockClient
from agents.morpheus import Morpheus

async def main():
    client = BedrockClient()
    morpheus = Morpheus(llm_client=client)

    result = await morpheus.execute({
        "content": "Write a binary search in Python",
        "action": "user_request",
    })

    print(result.content)  # The generated code
    print(result.status)   # "success", "error", or "partial"

asyncio.run(main())
```

Every agent accepts the same task format (`{"content": str, "action": str}`) and returns an `AgentResult`.

### Swapping the LLM Provider

The LLM client is isolated in `shared/llm_client.py`. All agents use it via `self.call_llm(messages)`. To swap providers:

1. Edit `shared/llm_client.py` — change the client class and model name
2. Keep the same interface: `async chat(system_prompt, messages, model, timeout) -> str`
3. No agent code changes needed

The `BedrockClient.chat()` signature is the contract:

```python
async def chat(
    self,
    system_prompt: str,          # Agent's system prompt from YAML
    messages: list[dict],        # [{"role": "user", "content": "..."}]
    model: str | None = None,    # Override default model
    timeout: float = 30.0,
) -> str:                        # Returns the response text
```

### Adding a New Agent

1. Create `agents/your_agent.py`:
   ```python
   from agents.base_agent import MatrixAgent
   from shared.models import AgentResult

   class YourAgent(MatrixAgent):
       def __init__(self, llm_client=None):
           super().__init__(name="YourAgent", role="Your Role", llm_client=llm_client)

       async def execute(self, task: dict) -> AgentResult:
           self.status = "ACTIVE"
           self.log("info", f"Received task: {task.get('action')}")
           messages = [{"role": "user", "content": task.get("content", "")}]
           response = await self.call_llm(messages)
           self.status = "IDLE"
           return AgentResult(agent=self.name, status="success", content=response)
   ```

2. Add the system prompt to `config/agent_prompts.yml`:
   ```yaml
   youragent:
     name: YourAgent
     role: Your Role
     prompt: |
       You are YourAgent, a specialist in...
   ```

3. Add identity to `config/agent_identities.yml`:
   ```yaml
   youragent:
     display_name: YourAgent
     emoji: ":your_emoji:"
     color: magenta
   ```

4. Add keywords to `config/routing_rules.yml` (optional):
   ```yaml
   keyword_routes:
     your_domain:
       keywords: ["your", "keywords"]
       agent: youragent
   ```

5. Register in `agents/neo.py`:
   ```python
   from agents.your_agent import YourAgent

   # In build_registry():
   agents = [
       # ... existing agents
       YourAgent(llm_client=llm_client),
   ]
   ```

---

## Project Structure

```
matrix-agents/
├── agents/                    # Agent implementations
│   ├── base_agent.py          # MatrixAgent abstract base class
│   ├── neo.py                 # Entry point, console loop, Slack mode
│   ├── trinity.py             # Executive Assistant (fallback)
│   ├── morpheus.py            # Code Generation
│   ├── oracle.py              # Research / RAG
│   ├── keymaker.py            # API & Integrations
│   ├── tank.py                # DevOps / Infrastructure
│   ├── niobe.py               # Security
│   ├── mouse.py               # Data Processing
│   ├── smith.py               # Testing / QA
│   └── architect.py           # System Design
├── orchestration/             # Pluggable orchestration layer
│   ├── protocol.py            # Orchestrator Protocol (the integration seam)
│   ├── matrix_orchestrator.py # Current impl: Merovingian + keyword routing
│   └── registry.py            # Agent name → instance lookup
├── integrations/
│   └── slack_adapter.py       # Slack bot + console dry-run mode
├── config/
│   ├── settings.py            # Pydantic Settings (loads from .env)
│   ├── agent_prompts.yml      # System prompts per agent
│   ├── agent_identities.yml   # Display names, emojis, colors
│   └── routing_rules.yml      # Keyword → agent routing config
├── shared/
│   ├── llm_client.py          # Bedrock/Anthropic API wrapper
│   ├── message_bus.py         # Redis pub/sub (Docker mode)
│   ├── models.py              # AgentResult, AgentMessage, AgentStatus
│   ├── logger.py              # Color-coded per-agent logging (Rich)
│   └── utils.py               # Matrix banner ASCII art
├── docker/
│   ├── Dockerfile             # Python 3.12-slim container
│   ├── docker-compose.yml     # zion-core + redis + chromadb
│   └── .env.example           # Environment variable template
├── scripts/
│   ├── start_zion.sh          # Boot Zion with Matrix banner
│   ├── stop_zion.sh           # Graceful shutdown
│   └── health_check.sh        # Service health checks
├── tests/                     # 58 tests (mocked, no external deps)
├── data/                      # Mouse's data landing zone + vector store
├── logs/                      # Rotating log files
├── requirements.txt
├── pyproject.toml
└── .gitignore
```
