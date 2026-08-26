# GODDESS AI 3.0 — HONNEY
> Fresh, Production-Grade YouTube Live AI Co-Host, Adaptive Hindi/Hinglish Moderation Engine, 1v1 Matchmaking Queue, Virtual Store & Economy System.

---

## 1. Overview & Vision

**Goddess AI 3.0** is an autonomous personal AI co-host and moderation system for YouTube Live streaming. Controlled directly through **YouTube Live Chat**, it requires **no web frontend** or complicated dashboard.

### Core Capabilities:
- 🌸 **Honney AI Co-Host**: Context-aware AI persona fluent in Hindi, Hinglish, and English gaming banter, activated on the `"honney"` wake word with 10-message conversational memory.
- 🛡️ **Adaptive Hindi/Hinglish Moderation**: Contextual understanding of friendly banter vs toxicity with automated high-confidence action (≥90%), Human-in-the-Loop (HITL) review queue (40–89%), and RAG-lite adaptive moderation memory.
- 🎮 **1v1 Waiting Queue**: Fully atomic, FIFO live stream matchmaking queue with race-safe `!next1v1` selection.
- 🪙 **Virtual Economy & Store**: XP & coin generation with 60s message cooldowns, configurable leveling formula, virtual store administration (`!addst`, `!editst`, `!chps`, `!delst`), and atomic double-spend protected purchases (`!buy`).
- ⚡ **Nightbot-Style Custom Commands**: Creator/moderator custom commands (`!adduk`, `!deluk`, `!Edituk`, `!reptuk`) with reserved command protection.
- 🔄 **API Key Rotation & Persistent OAuth**: 4-key Gemini pool and 3-key YouTube API pool with automated health tracking, exponential cooldown, and jittered rotation. Single persistent OAuth token manager with concurrency locks.
- 📡 **Multi-Channel & WebSub**: Live stream discovery via WebSub Atom XML push feeds and periodic discovery safety net.

---

## 2. Directory Structure

```
goddess-ai-3/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI lifecycle, health check, WebSub GET/POST
│   ├── config.py         # Pydantic Settings & channels.json loader
│   ├── database.py       # Async SQLAlchemy 2.x engine & sessionmaker
│   ├── models.py         # 13 ORM models with indices & unique constraints
│   ├── youtube.py        # 3-key pool, OAuth manager, API read/write methods
│   ├── gemini.py         # 4-key pool, structured Hindi/Hinglish moderation, Honney
│   ├── moderation.py     # Normalization, RAG-lite memory, review resolution
│   ├── commands.py       # Registry, permission matrix, 1v1 queue, settings
│   ├── economy.py        # XP, leveling formula, store, atomic purchases
│   ├── workers.py        # StreamManager, ChatWorker pipeline, WebSub manager
│   └── utils.py          # Structured logging, secret masking, normalization
├── tests/
│   ├── test_youtube.py
│   ├── test_gemini.py
│   ├── test_moderation.py
│   ├── test_commands.py
│   ├── test_economy.py
│   ├── test_queue.py
│   ├── test_websub.py
│   └── test_concurrency_and_integration.py
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial_schema.py
├── channels.json         # Configured YouTube channels
├── requirements.txt      # Production dependencies
├── .env.example          # Environment variables template
├── Dockerfile            # Container definition
├── railway.json          # Railway deployment configuration
├── alembic.ini           # Migration settings
└── README.md
```

---

## 3. Official YouTube Chat Command Reference

### Custom Commands (Moderator / Broadcaster)
| Command | Usage | Description |
| :--- | :--- | :--- |
| `!adduk` | `!adduk <name> <response>` | Create a custom command (e.g. `!adduk discord Join discord.gg/xyz`) |
| `!deluk` | `!deluk <name>` | Delete an existing custom command |
| `!Edituk` | `!Edituk <name> <response>` | Update an existing custom command's response |
| `!reptuk` | `!reptuk <name>` | Test/repeat the saved response of a custom command |

### 1v1 Waiting Queue
| Command | Perm | Usage | Description |
| :--- | :--- | :--- | :--- |
| `!join` | Viewer | `!join` | Join the active live stream's 1v1 queue (FIFO, duplicate-protected) |
| `!next1v1` | Mod+ | `!next1v1` | Atomically select and announce the next player in the queue |

