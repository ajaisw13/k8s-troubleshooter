from fastapi import FastAPI
from pydantic import BaseModel

from app.agent.agent import run_agent
from app.services.kubernetes import list_pods

app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    pod_name: str | None = None
    include_context: bool = True


@app.get("/pods")
def pods(namespace: str = "default"):
    return {"pods": list_pods(namespace)}


@app.post("/chat")
def chat(req: ChatRequest):
    print("request " + str(req))
    return run_agent(req.message, pod_name=req.pod_name, include_context=req.include_context)
