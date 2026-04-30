from unittest.mock import MagicMock, patch

import pytest
from kubernetes.client.rest import ApiException
from urllib3.exceptions import MaxRetryError

import app.services.kubernetes as k8s_module
from app.services.kubernetes import (
    KubernetesError,
    check_cluster,
    get_events,
    get_pod_logs,
    get_pod_status,
    list_pods,
)


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    """Skip real config loading and reset in-cluster cache between tests."""
    monkeypatch.setattr(k8s_module, "_in_cluster", False)
    monkeypatch.setattr(k8s_module, "_load_config", lambda: None)


def _make_pod(name, namespace="default", phase="Running"):
    pod = MagicMock()
    pod.metadata.name = name
    pod.metadata.namespace = namespace
    pod.status.phase = phase
    pod.status.pod_ip = "10.0.0.1"
    pod.spec.node_name = "node-1"
    pod.status.conditions = []
    pod.status.container_statuses = []
    return pod


# ── list_pods ─────────────────────────────────────────────────────────────────

class TestListPods:
    def test_returns_pod_names(self):
        resp = MagicMock()
        resp.items = [_make_pod("pod-a"), _make_pod("pod-b")]
        with patch("app.services.kubernetes.client.CoreV1Api") as api:
            api.return_value.list_namespaced_pod.return_value = resp
            assert list_pods() == ["pod-a", "pod-b"]

    def test_empty_namespace(self):
        resp = MagicMock()
        resp.items = []
        with patch("app.services.kubernetes.client.CoreV1Api") as api:
            api.return_value.list_namespaced_pod.return_value = resp
            assert list_pods() == []

    def test_raises_on_api_exception(self):
        with patch("app.services.kubernetes.client.CoreV1Api") as api:
            api.return_value.list_namespaced_pod.side_effect = ApiException(
                status=403, reason="Forbidden"
            )
            with pytest.raises(KubernetesError, match="403"):
                list_pods()

    def test_raises_on_connection_failure(self):
        with patch("app.services.kubernetes.client.CoreV1Api") as api:
            api.return_value.list_namespaced_pod.side_effect = MaxRetryError(
                pool=None, url="/"
            )
            with pytest.raises(KubernetesError, match="Cannot reach"):
                list_pods()


# ── get_pod_status ─────────────────────────────────────────────────────────────

class TestGetPodStatus:
    def test_returns_formatted_status(self):
        with patch("app.services.kubernetes.client.CoreV1Api") as api:
            api.return_value.read_namespaced_pod.return_value = _make_pod("my-pod")
            result = get_pod_status("my-pod")
        assert "my-pod" in result
        assert "Running" in result

    def test_error_string_on_not_found(self):
        with patch("app.services.kubernetes.client.CoreV1Api") as api:
            api.return_value.read_namespaced_pod.side_effect = ApiException(
                status=404, reason="Not Found"
            )
            result = get_pod_status("missing")
        assert "Error" in result
        assert "404" in result

    def test_error_string_on_connection_failure(self):
        with patch("app.services.kubernetes.client.CoreV1Api") as api:
            api.return_value.read_namespaced_pod.side_effect = MaxRetryError(
                pool=None, url="/"
            )
            result = get_pod_status("my-pod")
        assert "cannot reach" in result.lower()


# ── get_pod_logs ───────────────────────────────────────────────────────────────

class TestGetPodLogs:
    def test_returns_log_output(self):
        with patch("app.services.kubernetes.client.CoreV1Api") as api:
            api.return_value.read_namespaced_pod_log.return_value = "line1\nline2"
            assert get_pod_logs("my-pod") == "line1\nline2"

    def test_error_string_on_failure(self):
        with patch("app.services.kubernetes.client.CoreV1Api") as api:
            api.return_value.read_namespaced_pod_log.side_effect = ApiException(
                status=500, reason="Internal Server Error"
            )
            result = get_pod_logs("my-pod")
        assert "Error" in result
        assert "500" in result


# ── get_events ─────────────────────────────────────────────────────────────────

class TestGetEvents:
    def _make_event(self, pod_name="my-pod", msg="Back-off restarting"):
        e = MagicMock()
        e.last_timestamp = "2024-01-01T00:00:00Z"
        e.type = "Warning"
        e.involved_object.name = pod_name
        e.message = msg
        e.metadata.creation_timestamp = "2024-01-01T00:00:00Z"
        return e

    def test_returns_formatted_events(self):
        resp = MagicMock()
        resp.items = [self._make_event()]
        with patch("app.services.kubernetes.client.CoreV1Api") as api:
            api.return_value.list_namespaced_event.return_value = resp
            result = get_events("my-pod")
        assert "Warning" in result
        assert "my-pod" in result

    def test_no_events_message_when_empty(self):
        resp = MagicMock()
        resp.items = []
        with patch("app.services.kubernetes.client.CoreV1Api") as api:
            api.return_value.list_namespaced_event.return_value = resp
            assert get_events() == "No events found."

    def test_filters_by_pod_name(self):
        resp = MagicMock()
        resp.items = []
        with patch("app.services.kubernetes.client.CoreV1Api") as api:
            api.return_value.list_namespaced_event.return_value = resp
            get_events("my-pod")
            _, kwargs = api.return_value.list_namespaced_event.call_args
            assert "my-pod" in kwargs.get("field_selector", "")


# ── check_cluster ──────────────────────────────────────────────────────────────

class TestCheckCluster:
    def test_returns_cluster_info(self):
        version = MagicMock(git_version="v1.28.0", platform="linux/amd64")
        node = MagicMock()
        node.metadata.name = "node-1"
        node.status.conditions = [MagicMock(type="Ready", status="True")]
        nodes = MagicMock()
        nodes.items = [node]

        with patch("app.services.kubernetes.client.VersionApi") as ver_api, \
             patch("app.services.kubernetes.client.CoreV1Api") as core_api:
            ver_api.return_value.get_code.return_value = version
            core_api.return_value.list_node.return_value = nodes
            result = check_cluster()

        assert "v1.28.0" in result
        assert "node-1" in result
        assert "Ready" in result

    def test_not_ready_node(self):
        version = MagicMock(git_version="v1.28.0", platform="linux/amd64")
        node = MagicMock()
        node.metadata.name = "node-1"
        node.status.conditions = [MagicMock(type="Ready", status="False")]
        nodes = MagicMock()
        nodes.items = [node]

        with patch("app.services.kubernetes.client.VersionApi") as ver_api, \
             patch("app.services.kubernetes.client.CoreV1Api") as core_api:
            ver_api.return_value.get_code.return_value = version
            core_api.return_value.list_node.return_value = nodes
            result = check_cluster()

        assert "NotReady" in result
