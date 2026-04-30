from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.services.kubernetes import KubernetesError

client = TestClient(app)


# ── GET /pods ──────────────────────────────────────────────────────────────────

class TestPodsEndpoint:
    def test_returns_pod_list(self):
        with patch("app.main.list_pods", return_value=["pod-a", "pod-b"]):
            resp = client.get("/pods")
        assert resp.status_code == 200
        assert resp.json() == {"pods": ["pod-a", "pod-b"]}

    def test_empty_namespace_returns_empty_list(self):
        with patch("app.main.list_pods", return_value=[]):
            resp = client.get("/pods?namespace=empty-ns")
        assert resp.status_code == 200
        assert resp.json() == {"pods": []}

    def test_returns_503_on_kubernetes_error(self):
        with patch("app.main.list_pods", side_effect=KubernetesError("cluster down")):
            resp = client.get("/pods")
        assert resp.status_code == 503
        assert "cluster down" in resp.json()["detail"]

    def test_rejects_invalid_api_key(self, monkeypatch):
        monkeypatch.setattr(main_module, "_API_KEY", "secret")
        with patch("app.main.list_pods", return_value=[]):
            resp = client.get("/pods", headers={"X-API-Key": "wrong"})
        assert resp.status_code == 401

    def test_accepts_valid_api_key(self, monkeypatch):
        monkeypatch.setattr(main_module, "_API_KEY", "secret")
        with patch("app.main.list_pods", return_value=["pod-a"]):
            resp = client.get("/pods", headers={"X-API-Key": "secret"})
        assert resp.status_code == 200

    def test_no_auth_required_when_api_key_not_configured(self, monkeypatch):
        monkeypatch.setattr(main_module, "_API_KEY", None)
        with patch("app.main.list_pods", return_value=[]):
            resp = client.get("/pods")
        assert resp.status_code == 200


# ── POST /chat ─────────────────────────────────────────────────────────────────

class TestChatEndpoint:
    def test_returns_agent_response(self):
        with patch("app.main.run_agent", return_value={"response": "Pod is crashing", "summary": "Check logs"}):
            resp = client.post("/chat", json={"message": "Why is my pod crashing?"})
        assert resp.status_code == 200
        assert resp.json()["response"] == "Pod is crashing"
        assert resp.json()["summary"] == "Check logs"

    def test_passes_pod_name_to_agent(self):
        with patch("app.main.run_agent", return_value={"response": "OOMKilled", "summary": "Increase memory"}) as mock:
            client.post("/chat", json={"message": "Why?", "pod_name": "my-pod"})
        mock.assert_called_once_with("Why?", pod_name="my-pod", include_context=True)

    def test_passes_include_context_false(self):
        with patch("app.main.run_agent", return_value={"response": "ok", "summary": "ok"}) as mock:
            client.post("/chat", json={"message": "hi", "include_context": False})
        mock.assert_called_once_with("hi", pod_name=None, include_context=False)

    def test_rejects_missing_message(self):
        resp = client.post("/chat", json={"pod_name": "my-pod"})
        assert resp.status_code == 422
