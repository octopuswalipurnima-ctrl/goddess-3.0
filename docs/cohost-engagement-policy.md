# Co-Host Engagement & Suppression Policy

## Deterministic Evaluation
Before invoking any Gemini AI model, messages undergo rigorous deterministic evaluation by the `EngagementDecisionEngine`:

1. **Noise Suppression**: Command invocations (`!discord`, `/help`), repetitive character strings (`aaaaaa`), or short single tokens are marked `EngagementResponseType.IGNORE` and discarded without consuming AI tokens.
2. **Direct Mentions**: Mentions containing `@Goddess` or persona names are assigned `priority="HIGH"` and routed to `EngagementResponseType.ANSWER` (if question) or `ACKNOWLEDGE`.
3. **Streamer Questions**: Relevant questions regarding stream setup, game, rank, or schedule are evaluated against `confidence_threshold` ($\ge 0.70$).
4. **Chatter Probability Gating**: Ambient conversational chat is filtered via `response_probability` (default: 0.85) to prevent spamming live chat.
5. **Cooldowns & Rate Limits**:
   - Global Stream Cooldown: 5.0 seconds
   - Per-Viewer Cooldown: 30.0 seconds
   - Max Stream Responses: 12 / minute
   - Max Viewer Responses: 3 / minute window
