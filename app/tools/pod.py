from strands.tools import tool
from app.services.kubernetes import get_pod_status as _get_pod_status, get_pod_logs as _get_pod_logs


@tool
def get_pod_status(pod_name: str) -> str:
    return _get_pod_status(pod_name)


@tool
def get_pod_logs(pod_name: str) -> str:
    return _get_pod_logs(pod_name)
