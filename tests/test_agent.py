from unittest.mock import patch, MagicMock
import pytest

from app.agent.reasoning import analyze_issue
from app.agent.agent import run_agent


# --- analyze_issue unit tests ---

def test_crashloop_detected():
    result = analyze_issue(
        status="CrashLoopBackOff",
        logs="Error: application panic",
        events="",
    )
    assert result["root_cause"] == "Application crash"
    assert "logs" in result["fix"].lower()


def test_image_pull_backoff_detected():
    result = analyze_issue(
        status="Pending",
        logs="",
        events="ImagePullBackOff: failed to pull image",
    )
    assert result["root_cause"] == "Image pull failure"
    assert "image" in result["fix"].lower()


def test_oom_killed_detected():
    result = analyze_issue(
        status="Running",
        logs="OOMKilled: container exceeded memory limit",
        events="",
    )
    assert result["root_cause"] == "Out of memory"
    assert "memory" in result["fix"].lower()


def test_pending_insufficient_resources():
    result = analyze_issue(
        status="Pending",
        logs="",
        events="Insufficient cpu: 0/3 nodes available",
    )
    assert result["root_cause"] == "Insufficient cluster resources"
    assert "resource" in result["fix"].lower()


def test_unknown_fallback():
    result = analyze_issue(
        status="Running",
        logs="",
        events="",
    )
    assert result["root_cause"] == "Unknown"


# --- run_agent integration tests (tools mocked) ---

@patch("app.agent.agent.agent")
def test_run_agent_crashloop(mock_agent):
    mock_agent.return_value = "Pod is in CrashLoopBackOff due to application crash."
    response = run_agent("Why is my pod crashing?")
    mock_agent.assert_called_once_with("Why is my pod crashing?")
    assert response is not None


@patch("app.agent.agent.agent")
def test_run_agent_image_pull(mock_agent):
    mock_agent.return_value = "Pod cannot pull image from private registry."
    response = run_agent("Pod stuck on ImagePullBackOff")
    assert "image" in response.lower()


@patch("app.agent.agent.agent")
def test_run_agent_oom(mock_agent):
    mock_agent.return_value = "Pod was OOMKilled. Increase memory limits."
    response = run_agent("Pod keeps getting killed")
    assert "memory" in response.lower()


@patch("app.agent.agent.agent")
def test_run_agent_pending(mock_agent):
    mock_agent.return_value = "Pod is Pending due to insufficient cluster resources."
    response = run_agent("Pod is stuck in Pending state")
    assert "pending" in response.lower() or "resource" in response.lower()