from strands.tools import tool

from app.services.kubernetes import get_events as _get_events


@tool
def get_events(pod_name: str = None) -> str:
    """Fetch Kubernetes events. Pass pod_name to filter events for a specific pod."""
    return _get_events(pod_name=pod_name)
