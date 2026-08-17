# GODDESS AI 2.0 — Incident Response & Emergency Playbook

## 1. Emergency Halt Trigger
When anomalous behavior, chat flood attacks, or prompt injection is detected:
1. Trigger Global Emergency Stop:
   - VIA REST: `POST /api/v1/streams/global-emergency-stop`
   - VIA Dashboard: Click "EMERGENCY STOP" button.
2. System immediately blocks all automated external mutations.
3. Read-only diagnostics and audit logs remain available for root cause analysis.

## 2. Safe Mode Mitigation
If chat traffic has high volatility:
- Enable Safe Mode on affected stream: `POST /api/v1/streams/{stream_id}/safe-mode`
- Moderation continues in DRY_RUN / Log-Only mode; AI Co-Host replies are paused.

## 3. Quota Exhaustion
- YouTube or Gemini credential rotation occurs automatically across configured keys.
- If all keys exhaust quota, provider transitions to `UNAVAILABLE` and system fails closed without crashing.
