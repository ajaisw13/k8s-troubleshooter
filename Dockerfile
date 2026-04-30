FROM python:3.11-slim

WORKDIR /app

# Install auth plugins required by EKS and GKE exec credential providers
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates gnupg \
    && pip install --no-cache-dir awscli \
    && curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
        | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
        > /etc/apt/sources.list.d/google-cloud-sdk.list \
    && apt-get update && apt-get install -y --no-install-recommends \
        google-cloud-sdk-gke-gcloud-auth-plugin \
    && rm -rf /var/lib/apt/lists/*

# Required for gke-gcloud-auth-plugin to be used by kubectl / k8s client
ENV USE_GKE_GCLOUD_AUTH_PLUGIN=True

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
