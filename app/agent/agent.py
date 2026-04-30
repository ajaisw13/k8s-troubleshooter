import json

import boto3
from strands import Agent

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.reasoning import build_context
from app.models.bedrock import bedrock_model
from app.services.kubernetes import get_all_pods_status, get_events, get_pod_logs, get_pod_status
from app.tools.cluster import check_cluster
from app.tools.events import get_events as tool_get_events
from app.tools.pod import get_pod_logs as tool_get_pod_logs
from app.tools.pod import get_pod_status as tool_get_pod_status
from app.tools.stackoverflow import search_stackoverflow

# Lazy-initialized so the module can be imported without AWS credentials.
# Both are created on first use inside run_agent / _summarize.
_bedrock = None
_agent: Agent | None = None


def _get_bedrock():
    global _bedrock
    if _bedrock is None:
        _bedrock = boto3.client("bedrock-runtime", region_name="us-west-2")
    return _bedrock


def _get_agent() -> Agent:
    global _agent
    if _agent is None:
        _agent = Agent(
            name="k8s-troubleshooter",
            description="Diagnoses Kubernetes pod issues",
            model=bedrock_model,
            tools=[
                tool_get_pod_status, tool_get_pod_logs, tool_get_events,
                check_cluster, search_stackoverflow,
            ],
            system_prompt=SYSTEM_PROMPT,
        )
    return _agent


def _summarize(text: str) -> str:
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 80,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Summarize the following Kubernetes diagnostic response in 1-2 concise "
                    f"sentences highlighting the key issue and recommended action:\n\n{text}"
                ),
            }
        ],
    }
    resp = _get_bedrock().invoke_model(
        modelId="anthropic.claude-3-5-haiku-20241022-v1:0",
        body=json.dumps(body),
    )
    return json.loads(resp["body"].read())["content"][0]["text"]


def run_agent(user_input: str, pod_name: str = None, include_context: bool = True) -> dict:
    if include_context:
        if pod_name:
            status = get_pod_status(pod_name)
            logs = get_pod_logs(pod_name)
            events = get_events(pod_name)
            context = build_context(status, logs, events)
            user_input = (
                f"Primary pod under investigation: '{pod_name}'\n"
                f"{context}\n\n"
                f"User query: {user_input}"
            )
        else:
            all_status = get_all_pods_status()
            all_events = get_events()
            user_input = (
                f"Namespace-wide pod status:\n{all_status}\n\n"
                f"Recent events:\n{all_events}\n\n"
                f"User query: {user_input}"
            )
    result = _get_agent()(user_input)
    full_text = ""
    for block in result.message.get("content", []):
        if "text" in block:
            full_text = block["text"]
            break
    return {"response": full_text, "summary": _summarize(full_text)}
