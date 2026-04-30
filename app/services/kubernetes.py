import os

from kubernetes import client, config
from kubernetes.client.rest import ApiException
from urllib3.exceptions import MaxRetryError

NAMESPACE = os.getenv("K8S_NAMESPACE", "default")

# Cached after first call — in-cluster vs kubeconfig doesn't change at runtime
_in_cluster: bool | None = None


class KubernetesError(Exception):
    pass


def _load_config():
    global _in_cluster
    if _in_cluster is None:
        try:
            config.load_incluster_config()
            _in_cluster = True
            return
        except config.ConfigException:
            _in_cluster = False
    if not _in_cluster:
        # Re-read every call: picks up minikube port changes after restart,
        # and lets EKS/GKE exec plugins refresh tokens on their own schedule.
        config.load_kube_config()


def list_pods(namespace: str = NAMESPACE) -> list[str]:
    _load_config()
    v1 = client.CoreV1Api()
    try:
        pods = v1.list_namespaced_pod(namespace=namespace)
        return [p.metadata.name for p in pods.items]
    except ApiException as e:
        raise KubernetesError(f"Failed to list pods in '{namespace}': {e.reason} (HTTP {e.status})")
    except MaxRetryError:
        raise KubernetesError(
            "Cannot reach Kubernetes API server — is the cluster running and kubeconfig up to date?"
        )


def get_all_pods_status() -> str:
    _load_config()
    v1 = client.CoreV1Api()
    try:
        pods = v1.list_namespaced_pod(namespace=NAMESPACE)
        if not pods.items:
            return "No pods found in namespace."
        return "\n\n".join(_format_pod_status(p) for p in pods.items)
    except ApiException as e:
        return f"Error fetching pods: {e.reason} (HTTP {e.status})"
    except MaxRetryError:
        return "Error: cannot reach Kubernetes API server — is the cluster running?"


def get_pod_status(pod_name: str) -> str:
    _load_config()
    v1 = client.CoreV1Api()
    try:
        pod = v1.read_namespaced_pod(name=pod_name, namespace=NAMESPACE)
        return _format_pod_status(pod)
    except ApiException as e:
        return f"Error fetching pod '{pod_name}': {e.reason} (HTTP {e.status})"
    except MaxRetryError:
        return "Error: cannot reach Kubernetes API server — is the cluster running?"


def get_pod_logs(pod_name: str) -> str:
    _load_config()
    v1 = client.CoreV1Api()
    try:
        return v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=NAMESPACE,
            tail_lines=100,
        )
    except ApiException as e:
        return f"Error fetching logs for '{pod_name}': {e.reason} (HTTP {e.status})"
    except MaxRetryError:
        return "Error: cannot reach Kubernetes API server — is the cluster running?"


def get_events(pod_name: str = None) -> str:
    _load_config()
    v1 = client.CoreV1Api()
    try:
        kwargs = {"namespace": NAMESPACE}
        if pod_name:
            kwargs["field_selector"] = f"involvedObject.name={pod_name},involvedObject.kind=Pod"
        events = v1.list_namespaced_event(**kwargs)
        sorted_events = sorted(
            events.items,
            key=lambda e: e.metadata.creation_timestamp or "",
        )
        lines = [
            f"{e.last_timestamp} [{e.type}] {e.involved_object.name}: {e.message}"
            for e in sorted_events
        ]
        return "\n".join(lines) if lines else "No events found."
    except ApiException as e:
        return f"Error fetching events: {e.reason} (HTTP {e.status})"
    except MaxRetryError:
        return "Error: cannot reach Kubernetes API server — is the cluster running?"


def check_cluster() -> str:
    _load_config()
    try:
        version = client.VersionApi().get_code()
        nodes = client.CoreV1Api().list_node()
        node_summary = ", ".join(
            f"{n.metadata.name} ({_node_status(n)})"
            for n in nodes.items
        )
        return (
            f"Kubernetes {version.git_version} | Platform: {version.platform}\n"
            f"Nodes: {node_summary}"
        )
    except ApiException as e:
        return f"Error checking cluster: {e.reason} (HTTP {e.status})"
    except MaxRetryError:
        return "Error: cannot reach Kubernetes API server — is the cluster running?"


def _node_status(node) -> str:
    for condition in node.status.conditions or []:
        if condition.type == "Ready":
            return "Ready" if condition.status == "True" else "NotReady"
    return "Unknown"


def _format_pod_status(pod) -> str:
    name = pod.metadata.name
    namespace = pod.metadata.namespace
    phase = pod.status.phase
    pod_ip = pod.status.pod_ip or "N/A"
    node = pod.spec.node_name or "N/A"

    conditions = ", ".join(
        f"{c.type}={c.status}"
        for c in (pod.status.conditions or [])
    )

    containers = []
    for cs in pod.status.container_statuses or []:
        if cs.state.running:
            state = "running"
            detail = ""
        elif cs.state.terminated:
            state = "terminated"
            detail = f"exit={cs.state.terminated.exit_code}"
        else:
            state = "waiting"
            detail = cs.state.waiting.reason or ""
        containers.append(f"{cs.name}: {state} {detail}".strip())

    return (
        f"Name: {name} | Namespace: {namespace} | Phase: {phase}\n"
        f"Node: {node} | Pod IP: {pod_ip}\n"
        f"Conditions: {conditions}\n"
        f"Containers: {', '.join(containers)}"
    )
