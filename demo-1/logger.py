"""
logger.py — Auditable Action Log (Demo 1)

Every proposed action — confirmed or declined, executed or not — is
appended to logs/action_log.jsonl (one JSON object per line, so the log
is append-only and trivially diffable/greppable, which matters for the
Week 15-19 adversarial evaluation that needs to inspect what the
governance layer let through).
"""

import json
import os
from datetime import datetime

LOG_PATH = os.path.join(os.path.dirname(__file__), "logs", "action_log.jsonl")


def log_action(nl_request, command, tier, reason, confirmed, executed,
                rollback_hint=None, execution_result=None):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "nl_request": nl_request,
        "command": command,
        "risk_tier": tier,
        "reason": reason,
        "user_confirmed": confirmed,
        "executed": executed,
        "rollback_hint": rollback_hint,
        "execution_result": execution_result,
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def read_log():
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
