# Creator Knowledge Base & Anti-Hallucination

## Verified Knowledge Categories
The `CreatorKnowledgeManager` maintains stream-scoped structured facts:
- `schedule`: Streaming days and start times
- `socials`: Discord, Twitter/X, YouTube, TikTok links
- `faq`: Creator bio, peripherals, sensitivity, PC hardware
- `rules`: Chat guidelines, self-promotion policies
- `sponsor`: Active discount codes, partners, giveaways

## Anti-Hallucination Policy
- **Zero Fabrication**: If a viewer asks a question regarding an unconfigured fact (e.g. unknown schedule or personal details), the system explicitly forbids guessing.
- **Fail Safe**: The AI prompt explicitly enforces: *"If a viewer asks a fact that is not listed in your verified knowledge, reply that you don't know or that the streamer hasn't announced it yet. Never invent or guess creator details."*
