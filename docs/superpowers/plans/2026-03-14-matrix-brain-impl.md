# Matrix Brain Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a shared persistent memory system ("Matrix Brain") for all Matrix agents — Slack capture, semantic search, and MCP server for external AI tools.

**Architecture:** ChromaDB stores thoughts with built-in embeddings (all-MiniLM-L6-v2). A `MatrixBrain` module wraps capture/search/browse/stats. Metadata extraction via existing BedrockClient classifies thoughts (category, people, action items). A Python MCP server exposes the brain to external AI clients (Claude Desktop, Cursor, etc.). Slack `#capture` channel and console `/capture` command feed the brain.

**Tech Stack:** ChromaDB 1.5.5 (already installed), MCP Python SDK (mcp>=1.0.0), existing BedrockClient, pytest + pytest-asyncio

---

## Context

The Matrix Agent Team currently has no shared memory — each agent call is stateless. Inspired by the "Open Brain" concept (Slack capture → vector embedding → semantic search → MCP server), Matrix Brain gives all agents persistent, searchable memory. Unlike Open Brain (Supabase + Edge Functions), this runs entirely within Zion using ChromaDB (already in the Docker stack) and Python.

**Console mode works without Docker** — ChromaDB uses persistent local storage (`data/brain/`) or ephemeral in-memory mode for tests.

---

## File Structure

### New Files
| File | Purpose |
|------|---------|
| `shared/brain.py` | Core `MatrixBrain` class — ChromaDB wrapper |
| `shared/brain_extractor.py` | `BrainExtractor` — LLM metadata extraction |
| `mcp_server/__init__.py` | MCP server package |
| `mcp_server/brain_server.py` | MCP server exposing 4 brain tools |
| `tests/test_brain.py` | MatrixBrain tests (ephemeral ChromaDB) |
| `tests/test_brain_extractor.py` | BrainExtractor tests (mocked LLM) |
| `tests/test_brain_mcp.py` | MCP tool handler tests |
| `tests/conftest.py` | Shared fixtures (ephemeral brain) |

### Modified Files
| File | Change |
|------|--------|
| `config/settings.py` | Add brain_mode, brain_data_path, mcp_port, mcp_access_key, slack_capture_channel_id |
| `agents/base_agent.py` | Add optional `brain` param to `MatrixAgent.__init__` |
| `agents/neo.py` | Wire brain, add `/capture` + `/brain` commands, refactor command dispatch |
| `agents/oracle.py` | Search brain for context before LLM call (RAG) |
| `integrations/slack_adapter.py` | Add capture channel listener + `on_capture()` callback |
| `requirements.txt` | Add `mcp>=1.0.0` |
| `.env` | Add brain/MCP settings |
| `docker/.env.example` | Add brain/MCP settings template |

---

## Chunk 1: Core Brain Module

### Task 1: MatrixBrain — ChromaDB Wrapper

**Files:**
- Create: `shared/brain.py`
- Create: `tests/test_brain.py`
- Create: `tests/conftest.py`

