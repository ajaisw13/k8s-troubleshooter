# ⎈ K8s Troubleshooter

[![CI](https://github.com/ajaisw13/k8s-troubleshooter/actions/workflows/ci.yml/badge.svg)](https://github.com/ajaisw13/k8s-troubleshooter/actions/workflows/ci.yml)

An AI-powered Kubernetes diagnostic agent. Describe a problem in plain English — the agent fetches pod status, logs, and events from your cluster, reasons over them using Claude on AWS Bedrock, and returns a root cause with a suggested fix.

![demo placeholder — replace with a screen recording](docs/demo.gif)

---

## How it works

```
Streamlit UI  ──▶  FastAPI backend  ──▶  Strands Agent (Claude via Bedrock)
                        │                        │
                        ▼                        ▼
                 Kubernetes API          Tools: pod status, logs,
                 (minikube / EKS / GKE)  events, Stack Overflow search
```

1. The UI fetches the live pod list and lets you scope the conversation to a specific pod or the whole namespace.
2. On each question the backend pre-fetches pod status, logs, and events and injects them as context.
3. The Strands agent calls tools iteratively until it identifies a root cause, then returns a summary and full diagnostic.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | |
| Docker + Docker Compose | |
| AWS account | Bedrock access for `anthropic.claude-3-5-haiku-20241022-v1:0` in `us-west-2` |
| A Kubernetes cluster | minikube, kind, EKS, or GKE |

---

## Quickstart

### Local cluster (minikube / kind)

```bash
# 1. Start your cluster
minikube start

# 2. Copy and fill in credentials
cp .env.example .env

# 3. Build the embedded kubeconfig and start services
./start.sh
```

`start.sh` rewrites `127.0.0.1` → `host.docker.internal` and embeds all certificates inline so the Docker container can reach the host's cluster.

### EKS

```bash
# Authenticate and update your kubeconfig
aws eks update-kubeconfig --region us-west-2 --name <cluster-name>

cp .env.example .env          # set K8S_NAMESPACE, API_KEY, etc.
docker compose up --build -d
```

### GKE

```bash
gcloud container clusters get-credentials <cluster-name> --region <region>

cp .env.example .env
docker compose up --build -d
```

For EKS and GKE the container mounts `~/.aws` and `~/.config/gcloud` respectively, and ships the `aws` CLI and `gke-gcloud-auth-plugin` so exec credential plugins work inside Docker.

Once running, open:
- **UI** → http://localhost:8501
- **API docs** → http://localhost:8080/docs

---

## Configuration

Copy `.env.example` to `.env` and adjust:

```bash
K8S_NAMESPACE=default        # namespace to inspect
API_KEY=your-secret-key      # optional — protects the API with X-API-Key header
AWS_DEFAULT_REGION=us-west-2
```

---

## Test scenarios

Apply a broken workload to see the agent in action:

```bash
# CrashLoopBackOff
kubectl apply -f scenarios/crashloop.yaml

# ImagePullBackOff
kubectl apply -f scenarios/imagepull.yaml

# OOMKilled
kubectl apply -f scenarios/oom.yaml

# Pending (insufficient resources)
kubectl apply -f scenarios/pending.yaml
```

Then open the UI, select the failing pod, and ask: *"Why is this pod not running?"*

---

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/pods?namespace=default` | List pods in a namespace |
| `POST` | `/chat` | Run the diagnostic agent |

**POST /chat** request body:
```json
{
  "message": "Why is my pod crashing?",
  "pod_name": "my-pod",
  "include_context": true
}
```

If `API_KEY` is set, pass it as `X-API-Key: <key>` on every request.

---

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v --cov=app

# Lint
ruff check .
```

Tests mock the Kubernetes client and Bedrock — no live cluster or AWS credentials needed.
