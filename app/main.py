import logging
import os

from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from app.agent.agent import run_agent
from app.services.kubernetes import KubernetesError, list_pods

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI()

_API_KEY = os.getenv("API_KEY")
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _require_api_key(key: str = Security(_api_key_header)):
    if _API_KEY and key != _API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


class ChatRequest(BaseModel):
    message: str
    pod_name: str | None = None
    include_context: bool = True


@app.get("/pods", dependencies=[Depends(_require_api_key)])
def pods(namespace: str = "default"):
    try:
        return {"pods": list_pods(namespace)}
    except KubernetesError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@app.post("/chat", dependencies=[Depends(_require_api_key)])
def chat(req: ChatRequest):
    logger.info("chat request pod=%s include_context=%s", req.pod_name, req.include_context)
    return run_agent(req.message, pod_name=req.pod_name, include_context=req.include_context)
