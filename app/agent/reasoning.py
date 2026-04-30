def build_context(status: str, logs: str, events: str) -> str:
    result = analyze_issue(status, logs, events)
    if result["root_cause"] == "Unknown":
        return ""
    return (
        f"[Pre-analysis] Root cause: {result['root_cause']}. "
        f"Suggested fix: {result['fix']}. "
        f"Validate this with the available tools and provide a detailed response."
    )


def analyze_issue(status: str, logs: str, events: str) -> dict:
    if "CrashLoopBackOff" in status:
        return {
            "root_cause": "Application crash",
            "fix": "Check logs for exceptions and fix code"
        }

    if "ImagePullBackOff" in events:
        return {
            "root_cause": "Image pull failure",
            "fix": "Verify image name and credentials"
        }

    if "OOMKilled" in logs:
        return {
            "root_cause": "Out of memory",
            "fix": "Increase memory limits"
        }

    if "Pending" in status and "Insufficient" in events:
        return {
            "root_cause": "Insufficient cluster resources",
            "fix": "Reduce resource requests or scale cluster"
        }

    return {
        "root_cause": "Unknown",
        "fix": "Investigate logs and events further"
    }
