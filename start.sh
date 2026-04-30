#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KUBECONFIG_EMBEDDED="$HOME/.kube/config-embedded"

echo "==> Regenerating embedded kubeconfig..."
kubectl config view --raw | python3 "$SCRIPT_DIR/setup_local_kubeconfig.py" > "$KUBECONFIG_EMBEDDED"
echo "    Written to $KUBECONFIG_EMBEDDED"

SERVER=$(python3 -c "
import yaml
c = yaml.safe_load(open('$KUBECONFIG_EMBEDDED'))
ctx_name = c.get('current-context')
ctx = next((x['context'] for x in c['contexts'] if x['name'] == ctx_name), None)
cluster_name = ctx['cluster'] if ctx else c['clusters'][0]['name']
cluster = next(cl['cluster'] for cl in c['clusters'] if cl['name'] == cluster_name)
print(cluster['server'])
")
echo "    Active cluster endpoint: $SERVER"

echo "==> Starting Docker Compose services..."
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up --build -d

echo "==> Waiting for API to be ready..."
for i in $(seq 1 20); do
    if curl -sf http://localhost:8080/pods > /dev/null 2>&1; then
        echo "    API is up."
        break
    fi
    if [ "$i" -eq 20 ]; then
        echo "    API did not become ready in time. Check logs with: docker compose logs api"
        exit 1
    fi
    sleep 2
done

echo ""
echo "Services running:"
echo "  API: http://localhost:8080"
echo "  UI:  http://localhost:8501"
