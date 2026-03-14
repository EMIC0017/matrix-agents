"""Matrix Brain MCP Server — exposes brain tools to external AI clients."""
from __future__ import annotations

import json

from mcp.server import FastMCP

from shared.brain import MatrixBrain
from config.settings import settings


# --- Tool handlers (testable independently) ---

async def search_handler(brain: MatrixBrain, query: str, n_results: int = 5,
                         category: str | None = None) -> str:
    """Search the Matrix Brain for relevant thoughts."""
    where = {"category": category} if category else None
    results = await brain.search(query, n_results=n_results, where=where)
    return json.dumps(results, indent=2, default=str)


async def capture_handler(brain: MatrixBrain, content: str, source: str = "mcp") -> str:
    """Capture a new thought in the Matrix Brain."""
    thought_id = await brain.capture(content, source=source)
    return json.dumps({"status": "captured", "id": thought_id})


async def browse_handler(brain: MatrixBrain, limit: int = 20) -> str:
    """Browse recent thoughts from the Matrix Brain."""
    results = await brain.browse(limit=limit)
    return json.dumps(results, indent=2, default=str)


async def stats_handler(brain: MatrixBrain) -> str:
    """Get statistics about the Matrix Brain."""
    stats = await brain.stats()
    return json.dumps(stats, indent=2)


# --- MCP Server setup ---

def create_server() -> FastMCP:
    """Create and configure the MCP server."""
    mcp = FastMCP("matrix-brain")

    # Initialize the brain
    brain = MatrixBrain(
        mode=settings.brain_mode,
        data_path=settings.brain_data_path,
        host=settings.chroma_host,
        port=settings.chroma_port,
    )

    @mcp.tool()
    async def search(query: str, n_results: int = 5, category: str | None = None) -> str:
        """Search the Matrix Brain for relevant thoughts.

        Args:
            query: The search query text
            n_results: Maximum number of results to return (default: 5)
            category: Optional category filter
        """
        return await search_handler(brain, query, n_results, category)

    @mcp.tool()
    async def capture(content: str, source: str = "mcp") -> str:
        """Capture a new thought in the Matrix Brain.

        Args:
            content: The thought content to capture
            source: Source identifier for the thought (default: "mcp")
        """
        return await capture_handler(brain, content, source)

    @mcp.tool()
    async def browse(limit: int = 20) -> str:
        """Browse recent thoughts from the Matrix Brain.

        Args:
            limit: Maximum number of thoughts to return (default: 20)
        """
        return await browse_handler(brain, limit)

    @mcp.tool()
    async def stats() -> str:
        """Get statistics about the Matrix Brain including count, categories, and sources."""
        return await stats_handler(brain)

    return mcp


def main():
    """Run the MCP server with stdio transport."""
    mcp = create_server()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
