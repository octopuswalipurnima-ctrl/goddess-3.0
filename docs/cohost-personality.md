# Stream-Scoped Persona & Prompt Customization

## Persona Isolation
Each stream (`STREAM_A` through `STREAM_D`) maintains an independent persona configuration. Persona attributes include:
- `name`: Display name of the AI assistant (default: `Goddess`)
- `tone`: `friendly`, `energetic`, `professional`, `casual`, `humorous`
- `energy_level`: `low`, `medium`, `high`
- `humor_level`: `none`, `low`, `moderate`, `high`
- `formality`: `casual`, `polite`, `formal`
- `emoji_usage`: `none`, `minimal`, `moderate`, `expressive`
- `response_style`: `concise`, `conversational`, `enthusiastic`, `informative`
- `custom_instructions`: Creator-specified guidance

## Anti-Injection Safeguards
The `CoHostPersonalityManager` sanitizes `custom_instructions` to prevent prompt injection and policy overrides:
- Strips keywords attempting to ignore previous system instructions.
- Rejects system role tokens and forbidden patterns.
- Always enforces the 200-character upper bound and zero-hallucination policies regardless of custom directives.
