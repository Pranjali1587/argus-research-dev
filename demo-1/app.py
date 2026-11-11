"""
app.py — ARGUS FastAPI backend (Week 2 / Week 4 deliverable)

Run:
    uvicorn app:app --reload
    then open http://127.0.0.1:8000 for the themed GUI console,
    or http://127.0.0.1:8000/docs for the raw API (Swagger UI).

Endpoints:
    GET  /         themed GUI console (static/index.html)
    GET  /status   backend/model availability, for the GUI's status pill
    POST /command   {"request": "delete the temp folder"} -> proposal + risk classification
    POST /execute    proposal fields + {"confirmed": bool, "dry_run": bool} -> execution result + log entry
    GET  /log        full auditable action log
"""

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

import core
from logger import read_log

app = FastAPI(
    title="ARGUS Backend",
    description="Adaptive Reasoning & Governance framework — Demo 1 backend agent",
    version="0.1.0",
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class CommandRequest(BaseModel):
    request: str


class ExecuteRequest(BaseModel):
    nl_request: str
    command: str
    risk_tier: str
    reason: str
    rollback_hint: Optional[str] = None
    confirmed: bool = False
    dry_run: bool = True


@app.get("/")
def gui():
    """Themed GUI console — the main demo entry point."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/status")
def status():
    return {"backend": core.backend_label(), "ollama_available": core.backend_available()}


@app.post("/command")
def command(req: CommandRequest):
    """Reasoning & Planning Layer + Governance Layer: propose and classify."""
    return core.propose(req.request)


@app.post("/execute")
def execute(req: ExecuteRequest):
    """Execution Layer: run (or dry-run) a previously proposed command and log it."""
    return core.execute_and_log(
        req.nl_request, req.command, req.risk_tier, req.reason,
        req.rollback_hint, req.confirmed, req.dry_run,
    )


@app.get("/log")
def log():
    return read_log()
