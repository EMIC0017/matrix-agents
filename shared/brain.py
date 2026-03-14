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
