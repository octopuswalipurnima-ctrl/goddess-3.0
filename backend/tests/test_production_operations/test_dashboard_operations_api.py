"""
Tests for Dashboard Overview & Stream Control REST Operations in GODDESS AI 2.0.
"""

import pytest
from starlette.testclient import TestClient
from app.main import app


def test_dashboard_overview_endpoint_telemetry():
    """Verify GET /api/v1/dashboard/overview returns enriched operational safety & supervisor fields."""
    with TestClient(app) as client:
        response = client.get("/api/v1/dashboard/overview")
        assert response.status_code == 200
        data = response.json()

        assert "system_status" in data
        assert "production_mode" in data
        assert data["production_mode"] is True
        assert "global_safety_state" in data
        assert "supervisor_streams" in data
        assert "safety_summary" in data
        assert data["max_stream_count"] == 4


def test_stream_emergency_stop_endpoints():
    """Verify POST /api/v1/streams/global-emergency-stop and clear-global-emergency-stop."""
    with TestClient(app) as client:
        # Trigger
        resp = client.post("/api/v1/streams/global-emergency-stop", json={"reason": "Test incident"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "EMERGENCY_STOP"

        # Check overview reflects EMERGENCY_STOP
        overview_resp = client.get("/api/v1/dashboard/overview")
        assert overview_resp.json()["global_safety_state"] == "EMERGENCY_STOP"

        # Clear
        clear_resp = client.post("/api/v1/streams/clear-global-emergency-stop")
        assert clear_resp.status_code == 200
        assert clear_resp.json()["status"] == "NORMAL"

        overview_resp = client.get("/api/v1/dashboard/overview")
        assert overview_resp.json()["global_safety_state"] == "NORMAL"
