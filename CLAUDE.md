# Matrix Agents - Claude Code Instructions

## Memory: Use Matrix Brain

Matrix Brain is the shared persistent memory for this project and your default memory system. Use the MCP tools (`brain_search`, `brain_capture`, `brain_browse`, `brain_stats`) instead of file-based memory whenever possible.

### When to capture (brain_capture)
- Decisions made during development ("chose ChromaDB over pgvector because...")
- Important findings ("the AI Gateway requires short model aliases like claude-sonnet-4")
- User preferences and corrections
- Architecture insights that would help future sessions
- Anything the user asks you to remember

### When to search (brain_search)
- Before starting work on a topic, search for prior context
- When the user references something from a previous session
- Before making architecture decisions (check if there's prior art)

### Workflow
1. At session start: `brain_search` for relevant context about the current task
2. During work: `brain_capture` important decisions and findings
3. At session end: `brain_capture` a summary of what was accomplished

## Project Overview

Multi-agent AI system with 11 Matrix-themed agents. See README.md for full details.

## Key Technical Notes

- **LLM**: Instacart AI Gateway → Bedrock. Use short model aliases (`claude-sonnet-4`), not raw Bedrock IDs
- **Agent identity**: All prompts in `config/agent_prompts.yml` include character anchoring — don't break persona
- **Merovingian**: Router lives inside `MatrixOrchestrator`, not in agent registry. JSON extraction uses regex fallback
- **Tests**: `pytest tests/ -v` — currently 78 tests, all passing
- **Console mode**: `python3 -m agents.neo` — works without Docker
- **Brain data**: Stored in `data/brain/` (gitignored), ChromaDB persistent mode

## Code Style

- Python 3.14, async-first
- pydantic-settings for config
- Type hints on all public APIs
- No docstrings on obvious methods
