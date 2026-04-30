from strands.tools import tool

from app.services.stackoverflow import search_stackoverflow as _search


@tool
def search_stackoverflow(query: str) -> str:
    """Search Stack Overflow for Kubernetes-related solutions to errors or issues."""
    return _search(query)
