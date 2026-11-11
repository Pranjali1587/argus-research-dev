"""
governance.py — ARGUS Risk-Governance Layer

Hybrid classification: the LLM self-reports a risk label as part of its
structured JSON output (see llm_backend.py), and this module cross-validates
that self-report against an explicit rule table. Rule-based DESTRUCTIVE
matches always win (a model can't talk its way out of an rm -rf), but for
commands with no rule match, the model's self-reported risk is trusted.
This is the "model-proposed risk label + rule-based override for
known-destructive patterns" design from Week 3 of the project plan.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from enum import Enum


class RiskTier(str, Enum):
    SAFE = "SAFE"
    REVERSIBLE = "REVERSIBLE"
    DESTRUCTIVE = "DESTRUCTIVE"


@dataclass
class Classification:
    tier: RiskTier
    reason: str
    rollback_hint: str | None = None
    source: str = "rule"  # "rule", "model", or "fallback"


DESTRUCTIVE_PATTERNS = [
    (r"\brm\s+.*-[a-zA-Z]*r[a-zA-Z]*f\b", "recursive force-delete (rm -rf family)"),
    (r"\brm\s+.*-[a-zA-Z]*f[a-zA-Z]*r\b", "recursive force-delete (rm -fr family)"),
    (r"\bmkfs(\.\w+)?\b", "formats a filesystem, destroys all data on the target"),
    (r"\bdd\s+.*of=/dev/", "raw disk write via dd — can overwrite an entire disk"),
    (r":\(\)\s*\{\s*:\|:&\s*\};\s*:", "fork bomb"),
    (r"\bshutdown\b|\breboot\b|\bhalt\b|\bpoweroff\b", "shuts down or restarts the system"),
    (r"\bchmod\s+-R\s+000\b|\bchmod\s+-R\s+777\s+/\b", "recursive permission change on root-level path"),
    (r"\bchown\s+-R\b.*\s/\s*$", "recursive ownership change on root"),
    (r">\s*/dev/sd[a-z]\b", "direct write / overwrite of a raw block device"),
    (r"\bdrop\s+(table|database)\b", "irreversible database drop"),
    (r"\btruncate\s+table\b", "irreversible table truncation"),
    (r"\biptables\s+-F\b", "flushes all firewall rules"),
    (r"\buserdel\b|\bdeluser\b", "deletes a system user account"),
    (r"\bkill\s+-9\s+1\b|\bkill\s+-9\s+-1\b", "kills init or all processes"),
    (r"\brm\s+.*/\*\s*$", "wildcard delete at a directory root"),
    (r"\bgit\s+push\s+.*--force\b", "force-push can overwrite remote history irreversibly"),
    (r">\s*[\w./]+", "output redirection can silently overwrite an existing file"),
]

REVERSIBLE_PATTERNS = [
    (r"^\s*rm\s+(?!.*-[a-zA-Z]*r)", "single-file delete (no -r) — recoverable from trash/backup if configured"),
    (r"^\s*mv\s+", "moves/renames a file — can be undone by moving it back"),
    (r"^\s*cp\s+.*-r\b", "recursive copy — undo by removing the copy"),
    (r"^\s*chmod\s+", "permission change — original mode should be recorded before applying"),
    (r"^\s*chown\s+", "ownership change — original owner should be recorded before applying"),
    (r"^\s*mkdir\s+", "creates a directory — undo with rmdir if empty"),
    (r"^\s*touch\s+", "creates an empty file — undo by deleting it"),
    (r"^\s*systemctl\s+(stop|disable)\b", "stops/disables a service — can be re-enabled"),
    (r"^\s*git\s+commit\b", "commit — undo with git reset"),
    (r"^\s*apt(-get)?\s+remove\b|\bpip\s+uninstall\b", "package removal — reinstallable"),
]

SAFE_PATTERNS = [
    r"^\s*ls\b", r"^\s*cat\b", r"^\s*grep\b", r"^\s*find\b(?!.*-delete)",
    r"^\s*ps\b", r"^\s*top\b", r"^\s*df\b", r"^\s*du\b", r"^\s*whoami\b",
    r"^\s*pwd\b", r"^\s*echo\b(?!.*>)", r"^\s*head\b", r"^\s*tail\b", r"^\s*wc\b",
    r"^\s*which\b", r"^\s*man\b", r"^\s*history\b", r"^\s*uname\b",
    r"^\s*systemctl\s+status\b", r"^\s*git\s+(status|log|diff|branch)\b",
]

_TIER_ORDER = {RiskTier.SAFE: 0, RiskTier.REVERSIBLE: 1, RiskTier.DESTRUCTIVE: 2}


def rule_based_classify(command: str) -> Classification | None:
    """Return a Classification if a rule fires, else None (no opinion)."""
    cmd = command.strip()
    if not cmd:
        return Classification(RiskTier.SAFE, "empty command")

    for pattern, reason in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return Classification(RiskTier.DESTRUCTIVE, reason, source="rule")

    for pattern, reason in REVERSIBLE_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return Classification(RiskTier.REVERSIBLE, reason, _suggest_rollback(cmd), source="rule")

    for pattern in SAFE_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return Classification(RiskTier.SAFE, "read-only / informational command", source="rule")

    return None


def classify_hybrid(command: str, model_risk: str | None) -> Classification:
    """
    Combine the rule table with the model's self-reported risk label.
    Rule-based DESTRUCTIVE always wins (safety-critical, non-negotiable).
    Otherwise: if the rules recognize the command, trust the rules, unless
    the model claims an even higher risk (fail cautiously). If the rules
    have no opinion at all, fall back to the model's self-report.
    """
    rule_result = rule_based_classify(command)

    if rule_result and rule_result.tier == RiskTier.DESTRUCTIVE:
        return rule_result  # rules override the model, never the other way

    if rule_result:
        model_tier = _parse_model_tier(model_risk)
        if model_tier and _TIER_ORDER[model_tier] > _TIER_ORDER[rule_result.tier]:
            return Classification(
                model_tier,
                f"model flagged higher risk than rule table ({rule_result.reason})",
                rule_result.rollback_hint,
                source="model",
            )
        return rule_result

    model_tier = _parse_model_tier(model_risk)
    if model_tier:
        return Classification(
            model_tier, "model self-report (no rule match)", _suggest_rollback(command), source="model"
        )
    return Classification(
        RiskTier.REVERSIBLE,
        "unrecognized command, no usable model risk label — defaulting to caution",
        None,
        source="fallback",
    )


def _parse_model_tier(model_risk):
    if not model_risk:
        return None
    key = model_risk.strip().upper()
    if key == "SAFE":
        return RiskTier.SAFE
    if key == "REVERSIBLE":
        return RiskTier.REVERSIBLE
    if key == "DESTRUCTIVE":
        return RiskTier.DESTRUCTIVE
    return None


def _suggest_rollback(cmd: str):
    try:
        parts = shlex.split(cmd)
    except ValueError:
        return None
    if not parts:
        return None
    if parts[0] == "mv" and len(parts) == 3:
        return f"mv {parts[2]} {parts[1]}"
    if parts[0] == "mkdir":
        return f"rmdir {parts[-1]}"
    if parts[0] == "touch":
        return f"rm {parts[-1]}"
    if parts[0] == "systemctl" and len(parts) >= 3 and parts[1] == "stop":
        return f"systemctl start {parts[2]}"
    if parts[0] == "systemctl" and len(parts) >= 3 and parts[1] == "disable":
        return f"systemctl enable {parts[2]}"
    return None
