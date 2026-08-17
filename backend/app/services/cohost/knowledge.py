"""
Creator Knowledge Base Manager for AI Co-Host in GODDESS AI 2.0.
Provides stream-scoped creator-approved facts with strict anti-hallucination enforcement.
"""

from datetime import datetime, timezone
import re
from typing import Dict, List, Optional
from app.core.logging import get_logger
from app.services.cohost.models import CreatorKnowledge

logger = get_logger("cohost.knowledge")


class CreatorKnowledgeManager:
    """Manages stream-scoped knowledge base entries with zero cross-stream contamination."""

    def __init__(self):
        # stream_id -> { fact_key: CreatorKnowledge }
        self._knowledge: Dict[str, Dict[str, CreatorKnowledge]] = {}

    def get_knowledge_entries(self, stream_id: str) -> List[CreatorKnowledge]:
        """Fetch all knowledge entries for a stream."""
        if stream_id not in self._knowledge:
            return []
        return list(self._knowledge[stream_id].values())

    def get_fact(self, stream_id: str, key: str) -> Optional[CreatorKnowledge]:
        """Fetch a specific fact by key for a stream."""
        normalized_key = key.strip().lower()
        stream_facts = self._knowledge.get(stream_id, {})
        return stream_facts.get(normalized_key)

    def set_fact(
        self,
        stream_id: str,
        key: str,
        value: str,
        category: str = "general",
        enabled: bool = True,
    ) -> CreatorKnowledge:
        """Add or update a knowledge base fact for a specific stream."""
        normalized_key = key.strip().lower()
        if stream_id not in self._knowledge:
            self._knowledge[stream_id] = {}

        entry = CreatorKnowledge(
            key=normalized_key,
            value=value.strip()[:500],  # Bound value size
            category=category.strip().lower(),
            stream_id=stream_id,
            enabled=enabled,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self._knowledge[stream_id][normalized_key] = entry
        logger.info(f"Set CreatorKnowledge fact '{normalized_key}' for stream '{stream_id}'.")
        return entry

    def delete_fact(self, stream_id: str, key: str) -> bool:
        """Delete a fact from stream knowledge."""
        normalized_key = key.strip().lower()
        if stream_id in self._knowledge and normalized_key in self._knowledge[stream_id]:
            del self._knowledge[stream_id][normalized_key]
            logger.info(f"Deleted CreatorKnowledge fact '{normalized_key}' for stream '{stream_id}'.")
            return True
        return False

    def clear_stream_knowledge(self, stream_id: str) -> None:
        """Clear all knowledge for a stream."""
        if stream_id in self._knowledge:
            del self._knowledge[stream_id]
            logger.info(f"Cleared CreatorKnowledge for stream '{stream_id}'.")

    def find_relevant_facts(self, stream_id: str, query: str) -> List[CreatorKnowledge]:
        """Find active facts matching keywords in query text."""
        stream_facts = self._knowledge.get(stream_id, {})
        if not stream_facts or not query:
            return []

        query_tokens = set(re.findall(r"\w+", query.lower()))
        matched: List[CreatorKnowledge] = []

        for fact in stream_facts.values():
            if not fact.enabled:
                continue
            fact_key_tokens = set(re.findall(r"\w+", fact.key.lower()))
            # Keyword match on key or category
            if query_tokens & fact_key_tokens or fact.category in query_tokens:
                matched.append(fact)

        return matched

    def build_knowledge_prompt(self, stream_id: str, query: Optional[str] = None) -> str:
        """
        Format creator knowledge into structured prompt text.
        Includes mandatory anti-hallucination instruction.
        """
        stream_facts = self._knowledge.get(stream_id, {})
        active_facts = [f for f in stream_facts.values() if f.enabled]

        if not active_facts:
            return "=== CREATOR KNOWLEDGE BASE ===\n(No creator facts configured. If asked for stream facts, say you don't know.)"

        lines = [
            "=== CREATOR KNOWLEDGE BASE (OFFICIAL APPROVED FACTS) ===",
            "Use ONLY these verified facts to answer questions. If a question is NOT answered below, do NOT guess.",
        ]
        for f in active_facts[:10]:  # Bound to max 10 facts in prompt
            lines.append(f"- [{f.category.upper()}] {f.key}: {f.value}")

        return "\n".join(lines)


# Global singleton instance
creator_knowledge_manager = CreatorKnowledgeManager()
