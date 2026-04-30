from unittest.mock import MagicMock, patch

from app.agent.agent import run_agent
from app.agent.reasoning import analyze_issue

# ── analyze_issue ──────────────────────────────────────────────────────────────

def test_crashloop_detected():
    result = analyze_issue(status="CrashLoopBackOff", logs="Error: application panic", events="")
    assert result["root_cause"] == "Application crash"
    assert "logs" in result["fix"].lower()


def test_image_pull_backoff_detected():
    result = analyze_issue(
        status="Pending", logs="", events="ImagePullBackOff: failed to pull image"
    )
    assert result["root_cause"] == "Image pull failure"
    assert "image" in result["fix"].lower()


def test_oom_killed_detected():
    result = analyze_issue(
        status="Running", logs="OOMKilled: container exceeded memory limit", events=""
    )
    assert result["root_cause"] == "Out of memory"
    assert "memory" in result["fix"].lower()


def test_pending_insufficient_resources():
    result = analyze_issue(
        status="Pending", logs="", events="Insufficient cpu: 0/3 nodes available"
    )
    assert result["root_cause"] == "Insufficient cluster resources"
    assert "resource" in result["fix"].lower()


def test_unknown_fallback():
    result = analyze_issue(status="Running", logs="", events="")
    assert result["root_cause"] == "Unknown"


# ── run_agent ──────────────────────────────────────────────────────────────────
# Use include_context=False to skip live Kubernetes calls.
# Patch _get_agent and _summarize to avoid AWS/Bedrock dependencies.

def _agent_result(text: str) -> MagicMock:
    result = MagicMock()
    result.message = {"content": [{"text": text}]}
    return result


@patch("app.agent.agent._summarize", return_value="summary text")
@patch("app.agent.agent._get_agent")
def test_run_agent_returns_response_and_summary(mock_get_agent, mock_summarize):
    mock_get_agent.return_value.return_value = _agent_result("Pod is in CrashLoopBackOff.")
    result = run_agent("Why is my pod crashing?", include_context=False)
    assert result["response"] == "Pod is in CrashLoopBackOff."
    assert result["summary"] == "summary text"


@patch("app.agent.agent._summarize", return_value="summary")
@patch("app.agent.agent._get_agent")
def test_run_agent_passes_user_input(mock_get_agent, mock_summarize):
    mock_get_agent.return_value.return_value = _agent_result("ok")
    run_agent("check image pull error", include_context=False)
    mock_get_agent.return_value.assert_called_once_with("check image pull error")


@patch("app.agent.agent._summarize", return_value="summary")
@patch("app.agent.agent._get_agent")
def test_run_agent_with_pod_context(mock_get_agent, mock_summarize):
    mock_get_agent.return_value.return_value = _agent_result("OOMKilled")
    with patch("app.agent.agent.get_pod_status", return_value="Running"), \
         patch("app.agent.agent.get_pod_logs", return_value="OOMKilled"), \
         patch("app.agent.agent.get_events", return_value=""), \
         patch("app.agent.agent.build_context", return_value="[Pre-analysis] OOM"):
        result = run_agent("Why is it crashing?", pod_name="my-pod", include_context=True)
    assert result["response"] == "OOMKilled"
    call_arg = mock_get_agent.return_value.call_args[0][0]
    assert "my-pod" in call_arg
    assert "[Pre-analysis]" in call_arg


@patch("app.agent.agent._summarize", return_value="summary")
@patch("app.agent.agent._get_agent")
def test_run_agent_empty_content_returns_empty_response(mock_get_agent, mock_summarize):
    result_mock = MagicMock()
    result_mock.message = {"content": []}
    mock_get_agent.return_value.return_value = result_mock
    result = run_agent("hello", include_context=False)
    assert result["response"] == ""
