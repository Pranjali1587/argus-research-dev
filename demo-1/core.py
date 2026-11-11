"""
core.py — shared pipeline: propose -> classify -> (confirm) -> execute -> log

Both app.py (FastAPI backend, Week 2 deliverable) and main.py (text-based
front-end, Week 6 deliverable) import this module so there is exactly one
implementation of the actual agent logic behind two interfaces.
"""

from __future__ import annotations

import subprocess

from llm_backend import get_backend
from governance import classify_hybrid, RiskTier
from logger import log_action

_backend, _backend_label = get_backend()


def backend_label() -> str:
    return _backend_label


def backend_available() -> bool:
    return _backend.available()


def propose(nl_request: str) -> dict:
    """Turn a natural-language request into a classified command proposal."""
    result = _backend.get_structured_command(nl_request)
    command = result["command"]
    classification = classify_hybrid(command, result.get("risk"))
    return {
        "nl_request": nl_request,
        "command": command,
        "explanation": result.get("explanation"),
        "model_risk": result.get("risk"),
        "risk_tier": classification.tier.value,
        "reason": classification.reason,
        "risk_source": classification.source,
        "rollback_hint": classification.rollback_hint,
        "requires_confirmation": classification.tier == RiskTier.DESTRUCTIVE,
    }


def _run(command: str) -> str:
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        return out if not err else f"{out}\n[stderr] {err}".strip()
    except Exception as e:
        return f"[execution error] {e}"


def execute_and_log(nl_request: str, command: str, risk_tier: str, reason: str,
                     rollback_hint: str | None, confirmed: bool, dry_run: bool = True) -> dict:
    """Execution Layer: runs the command (or dry-runs it) and logs the
    outcome to the auditable action log regardless of the outcome."""
    executed = False
    execution_result = None

    if risk_tier == RiskTier.DESTRUCTIVE.value and not confirmed:
        execution_result = "blocked: destructive action not confirmed"
    elif dry_run:
        execution_result = "dry-run — not actually executed"
    else:
        execution_result = _run(command)
        executed = True

    entry = log_action(
        nl_request, command, risk_tier, reason, confirmed, executed,
        rollback_hint, execution_result,
    )
    return entry
