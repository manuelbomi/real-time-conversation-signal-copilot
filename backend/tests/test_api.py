"""End-to-end API tests using FastAPI's TestClient, which runs the real
`lifespan` (so the real HashingEmbedder-backed KB store gets built) but
with LLM_PROVIDER left at its default "mock" -- no network calls happen.
"""

import json

from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_metrics_endpoint_exposes_prometheus_text():
    with TestClient(app) as client:
        response = client.get("/metrics")
        assert response.status_code == 200
        assert b"copilot_" in response.content


def test_create_session_returns_id():
    with TestClient(app) as client:
        response = client.post("/sessions")
        assert response.status_code == 200
        assert "session_id" in response.json()


def test_websocket_full_round_trip():
    with TestClient(app) as client:
        session_id = client.post("/sessions").json()["session_id"]
        with client.websocket_connect(f"/ws/sessions/{session_id}") as ws:
            ws.send_text(
                json.dumps(
                    {
                        "speaker": "customer",
                        "text": "This is too expensive, I'm hesitant to sign up.",
                        "ts": 0.0,
                        "is_final": True,
                    }
                )
            )
            first_event = json.loads(ws.receive_text())
            assert first_event["type"] == "signal"
            assert "OBJECTION" in first_event["labels"]


def test_websocket_ignores_interim_partials():
    with TestClient(app) as client:
        session_id = client.post("/sessions").json()["session_id"]
        with client.websocket_connect(f"/ws/sessions/{session_id}") as ws:
            ws.send_text(
                json.dumps(
                    {
                        "speaker": "customer",
                        "text": "part",
                        "ts": 0.0,
                        "is_final": False,
                    }
                )
            )
            ws.send_text(
                json.dumps(
                    {
                        "speaker": "customer",
                        "text": "Sounds good, thanks.",
                        "ts": 1.0,
                        "is_final": True,
                    }
                )
            )
            # Only the final utterance should produce a response.
            first_event = json.loads(ws.receive_text())
            assert first_event["type"] == "signal"
            assert first_event["utterance"] == "Sounds good, thanks."


def test_websocket_malformed_frame_returns_error_event():
    with TestClient(app) as client:
        session_id = client.post("/sessions").json()["session_id"]
        with client.websocket_connect(f"/ws/sessions/{session_id}") as ws:
            ws.send_text("not valid json at all")
            event = json.loads(ws.receive_text())
            assert event["type"] == "error"
