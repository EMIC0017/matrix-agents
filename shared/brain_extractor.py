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
