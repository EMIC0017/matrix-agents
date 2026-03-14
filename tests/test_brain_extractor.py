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
