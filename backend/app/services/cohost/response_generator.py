"""
Response Generator for AI Co-Host in GODDESS AI 2.0.

Interfaces with the centralized Gemini AI Manager using NORMAL priority,
constructs structured prompts with personality and short-term context,
enforces character length caps (max 200 chars), and applies safety normalization.
"""

import re
import time
from typing import Optional

from app.core.logging import get_logger
from app.services.cohost.context import CoHostContextManager, cohost_context_manager
from app.services.cohost.models import (
    CoHostConfig,
    CoHostIntent,
    CoHostMessage,
    CoHostPersonality,
    CoHostResponse,
    ResponseStatus,
)
from app.services.cohost.personality import CoHostPersonalityManager, cohost_personality_manager
from app.services.cohost.prompts import BASE_COHOST_SYSTEM_INSTRUCTION, build_cohost_prompt
from app.services.gemini.manager import GeminiAIManager, gemini_manager
from app.services.gemini.models import AIRequest, AIRequestPriority, AIResponseStatus

logger = get_logger("cohost.generator")


class ResponseGenerator:
    """Generates conversational live chat replies using Gemini AI."""

    def __init__(
        self,
        ai_manager: Optional[GeminiAIManager] = None,
        context_mgr: Optional[CoHostContextManager] = None,
        personality_mgr: Optional[CoHostPersonalityManager] = None,
    ):
        self.ai_manager = ai_manager or gemini_manager
        self.context_mgr = context_mgr or cohost_context_manager
        self.personality_mgr = personality_mgr or cohost_personality_manager

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

        # 4. Enforce maximum character length (max 200 chars)
        if len(cleaned) > max_length:
            # Try to trim at word boundary
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
    ) -> CoHostResponse:
        """
        Generate a conversational reply for an incoming viewer message.
        """
        start_time = time.time()
        stream_id = msg.stream_id
        personality = config.personality

        # 1. Gather short-term conversational context
        ctx = self.context_mgr.get_context(
            stream_id=stream_id,
            max_stream_messages=config.context_window_size,
            max_user_messages=config.user_context_window_size,
        )
        context_str = ctx.get_formatted_context(current_author_id=msg.author_id)

        # 2. Build structured prompt
        personality_str = self.personality_mgr.build_personality_prompt(personality)
        user_prompt = build_cohost_prompt(
            msg=msg,
            personality_prompt=personality_str,
            context_str=context_str,
        )

        # 3. Dispatch AI Request to centralized Gemini Engine (NORMAL priority)
        ai_req = AIRequest(
            stream_id=stream_id,
            source="cohost",
            prompt=user_prompt,
            system_instruction=BASE_COHOST_SYSTEM_INSTRUCTION,
            priority=AIRequestPriority.NORMAL,
            timeout_seconds=8.0,
            temperature=0.7,
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
                latency_ms=latency,
                block_reason=f"AI Request Exception: {exc}",
            )

        latency = (time.time() - start_time) * 1000

        # 4. Handle Gemini AI error / timeout statuses
        if ai_res.status != AIResponseStatus.SUCCESS or not ai_res.text.strip():
            reason = ai_res.error_message or f"AI returned status '{ai_res.status.value}'"
            logger.warning(f"Co-Host Gemini generation unsuccessful for stream '{stream_id}': {reason}")
            return CoHostResponse(
                stream_id=stream_id,
                message_id=msg.message_id,
                author_id=msg.author_id,
                author_name=msg.author_name,
                response_text="",
                status=ResponseStatus.FAILED,
                intent=intent,
                latency_ms=latency,
                model=ai_res.model or "gemini-2.5-flash",
                block_reason=reason,
            )

        # 5. Sanitize and length-cap response (max 200 chars)
        sanitized_text = self._sanitize_response(ai_res.text, max_length=config.max_response_length)

        return CoHostResponse(
            stream_id=stream_id,
            message_id=msg.message_id,
            author_id=msg.author_id,
            author_name=msg.author_name,
            response_text=sanitized_text,
            status=ResponseStatus.APPROVED,
            intent=intent,
            latency_ms=latency,
            model=ai_res.model,
        )


# Global singleton response generator
response_generator = ResponseGenerator()
