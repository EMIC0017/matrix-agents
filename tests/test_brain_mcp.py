"""Tests for MCP Brain server tool handlers."""
import pytest
from unittest.mock import AsyncMock

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
