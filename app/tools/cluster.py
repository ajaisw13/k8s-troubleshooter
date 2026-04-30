from strands.tools import tool

from app.services.kubernetes import check_cluster as _check_cluster


@tool
def check_cluster() -> str:
    return _check_cluster()
