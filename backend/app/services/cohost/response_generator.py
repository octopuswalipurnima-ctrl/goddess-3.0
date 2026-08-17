"""
Response Generator for AI Co-Host in GODDESS AI 2.0.
Interfaces with centralized Gemini AI Manager using NORMAL priority,
incorporates stream awareness, creator knowledge, and anti-repetition similarity checks.
"""

import re
import time
from typing import Optional
from app.core.logging import get_logger
from app.services.cohost.awareness import StreamAwarenessEngine, stream_awareness_engine
from app.services.cohost.context import CoHostContextManager, cohost_context_manager
from app.services.cohost.deduplication import ResponseDeduplicator, response_deduplicator
from app.services.cohost.knowledge import CreatorKnowledgeManager, creator_knowledge_manager
from app.services.cohost.models import (
    CoHostConfig,
    CoHostIntent,
    CoHostMessage,
    CoHostResponse,
    EngagementDecision,
    ResponseStatus,
)
from app.services.cohost.personality import CoHostPersonalityManager, cohost_personality_manager
from app.services.cohost.prompts import BASE_COHOST_SYSTEM_INSTRUCTION, build_cohost_prompt
from app.services.gemini.manager import GeminiAIManager, gemini_manager
from app.services.gemini.models import AIRequest, AIRequestPriority, AIResponseStatus

logger = get_logger("cohost.generator")


