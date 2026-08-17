# GODDESS AI 2.0 — Production AI Co-Host 2.0

## 1. Overview & Capabilities

The AI Co-Host provides real-time contextual interaction with live chat viewers during live broadcasts.

Key Capabilities:
1. **Per-Stream Personality & Configuration**:
   - `enabled`, `dry_run`, `cooldown_seconds`, `max_response_length`, `confidence_threshold`, `response_probability`, `allowed_intents`.
2. **Short-Term Conversational Memory**:
   - Rolling stream chat context ($\le 20$ messages).
   - Rolling per-viewer interaction context ($\le 5$ messages).
3. **Fail-Closed Fallback**:
   - If Gemini fails, returns `NO_RESPONSE` without fabricating synthetic replies.
4. **Duplicate Prevention**:
   - Recent response caching prevents repeating the same greeting or answer.
5. **Safety Filtering**:
   - Outgoing replies are scanned for secrets, URLs, toxic phrases, or excessive length.
