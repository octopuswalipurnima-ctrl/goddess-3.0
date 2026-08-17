# GODDESS AI 2.0 — Controlled Real-Service Testing Protocol

## 1. Safety Rules for Real External APIs

1. **Explicit Operator Opt-In Only**: Real external API tests are skipped during automated CI/CD runs unless explicit environment variables are provided.
2. **Private/Unlisted Stream Requirement**: Never execute automated tests against live production or public streams. Always use an unlisted testing broadcast.
3. **Zero Secret Persistence**: Never commit API keys or OAuth secrets into test files or version control.

---

## 2. Running Controlled Real Gemini Tests

```powershell
$env:RUN_REAL_GEMINI_TEST="true"
$env:GEMINI_API_KEY_1="AIzaSyYourRealGeminiKeyHere"
pytest -v tests/test_real_integrations/test_gemini_integration_audit.py
```

### Verification Points:
- Successful round-trip text generation via `gemini-2.5-flash`.
- Token accounting incremented in metrics.
- Zero credential exposure in return models or logs.

---

## 3. Running Controlled Real YouTube Tests

```powershell
$env:RUN_REAL_YOUTUBE_TEST="true"
$env:YOUTUBE_API_KEY_1="AIzaSyYourRealYouTubeKeyHere"
$env:TEST_YOUTUBE_STREAM_ID="your_unlisted_stream_id"
python backend/app/services/youtube/manual_test.py
```

### Verification Points:
- Resolves active broadcast and extracts `activeLiveChatId`.
- Reads incoming messages via polling reader.
- Deduplication prevents duplicate message re-broadcasts.
- Clean session teardown on manual termination (`Ctrl+C`).