**Key patterns:**
- ChromaDB client is sync — wrap with `asyncio.get_event_loop().run_in_executor()` (same pattern as `neo.py:122`)
- Three modes: `ephemeral` (in-memory, tests), `persistent` (local files, console), `docker` (HttpClient)
- Collection: `matrix_brain` (separate from Oracle's future `oracle_knowledge`)
- ChromaDB built-in embeddings — no external API call needed

- [ ] **Step 1: Create conftest.py with shared fixtures**

```python
# tests/conftest.py
import pytest
from shared.brain import MatrixBrain


@pytest.fixture
def brain():
    """Fresh ephemeral brain for each test."""
    return MatrixBrain(mode="ephemeral")
```

- [ ] **Step 2: Write failing tests**

```python
# tests/test_brain.py
import pytest
from shared.brain import MatrixBrain


class TestMatrixBrain:
    def test_init_ephemeral(self):
        brain = MatrixBrain(mode="ephemeral")
        assert brain._collection is not None

    def test_init_persistent(self, tmp_path):
        brain = MatrixBrain(mode="persistent", data_path=str(tmp_path / "brain"))
        assert brain._collection is not None

    @pytest.mark.asyncio
    async def test_capture_returns_id(self, brain):
        thought_id = await brain.capture("Test thought", source="test")
        assert isinstance(thought_id, str)
        assert len(thought_id) > 0

    @pytest.mark.asyncio
    async def test_capture_with_metadata(self, brain):
        metadata = {"category": "idea", "people": ["Alice"]}
        thought_id = await brain.capture("Great idea", source="test", metadata=metadata)
        results = await brain.search("great idea", n_results=1)
        assert len(results) == 1
        assert results[0]["metadata"]["category"] == "idea"

    @pytest.mark.asyncio
    async def test_search_returns_relevant_results(self, brain):
        await brain.capture("Python is a great programming language", source="test")
        await brain.capture("The weather is sunny today", source="test")
        results = await brain.search("coding in Python")
        assert len(results) >= 1
        assert "Python" in results[0]["content"]

    @pytest.mark.asyncio
    async def test_search_empty_brain(self, brain):
        results = await brain.search("anything")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_with_category_filter(self, brain):
        await brain.capture("Idea A", source="test", metadata={"category": "idea"})
        await brain.capture("Task B", source="test", metadata={"category": "task"})
        results = await brain.search("anything", where={"category": "idea"})
        assert all(r["metadata"]["category"] == "idea" for r in results)

    @pytest.mark.asyncio
    async def test_search_respects_n_results(self, brain):
        for i in range(5):
            await brain.capture(f"Thought number {i}", source="test")
        results = await brain.search("thought", n_results=2)
        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_browse_returns_recent(self, brain):
        await brain.capture("First thought", source="test")
        await brain.capture("Second thought", source="test")
        results = await brain.browse(limit=10)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_browse_respects_limit(self, brain):
        for i in range(5):
            await brain.capture(f"Thought {i}", source="test")
        results = await brain.browse(limit=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_stats_returns_counts(self, brain):
        await brain.capture("An idea", source="slack", metadata={"category": "idea"})
        await brain.capture("A task", source="console", metadata={"category": "task"})
        stats = await brain.stats()
        assert stats["count"] == 2
        assert "idea" in stats["categories"]
        assert "task" in stats["categories"]

    @pytest.mark.asyncio
    async def test_delete_removes_thought(self, brain):
        thought_id = await brain.capture("Delete me", source="test")
        deleted = await brain.delete(thought_id)
        assert deleted is True
        stats = await brain.stats()
        assert stats["count"] == 0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_brain.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'shared.brain'`

- [ ] **Step 4: Implement MatrixBrain**

```python
# shared/brain.py
"""Matrix Brain — shared persistent memory backed by ChromaDB."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from functools import partial

import chromadb


class MatrixBrain:
    """ChromaDB-backed shared memory for the Matrix Agent Team."""

    COLLECTION_NAME = "matrix_brain"

    def __init__(
        self,
        mode: str = "persistent",
        host: str | None = None,
        port: int | None = None,
        data_path: str = "data/brain",
    ):
        self.mode = mode
        if mode == "ephemeral":
            self._client = chromadb.EphemeralClient()
        elif mode == "persistent":
            self._client = chromadb.PersistentClient(path=data_path)
        elif mode == "docker":
            self._client = chromadb.HttpClient(host=host or "localhost", port=port or 8001)
        else:
            raise ValueError(f"Unknown brain mode: {mode}")

        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "Matrix Agent Team shared memory"},
        )

    def _run_sync(self, func, *args, **kwargs):
        """Run a sync ChromaDB call in an executor to avoid blocking."""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(None, partial(func, *args, **kwargs))

    async def capture(
        self,
        content: str,
        source: str = "unknown",
        metadata: dict | None = None,
    ) -> str:
        """Store a thought. Returns the thought ID."""
        thought_id = str(uuid.uuid4())
        meta = {
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": "uncategorized",
        }
        if metadata:
            # ChromaDB metadata values must be str, int, float, or bool
            for k, v in metadata.items():
                if isinstance(v, list):
                    meta[k] = ", ".join(str(item) for item in v)
                else:
                    meta[k] = v

        await self._run_sync(
            self._collection.add,
            ids=[thought_id],
            documents=[content],
            metadatas=[meta],
        )
        return thought_id

    async def search(
        self,
        query: str,
        n_results: int = 5,
        where: dict | None = None,
    ) -> list[dict]:
        """Semantic search. Returns list of {id, content, metadata, distance}."""
        count = self._collection.count()
        if count == 0:
            return []

        kwargs = {
            "query_texts": [query],
            "n_results": min(n_results, count),
        }
        if where:
            kwargs["where"] = where

        results = await self._run_sync(self._collection.query, **kwargs)

        thoughts = []
        for i in range(len(results["ids"][0])):
            thoughts.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if results.get("distances") else None,
            })
        return thoughts

    async def browse(self, limit: int = 20, offset: int = 0) -> list[dict]:
        """Get recent thoughts by insertion order."""
        count = self._collection.count()
        if count == 0:
            return []

        results = await self._run_sync(
            self._collection.get,
            limit=min(limit, count),
            offset=offset,
            include=["documents", "metadatas"],
        )

        thoughts = []
        for i in range(len(results["ids"])):
            thoughts.append({
                "id": results["ids"][i],
                "content": results["documents"][i],
                "metadata": results["metadatas"][i],
            })
        return thoughts

    async def stats(self) -> dict:
        """Return brain statistics."""
        count = self._collection.count()
        categories: dict[str, int] = {}
        sources: dict[str, int] = {}

        if count > 0:
            all_data = await self._run_sync(
                self._collection.get, include=["metadatas"]
            )
            for meta in all_data["metadatas"]:
                cat = meta.get("category", "uncategorized")
                categories[cat] = categories.get(cat, 0) + 1
                src = meta.get("source", "unknown")
                sources[src] = sources.get(src, 0) + 1

        return {"count": count, "categories": categories, "sources": sources}

    async def delete(self, thought_id: str) -> bool:
        """Delete a thought by ID."""
        try:
            await self._run_sync(self._collection.delete, ids=[thought_id])
            return True
        except Exception:
            return False
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_brain.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add shared/brain.py tests/test_brain.py tests/conftest.py
git commit -m "feat: add MatrixBrain shared memory module (ChromaDB)"
```

---

### Task 2: Settings Additions

**Files:**
- Modify: `config/settings.py:4-31`
- Modify: `.env`
- Modify: `docker/.env.example`

- [ ] **Step 1: Add brain and MCP settings to Settings class**

Add after line 23 (`chroma_port`) in `config/settings.py`:

```python
    # Brain (shared memory)
    brain_mode: str = "persistent"  # "ephemeral", "persistent", "docker"
    brain_data_path: str = "data/brain"

    # MCP Server
    mcp_port: int = 8002
    mcp_access_key: str = ""  # Empty = no auth (dev mode)

    # Slack Capture
    slack_capture_channel_id: str = ""
```

- [ ] **Step 2: Add to .env and docker/.env.example**

Append to both files:

```bash
# Brain (Matrix Brain shared memory)
BRAIN_MODE=persistent
BRAIN_DATA_PATH=data/brain

# MCP Server
MCP_PORT=8002
MCP_ACCESS_KEY=

# Slack Capture Channel (separate from main channel)
SLACK_CAPTURE_CHANNEL_ID=
```

- [ ] **Step 3: Run existing tests to verify no breakage**

Run: `pytest tests/ -v`
Expected: All 58 existing tests PASS

- [ ] **Step 4: Commit**

```bash
git add config/settings.py .env docker/.env.example
git commit -m "feat: add brain, MCP, and capture channel settings"
```

---

### Task 3: Metadata Extractor

**Files:**
- Create: `shared/brain_extractor.py`
- Create: `tests/test_brain_extractor.py`

**Key pattern:** Mock `BedrockClient.chat` with `AsyncMock`. Graceful fallback — if LLM fails, return defaults and still capture the thought.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_brain_extractor.py
import json
import pytest
from unittest.mock import AsyncMock

from shared.brain_extractor import BrainExtractor


class TestBrainExtractor:
    @pytest.fixture
    def mock_llm(self):
        llm = AsyncMock()
        llm.chat = AsyncMock()
        return llm

    @pytest.mark.asyncio
    async def test_extract_returns_structured_metadata(self, mock_llm):
        mock_llm.chat.return_value = json.dumps({
            "category": "idea",
            "summary": "A new feature",
            "people": ["Alice"],
            "action_items": ["Prototype it"],
        })
        extractor = BrainExtractor(llm_client=mock_llm)
        result = await extractor.extract("Alice suggested a new feature idea")
        assert result["category"] == "idea"
        assert "Alice" in result["people"]
        assert len(result["action_items"]) == 1

    @pytest.mark.asyncio
    async def test_extract_handles_llm_error(self, mock_llm):
        mock_llm.chat.side_effect = Exception("LLM down")
        extractor = BrainExtractor(llm_client=mock_llm)
        result = await extractor.extract("Some thought")
        assert result["category"] == "uncategorized"
        assert "summary" in result

    @pytest.mark.asyncio
    async def test_extract_handles_malformed_json(self, mock_llm):
        mock_llm.chat.return_value = "This is not JSON at all"
        extractor = BrainExtractor(llm_client=mock_llm)
        result = await extractor.extract("Some thought")
        assert result["category"] == "uncategorized"

    @pytest.mark.asyncio
    async def test_capture_enriched_stores_with_metadata(self, brain, mock_llm):
        mock_llm.chat.return_value = json.dumps({
            "category": "decision",
            "summary": "Chose Python",
            "people": [],
            "action_items": [],
        })
        extractor = BrainExtractor(llm_client=mock_llm)
        thought_id = await extractor.capture_enriched(brain, "We decided to use Python", source="test")
        assert thought_id is not None

        results = await brain.search("Python", n_results=1)
        assert len(results) == 1
        assert results[0]["metadata"]["category"] == "decision"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_brain_extractor.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement BrainExtractor**

```python
# shared/brain_extractor.py
"""Metadata extraction for Matrix Brain thoughts via LLM."""
from __future__ import annotations

import json
import re

from shared.llm_client import BedrockClient


EXTRACTION_PROMPT = """Analyze this thought and extract metadata. Return ONLY valid JSON, no other text.

Format: {"category": "...", "summary": "...", "people": [...], "action_items": [...]}

Categories (pick one): idea, decision, question, reference, meeting_note, task, observation, person_note

Rules:
- summary: one sentence, max 100 characters
- people: list of names mentioned (empty list if none)
- action_items: list of actionable next steps (empty list if none)"""


class BrainExtractor:
    """Extracts structured metadata from raw thoughts using LLM."""

    def __init__(self, llm_client: BedrockClient | None = None):
        self._llm = llm_client

    async def extract(self, content: str) -> dict:
        """Extract metadata from content. Returns dict with category, summary, people, action_items."""
        defaults = {
            "category": "uncategorized",
            "summary": content[:100],
            "people": [],
            "action_items": [],
        }

        if not self._llm:
            return defaults

        try:
            response = await self._llm.chat(
                system_prompt=EXTRACTION_PROMPT,
                messages=[{"role": "user", "content": content}],
            )
            # Extract JSON from response (handle LLM wrapping in text)
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return {
                    "category": parsed.get("category", "uncategorized"),
                    "summary": parsed.get("summary", content[:100]),
                    "people": parsed.get("people", []),
                    "action_items": parsed.get("action_items", []),
                }
        except Exception:
            pass

        return defaults

    async def capture_enriched(
        self,
        brain,
        content: str,
        source: str = "unknown",
    ) -> str:
        """Extract metadata then capture to brain. Returns thought ID."""
        metadata = await self.extract(content)
        return await brain.capture(content, source=source, metadata=metadata)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_brain_extractor.py -v`
Expected: All PASS

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS (existing 58 + new brain tests)

- [ ] **Step 6: Commit**

```bash
git add shared/brain_extractor.py tests/test_brain_extractor.py
git commit -m "feat: add BrainExtractor for LLM metadata extraction"
```

---

## Chunk 2: Agent Integration

### Task 4: Add Brain to Base Agent

**Files:**
- Modify: `agents/base_agent.py:21`
- Modify: `tests/test_base_agent.py`

- [ ] **Step 1: Add test for brain parameter**

Add to `tests/test_base_agent.py`:

```python
@pytest.mark.asyncio
async def test_agent_brain_defaults_to_none(self):
    """Brain parameter is optional and defaults to None."""
    agent = self._create_agent()
    assert agent.brain is None

@pytest.mark.asyncio
async def test_agent_accepts_brain(self, brain):
    """Agent accepts a brain instance."""
    agent = self._create_agent(brain=brain)
    assert agent.brain is brain
```

Note: The test class likely has a `_create_agent` helper or uses a concrete subclass. Adapt to the existing pattern — check the file first.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_base_agent.py -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'brain'`

- [ ] **Step 3: Add brain parameter to MatrixAgent**

In `agents/base_agent.py`, modify `__init__`:

```python
def __init__(self, name: str, role: str, llm_client: BedrockClient | None = None,
             brain=None):
    self.name = name
    self.role = role
    self.status = "IDLE"
    self._logger = get_agent_logger(name)
    self._llm_client = llm_client
    self.brain = brain
    # ... rest unchanged
```

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/ -v`
Expected: All PASS — `brain=None` default is backward-compatible

- [ ] **Step 5: Commit**

```bash
git add agents/base_agent.py tests/test_base_agent.py
git commit -m "feat: add optional brain parameter to MatrixAgent"
```

---

### Task 5: Wire Brain into Neo + Console Commands

**Files:**
- Modify: `agents/neo.py`

**Changes:**
1. Create `MatrixBrain` in `main()`
2. Pass `brain` to `build_registry()`
3. Add `/capture <text>` command
4. Add `/brain` command (stats) and `/brain search <query>`
5. Refactor command dispatch to handle prefix commands

- [ ] **Step 1: Modify build_registry to accept brain**

In `agents/neo.py`, change `build_registry`:

```python
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
```

- [ ] **Step 2: Create brain in main() and pass it through**

```python
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
    # ... rest similar, passing brain where needed
```

- [ ] **Step 3: Add /capture and /brain commands**

Update `handle_meta_command` to accept `brain` parameter. Add handling:

```python
async def handle_meta_command(
    command: str, orchestrator: MatrixOrchestrator, adapter: SlackAdapter,
    brain=None,
) -> bool:
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

    # ... existing handlers unchanged
```

- [ ] **Step 4: Refactor command dispatch in console_loop**

The `console_loop` currently checks `user_input.lower() in META_COMMANDS` (exact match). Change to prefix-based dispatch for `/capture` and `/brain`:

```python
# In console_loop, replace the command check:
cmd = user_input.strip()
cmd_lower = cmd.lower()

if cmd_lower.startswith("/capture") or cmd_lower.startswith("/brain") or cmd_lower in META_COMMANDS:
    should_exit = await handle_meta_command(cmd_lower, orchestrator, adapter, brain=brain)
    if should_exit:
        break
else:
    await process_task(user_input, orchestrator, adapter)
```

- [ ] **Step 5: Update META_COMMANDS set and /help text**

Add `/capture` and `/brain` to help text:

```python
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
```

- [ ] **Step 6: Run full test suite**

Run: `pytest tests/ -v`
Expected: All PASS

- [ ] **Step 7: Manual test in console mode**

```bash
source .venv/bin/activate
python3 -m agents.neo
# Type: /capture Sarah mentioned she's thinking about consulting
# Type: /brain
# Type: /brain search career changes
# Type: /quit
```

- [ ] **Step 8: Commit**

```bash
git add agents/neo.py
git commit -m "feat: wire Matrix Brain into Neo with /capture and /brain commands"
```

---

## Chunk 3: Slack Capture + MCP Server

### Task 6: Slack Capture Channel Integration

**Files:**
- Modify: `integrations/slack_adapter.py`
- Modify: `agents/neo.py` (Slack mode wiring)

- [ ] **Step 1: Add on_capture callback to SlackAdapter**

In `slack_adapter.py`, add to `__init__`:

```python
self._on_capture: Callable | None = None
self._capture_channel_id = settings.slack_capture_channel_id if settings.slack_capture_channel_id else None
```

Add method:

```python
def on_capture(self, callback: Callable) -> None:
    """Register callback for capture channel messages."""
    self._on_capture = callback
```

- [ ] **Step 2: Modify Slack message handler to detect capture channel**

In `_init_slack`, modify the message handler:

```python
@self._slack_app.event("message")
async def handle_message(event, say):
    if event.get("subtype") is not None:
        return

    channel = event.get("channel", "")
    text = event.get("text", "")

    # Capture channel -> brain ingestion
    if self._capture_channel_id and channel == self._capture_channel_id and self._on_capture:
        await self._on_capture(text, event.get("user", "unknown"), event.get("ts"))
        return

    # Normal message -> command/task handling
    if self._on_message:
        thread_ts = event.get("ts")
        await self._on_message(text, thread_ts)
```

- [ ] **Step 3: Wire capture in Neo's Slack mode**

In `neo.py`'s `main()`, Slack mode section:

```python
async def on_slack_capture(text: str, user: str, thread_ts: str) -> None:
    extractor = BrainExtractor(llm_client=llm_client)
    thought_id = await extractor.capture_enriched(brain, text, source=f"slack:{user}")
    # Reply in thread with confirmation
    stats = await brain.stats()
    meta = (await brain.search(text, n_results=1))[0]["metadata"] if thought_id else {}
    cat = meta.get("category", "uncategorized")
    summary = meta.get("summary", text[:50])
    await adapter.post_message(
        "Neo",
        f"Captured as {cat} — {summary}\nTotal: {stats['count']} thoughts",
        thread_id=thread_ts,
    )

adapter.on_capture(on_slack_capture)
```

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/ -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add integrations/slack_adapter.py agents/neo.py
git commit -m "feat: add Slack capture channel integration for Matrix Brain"
```

---

### Task 7: MCP Server

**Files:**
- Create: `mcp_server/__init__.py`
- Create: `mcp_server/brain_server.py`
- Create: `tests/test_brain_mcp.py`
- Modify: `requirements.txt`

**Note:** Check the actual `mcp` package API before implementing. The tool decorator pattern below is based on MCP SDK v1.x — verify against the installed version. The key is that tool handlers are async functions that return results. If the API differs, adapt the implementation.

- [ ] **Step 1: Add mcp to requirements.txt**

Append to `requirements.txt`:

```
mcp>=1.0.0
```

Install: `pip install mcp`

- [ ] **Step 2: Write failing tests**

```python
# tests/test_brain_mcp.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from mcp_server.brain_server import search_handler, capture_handler, browse_handler, stats_handler


class TestMCPBrainTools:
    @pytest.fixture
    def mock_brain(self):
        brain = AsyncMock()
        brain.search = AsyncMock(return_value=[
            {"id": "abc", "content": "Test thought", "metadata": {"category": "idea"}, "distance": 0.1}
        ])
        brain.capture = AsyncMock(return_value="new-id-123")
        brain.browse = AsyncMock(return_value=[
            {"id": "abc", "content": "Recent thought", "metadata": {"category": "task"}}
        ])
        brain.stats = AsyncMock(return_value={"count": 5, "categories": {"idea": 3, "task": 2}, "sources": {}})
        return brain

    @pytest.mark.asyncio
    async def test_search_handler(self, mock_brain):
        result = await search_handler(mock_brain, query="test", n_results=5, category=None)
        mock_brain.search.assert_called_once()
        assert "Test thought" in result

    @pytest.mark.asyncio
    async def test_capture_handler(self, mock_brain):
        result = await capture_handler(mock_brain, content="New thought", source="mcp")
        mock_brain.capture.assert_called_once()
        assert "new-id-123" in result

    @pytest.mark.asyncio
    async def test_browse_handler(self, mock_brain):
        result = await browse_handler(mock_brain, limit=20)
        mock_brain.browse.assert_called_once()
        assert "Recent thought" in result

    @pytest.mark.asyncio
    async def test_stats_handler(self, mock_brain):
        result = await stats_handler(mock_brain)
        mock_brain.stats.assert_called_once()
        assert "5" in result
```

- [ ] **Step 3: Implement MCP server**

```python
# mcp_server/__init__.py
# (empty)
```

```python
# mcp_server/brain_server.py
"""Matrix Brain MCP Server — exposes brain tools to external AI clients."""
from __future__ import annotations

import json

from shared.brain import MatrixBrain
from config.settings import settings


# --- Tool handlers (testable independently) ---

async def search_handler(brain: MatrixBrain, query: str, n_results: int = 5,
                         category: str | None = None) -> str:
    where = {"category": category} if category else None
    results = await brain.search(query, n_results=n_results, where=where)
    return json.dumps(results, indent=2, default=str)


async def capture_handler(brain: MatrixBrain, content: str, source: str = "mcp") -> str:
    thought_id = await brain.capture(content, source=source)
    return json.dumps({"status": "captured", "id": thought_id})


async def browse_handler(brain: MatrixBrain, limit: int = 20) -> str:
    results = await brain.browse(limit=limit)
    return json.dumps(results, indent=2, default=str)


async def stats_handler(brain: MatrixBrain) -> str:
    stats = await brain.stats()
    return json.dumps(stats, indent=2)


# --- MCP Server setup ---

def create_server():
    """Create and configure the MCP server with brain tools."""
    from mcp.server import Server

    server = Server("matrix-brain")
    brain = MatrixBrain(
        mode=settings.brain_mode,
        data_path=settings.brain_data_path,
        host=settings.chroma_host,
        port=settings.chroma_port,
    )

    @server.tool()
    async def brain_search(query: str, n_results: int = 5, category: str | None = None) -> str:
        """Search the Matrix Brain by meaning. Returns semantically similar thoughts."""
        return await search_handler(brain, query, n_results, category)

    @server.tool()
    async def brain_capture(content: str, source: str = "mcp") -> str:
        """Save a thought to the Matrix Brain."""
        return await capture_handler(brain, content, source)

    @server.tool()
    async def brain_browse(limit: int = 20) -> str:
        """Browse recent thoughts in the Matrix Brain."""
        return await browse_handler(brain, limit)

    @server.tool()
    async def brain_stats() -> str:
        """Get Matrix Brain statistics — total thoughts, categories, sources."""
        return await stats_handler(brain)

    return server


def main():
    """Run the MCP server as a standalone process."""
    from mcp.server.stdio import StdioServerTransport

    server = create_server()
    transport = StdioServerTransport()
    server.run(transport)


if __name__ == "__main__":
    main()
```

**Connection from Claude Code:**
```bash
claude mcp add matrix-brain -- python3 -m mcp_server.brain_server
```

**Connection from other MCP clients (JSON config):**
```json
{
  "mcpServers": {
    "matrix-brain": {
      "command": "python3",
      "args": ["-m", "mcp_server.brain_server"],
      "cwd": "/path/to/matrix-agents"
    }
  }
}
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_brain_mcp.py -v`
Expected: All PASS

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add mcp_server/ tests/test_brain_mcp.py requirements.txt
git commit -m "feat: add MCP server exposing Matrix Brain tools"
```

---

## Chunk 4: Oracle Enhancement + Final Verification

### Task 8: Oracle Brain-Augmented Search

**Files:**
- Modify: `agents/oracle.py`
- Modify: `tests/test_agents.py` (add Oracle-specific tests)

- [ ] **Step 1: Add Oracle brain tests**

Add to `tests/test_agents.py`:

```python
class TestOracleBrainIntegration:
    @pytest.mark.asyncio
    async def test_oracle_searches_brain_when_available(self):
        from agents.oracle import Oracle
        brain = AsyncMock()
        brain.search = AsyncMock(return_value=[
            {"content": "Python was created by Guido van Rossum", "metadata": {"category": "reference"}}
        ])
        brain.capture = AsyncMock(return_value="id-123")

        oracle = Oracle(brain=brain)
        oracle.call_llm = AsyncMock(return_value="Python is a programming language created by Guido.")
        result = await oracle.execute({"content": "Tell me about Python", "action": "user_request"})

        assert result.status == "success"
        brain.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_oracle_works_without_brain(self):
        from agents.oracle import Oracle
        oracle = Oracle()
        oracle.call_llm = AsyncMock(return_value="Response without brain")
        result = await oracle.execute({"content": "Hello", "action": "user_request"})
        assert result.status == "success"
```

- [ ] **Step 2: Modify Oracle to use brain**

Replace `agents/oracle.py`:

```python
from agents.base_agent import MatrixAgent
from shared.models import AgentResult


class Oracle(MatrixAgent):
    """Oracle - Research & Knowledge Retrieval specialist with Brain-augmented search."""

    def __init__(self, **kwargs):
        super().__init__(name="Oracle", role="Research & Knowledge Retrieval", **kwargs)

    async def execute(self, task: dict) -> AgentResult:
        self.log("info", f"Received task: {task.get('action', 'unknown')}")
        try:
            content = task.get("content", "")

            # Search brain for relevant context
            context = ""
            if self.brain:
                results = await self.brain.search(content, n_results=3)
                if results:
                    context_lines = [f"- {r['content']}" for r in results]
                    context = "Relevant from Matrix Brain:\n" + "\n".join(context_lines)

            prompt = f"Research the following and provide a thorough answer:\n\n{content}"
            if context:
                prompt = f"{context}\n\n---\n\n{prompt}"

            response = await self.call_llm([{"role": "user", "content": prompt}])

            # Capture research result back to brain
            if self.brain:
                await self.brain.capture(
                    response[:500], source="Oracle",
                    metadata={"category": "reference"},
                )

            return AgentResult(agent=self.name, status="success", content=response)
        except Exception as e:
            self.log("error", f"Execution failed: {e}")
            return AgentResult(agent=self.name, status="error", content="", error=str(e))
```

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add agents/oracle.py tests/test_agents.py
git commit -m "feat: enhance Oracle with brain-augmented search (RAG)"
```

---

### Task 9: End-to-End Verification

- [ ] **Step 1: Run full test suite**

```bash
source .venv/bin/activate
pytest tests/ -v
```

Expected: All tests PASS (58 existing + ~20 new brain tests)

- [ ] **Step 2: Manual console mode test**

```bash
python3 -m agents.neo
```

Test sequence:
```
You> /capture Sarah mentioned she's thinking about leaving her job
# Expect: "Captured to Matrix Brain (ID: ...)" with category
You> /brain
# Expect: "Thoughts: 1, Categories: ..."
You> /brain search career changes
# Expect: Sarah's thought appears
You> /capture Decided to use Python for the new project
You> /brain
# Expect: "Thoughts: 2"
You> Ask Oracle about recent decisions
# Expect: Oracle's response includes brain context about Python decision
You> /quit
```

- [ ] **Step 3: Test MCP server locally**

```bash
# In another terminal:
source .venv/bin/activate
python3 -m mcp_server.brain_server
# Server starts on stdio transport

# Or connect via Claude Code:
claude mcp add matrix-brain -- python3 -m mcp_server.brain_server
```

- [ ] **Step 4: Final commit**

```bash
git add -A
git push origin main
```

---

## Verification Summary

| Test | Command | Expected |
|------|---------|----------|
| Unit tests | `pytest tests/ -v` | All pass |
| Console capture | `/capture <text>` in Neo | Thought stored, confirmation shown |
| Console search | `/brain search <query>` in Neo | Relevant results returned |
| Console stats | `/brain` in Neo | Count and categories shown |
| Oracle RAG | Ask Oracle a question after capturing related thoughts | Oracle includes brain context |
| MCP server | `python3 -m mcp_server.brain_server` | Server starts, tools available |
| Backward compat | Existing 58 tests | All still pass |