class ResponseGenerator:
    """Generates conversational live chat replies using Gemini AI with anti-repetition & knowledge guards."""

    def __init__(
        self,
        ai_manager: Optional[GeminiAIManager] = None,
        context_mgr: Optional[CoHostContextManager] = None,
        personality_mgr: Optional[CoHostPersonalityManager] = None,
        awareness_engine: Optional[StreamAwarenessEngine] = None,
        knowledge_mgr: Optional[CreatorKnowledgeManager] = None,
        deduplicator: Optional[ResponseDeduplicator] = None,
    ):
        self.ai_manager = ai_manager or gemini_manager
        self.context_mgr = context_mgr or cohost_context_manager
        self.personality_mgr = personality_mgr or cohost_personality_manager
        self.awareness = awareness_engine or stream_awareness_engine
        self.knowledge = knowledge_mgr or creator_knowledge_manager
        self.deduplicator = deduplicator or response_deduplicator

    def _sanitize_response(self, text: str, max_length: int = 200) -> str:
        """Clean and normalize generated AI text to ensure safe live chat formatting."""
        # 1. Strip markdown fences and formatting
        cleaned = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        cleaned = re.sub(r"[\r\n]+", " ", cleaned).strip()

        # 2. Strip quotation marks if whole message is enclosed in quotes
        if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
            cleaned = cleaned[1:-1].strip()

        # 3. Strip command prefixes (! / $)
        cleaned = re.sub(r"^(!|/|\$)", "", cleaned).strip()

        # 4. Enforce maximum character length (strictly max 200 chars)
        if len(cleaned) > max_length:
            truncated = cleaned[:max_length]
            last_space = truncated.rfind(" ")
            if last_space > max_length * 0.7:
                cleaned = truncated[:last_space] + "..."
            else:
                cleaned = truncated[:max_length - 3] + "..."

        return cleaned

    async def generate_response(
        self,
        msg: CoHostMessage,
        intent: CoHostIntent,
        config: CoHostConfig,
        engagement_decision: Optional[EngagementDecision] = None,
    ) -> CoHostResponse:
        """
        Generate a conversational reply for an incoming viewer message.
        Enforces 1-attempt regeneration on high similarity before returning fail-closed.
        """
        start_time = time.time()
        stream_id = msg.stream_id
        personality = self.personality_mgr.get_personality(stream_id) if config.personality_enabled else config.personality

        # 1. Gather short-term conversational context
        ctx = self.context_mgr.get_context(
            stream_id=stream_id,
            max_stream_messages=config.context_window_size,
            max_user_messages=config.user_context_window_size,
        )
        context_str = ctx.get_formatted_context(current_author_id=msg.author_id)

        # 2. Gather stream awareness and creator knowledge
        awareness_str = self.awareness.build_awareness_prompt(stream_id)
        knowledge_str = self.knowledge.build_knowledge_prompt(stream_id, query=msg.message_text)
        personality_str = self.personality_mgr.build_personality_prompt(personality)

        # Priority from engagement decision or default NORMAL
        priority_enum = AIRequestPriority.HIGH if (engagement_decision and engagement_decision.priority == "HIGH") else AIRequestPriority.NORMAL

        attempts = 0
        max_attempts = max(1, 1 + config.max_regeneration_attempts)
        variation_directive = ""
        last_response_text = ""
        last_model = "gemini-2.5-flash"
        fallback_used = False

        while attempts < max_attempts:
            attempts += 1
            user_prompt = build_cohost_prompt(
                msg=msg,
                personality_prompt=personality_str,
                context_str=context_str,
                awareness_str=awareness_str,
                knowledge_str=knowledge_str,
                engagement_decision=engagement_decision,
                variation_directive=variation_directive,
            )

            ai_req = AIRequest(
                stream_id=stream_id,
                source="cohost",
                prompt=user_prompt,
                system_instruction=BASE_COHOST_SYSTEM_INSTRUCTION,
                priority=priority_enum,
                timeout_seconds=8.0,
                temperature=0.75 if attempts > 1 else 0.7,
            )

            try:
                ai_res = await self.ai_manager.request(ai_req)
            except Exception as exc:
                latency = (time.time() - start_time) * 1000
                logger.warning(f"Co-Host Gemini request exception for stream '{stream_id}': {exc}")
                return CoHostResponse(
                    stream_id=stream_id,
                    message_id=msg.message_id,
                    author_id=msg.author_id,
                    author_name=msg.author_name,
                    response_text="",
                    status=ResponseStatus.FAILED,
                    intent=intent,
                    engagement_decision=engagement_decision,
                    latency_ms=latency,
                    block_reason=f"Gemini API request error: {str(exc)}",
                )

            ai_text = getattr(ai_res, "text", getattr(ai_res, "content", "")) or ""
            fallback_used = getattr(ai_res, "fallback_used", False)
            if not fallback_used and hasattr(ai_res, "metadata") and isinstance(ai_res.metadata, dict):
                fallback_used = ai_res.metadata.get("fallback_used", False)

            if ai_res.status != AIResponseStatus.SUCCESS or not ai_text:
                latency = (time.time() - start_time) * 1000
                logger.warning(
                    f"Co-Host Gemini generation unsuccessful for stream '{stream_id}': Status={ai_res.status}, Reason={ai_res.error_message}"
                )
                return CoHostResponse(
                    stream_id=stream_id,
                    message_id=msg.message_id,
                    author_id=msg.author_id,
                    author_name=msg.author_name,
                    response_text="",
                    status=ResponseStatus.FAILED,
                    intent=intent,
                    engagement_decision=engagement_decision,
                    latency_ms=latency,
                    model=ai_res.model or getattr(ai_res, "model_used", "gemini-2.5-flash"),
                    fallback_used=fallback_used,
                    block_reason=ai_res.error_message or "AI model returned empty response",
                )

            cleaned_text = self._sanitize_response(ai_text, max_length=config.max_response_length)
            last_response_text = cleaned_text
            last_model = ai_res.model or getattr(ai_res, "model_used", "gemini-2.5-flash")

            # Check similarity against recent responses in this stream
            is_sim, sim_score = self.deduplicator.is_similar(stream_id, cleaned_text, threshold=0.70)
            if not is_sim:
                # Response is fresh and unique
                latency = (time.time() - start_time) * 1000
                return CoHostResponse(
                    stream_id=stream_id,
                    message_id=msg.message_id,
                    author_id=msg.author_id,
                    author_name=msg.author_name,
                    response_text=cleaned_text,
                    status=ResponseStatus.APPROVED,
                    intent=intent,
                    engagement_decision=engagement_decision,
                    latency_ms=latency,
                    model=last_model,
                    fallback_used=fallback_used,
                )

            # High similarity detected: prepare variation directive for 1 retry
            logger.info(
                f"Co-Host similarity trigger on stream '{stream_id}' (sim={sim_score:.2f}, attempt={attempts}/{max_attempts})."
            )
            variation_directive = f"Your previous reply '{cleaned_text}' was too similar to recent messages. Use completely different words and angle."

        # Exceeded regeneration attempts on high similarity -> return BLOCKED / NO_RESPONSE
        latency = (time.time() - start_time) * 1000
        return CoHostResponse(
            stream_id=stream_id,
            message_id=msg.message_id,
            author_id=msg.author_id,
            author_name=msg.author_name,
            response_text=last_response_text,
            status=ResponseStatus.BLOCKED,
            intent=intent,
            engagement_decision=engagement_decision,
            latency_ms=latency,
            model=last_model,
            fallback_used=fallback_used,
            block_reason="Generated response was too similar to recent responses after regeneration attempt",
        )


# Global singleton instance
response_generator = ResponseGenerator()
