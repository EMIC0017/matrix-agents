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