### Economy & Virtual Store
| Command | Perm | Usage | Description |
| :--- | :--- | :--- | :--- |
| `!coins` | Viewer | `!coins` | View your coin balance, XP, and level |
| `!rank` | Viewer | `!rank` | Display your rank profile |
| `!store` | Viewer | `!store` | View items available for purchase |
| `!buy` | Viewer | `!buy <item>` | Atomically purchase a store item with coins |
| `!addst` | Mod+ | `!addst <item> <price> <desc>` | Add a new item to the store |
| `!delst` | Mod+ | `!delst <item>` | Remove an item from the store |
| `!editst` | Mod+ | `!editst <item> <desc>` | Update item description |
| `!chps` | Mod+ | `!chps <item> <price>` | Change item price |

### Moderation & HITL
| Command | Perm | Usage | Description |
| :--- | :--- | :--- | :--- |
| `!delmsg` | Mod+ | `!delmsg @username` | Delete the latest live chat message from user |
| `!tout` | Mod+ | `!tout @username [seconds]` | Timeout user in live chat (default 300s) |
| `!hid` | Broadcaster | `!hid @username` | Permanently hide user from channel |
| `!mod allow` | Mod+ | `!mod allow <review_id>` | Mark review ALLOWED & save to moderation memory |
| `!mod ban` | Mod+ | `!mod ban <review_id>` | Mark review BANNED & save to moderation memory |
| `!mod ignore`| Mod+ | `!mod ignore <review_id>` | Mark review IGNORED |

### Chat Settings & System
| Command | Perm | Usage | Description |
| :--- | :--- | :--- | :--- |
| `!ghelp` | Viewer | `!ghelp` | Dynamic command help listing |
| `!settings` | Mod+ | `!settings` | Display current channel settings |
| `!setai` | Mod+ | `!setai on\|off` | Toggle AI moderation |
| `!setcohost` | Mod+ | `!setcohost on\|off` | Toggle Honney AI Co-Host |
| `!setmod` | Mod+ | `!setmod relaxed\|balanced\|strict` | Set moderation strictness level |
| `!setpersonality` | Mod+ | `!setpersonality <style>` | Adjust Honney's personality |
| `!setxp` | Mod+ | `!setxp <amount>` | Set XP awarded per chat message |
| `!setcoins` | Mod+ | `!setcoins <amount>` | Set coins awarded per chat message |
| `!setcooldown` | Mod+ | `!setcooldown <seconds>` | Set reward cooldown window |

---

## 4. Setup & Configuration

### Prerequisites
- Python 3.12+
- PostgreSQL database
- Google Cloud Project with YouTube Data API v3 enabled
- Google Gemini API Keys (4 keys recommended)

### Environment Variables (`.env`)
```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/goddess_ai
PORT=8000

# 4 Gemini API Keys
GEMINI_API_KEY_1=your_gemini_key_1
GEMINI_API_KEY_2=your_gemini_key_2
GEMINI_API_KEY_3=your_gemini_key_3
GEMINI_API_KEY_4=your_gemini_key_4

# 3 YouTube Data API Keys (Read-only)
YOUTUBE_API_KEY_1=your_youtube_key_1
YOUTUBE_API_KEY_2=your_youtube_key_2
YOUTUBE_API_KEY_3=your_youtube_key_3

# Google OAuth 2.0 (For authenticated write operations)
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/oauth2callback

YOUTUBE_OAUTH_TOKEN=your_access_token
YOUTUBE_OAUTH_REFRESH_TOKEN=your_refresh_token

# WebSub Stream Detection
WEBSUB_CALLBACK_URL=https://your-domain.up.railway.app/websub/youtube
WEBSUB_SECRET=your_websub_secret

# Optional Discord Alerts for HITL
DISCORD_MOD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### Channels Configuration (`channels.json`)
```json
[
  {
    "channel_id": "UCxxxxxxxxxxxxxxxxxxxxxx",
    "enabled": true,
    "name": "Main Channel"
  }
]
```

---

## 5. Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run database migrations
alembic upgrade head

# 3. Run test suite
pytest -v

# 4. Lint and typecheck
ruff check .
ruff format --check .
mypy app

# 5. Start the application
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 6. Railway Deployment

1. Connect your repository to Railway.
2. Add a PostgreSQL database service in Railway.
3. Configure environment variables in Railway project settings.
4. Deploy — Railway will use `Dockerfile` and `railway.json` to automatically run `alembic upgrade head` and launch the bot.
5. Set `WEBSUB_CALLBACK_URL` to `https://${RAILWAY_PUBLIC_DOMAIN}/websub/youtube`.
