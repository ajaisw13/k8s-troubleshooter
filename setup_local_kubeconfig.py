import base64
import sys
import yaml


def _read_file_as_b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _is_local(server: str) -> bool:
    return "127.0.0.1" in server or "localhost" in server


c = yaml.safe_load(sys.stdin)

for cl in c.get("clusters", []):
    cluster = cl["cluster"]
    server = cluster.get("server", "")
    if _is_local(server):
        # Local cluster: Docker can't reach 127.0.0.1 — rewrite host and skip TLS.
        cluster.pop("certificate-authority-data", None)
        cluster.pop("certificate-authority", None)
        cluster["insecure-skip-tls-verify"] = True
        cluster["server"] = (
            server.replace("127.0.0.1", "host.docker.internal")
                  .replace("localhost", "host.docker.internal")
        )
    # Cloud clusters (EKS, GKE): leave server and TLS config untouched.

for u in c.get("users", []):
    user = u.get("user") or {}
    # Embed file-path certs as inline base64 so they survive inside the container.
    if "client-certificate" in user:
        user["client-certificate-data"] = _read_file_as_b64(user.pop("client-certificate"))
    if "client-key" in user:
        user["client-key-data"] = _read_file_as_b64(user.pop("client-key"))

print(yaml.dump(c))
