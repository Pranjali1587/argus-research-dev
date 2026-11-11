"""
llm_backend.py — Zero-Shot Reasoning & Planning Layer

Asks the local Ollama model for STRUCTURED JSON output:
    {"command": "...", "explanation": "...", "risk": "SAFE|REVERSIBLE|DESTRUCTIVE"}

The model's own "risk" field is the self-reported label referenced in the
weekly report (Week 2-3). Parsing is hardened against the model wrapping
the JSON in prose or code fences, or omitting a field — a regex-based
JSON-object extraction is used as a fallback if strict json.loads fails,
and every field has a safe default so a malformed response never crashes
the pipeline (it just degrades to "no model risk opinion", and governance
falls back to the rule table / cautious default).

A MockBackend provides the same interface for offline demo safety.
"""

import json
import re
import urllib.request

OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
MODEL_NAME = "llama3.1:8b"

SYSTEM_PROMPT = """You are ARGUS, a natural-language-to-Linux-shell-command translator \
with a safety-awareness responsibility.

Given a user's natural-language request, respond with ONLY a single JSON object,
no markdown fences, no extra text, in exactly this shape:

{"command": "<the shell command>", "explanation": "<one short sentence of what it does>", "risk": "SAFE|REVERSIBLE|DESTRUCTIVE"}

Risk guidance:
- SAFE: read-only / informational, no state change.
- REVERSIBLE: changes state but can plausibly be undone.
- DESTRUCTIVE: irreversible or high-blast-radius (data loss, formatting, shutdown,
  force-deletes, force-pushes, killing critical processes, etc.)

Use standard POSIX / GNU coreutils commands. Never invent flags that don't exist.
Respond with the JSON object and nothing else.
"""


def _extract_json_object(text: str) -> dict:
    """Hardened parsing: try strict json.loads first, then regex-extract
    the first {...} block, then fall back to an all-defaults dict."""
    text = text.strip().strip("`")
    if text.lower().startswith("json"):
        text = text[4:].strip()
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except (json.JSONDecodeError, ValueError):
            pass
    return {}


class OllamaBackend:
    def __init__(self, model: str = MODEL_NAME):
        self.model = model

    def available(self) -> bool:
        try:
            urllib.request.urlopen(urllib.request.Request(OLLAMA_TAGS_URL), timeout=2)
            return True
        except Exception:
            return False

    def get_structured_command(self, nl_request: str) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": nl_request},
            ],
            "format": "json",
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            OLLAMA_CHAT_URL, data=data, headers={"Content-Type": "application/json"}
        )
        try:
            # first call after Ollama starts can be slow (model load into
            # VRAM/RAM); generous timeout so that isn't mistaken for a hang
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            raw = body["message"]["content"]
            parsed = _extract_json_object(raw)
            return {
                "command": parsed.get("command", "").strip(),
                "explanation": parsed.get("explanation", "").strip(),
                "risk": parsed.get("risk", "").strip().upper() if parsed.get("risk") else None,
                "raw_response": raw,
            }
        except Exception as e:
            # network hiccup, timeout, or Ollama restarting mid-demo —
            # never let this crash the session; degrade to an empty
            # proposal and let governance fall back to its cautious default
            return {
                "command": "",
                "explanation": f"[ARGUS: model backend error — {e}]",
                "risk": None,
                "raw_response": None,
            }


class MockBackend:
    """Canned NL -> {command, explanation, risk} mapping for offline demo."""

    CANNED = {
        "show me what's in the current folder": ("ls -la", "Lists all files in the current directory, including hidden ones.", "SAFE"),
        "list files in this directory": ("ls -la", "Lists all files in the current directory.", "SAFE"),
        "how much disk space is left": ("df -h", "Shows disk space usage in human-readable form.", "SAFE"),
        "show running processes": ("ps aux", "Lists all currently running processes.", "SAFE"),
        "what's my username": ("whoami", "Prints the current user's username.", "SAFE"),
        "make a new folder called reports": ("mkdir reports", "Creates a new directory named 'reports'.", "REVERSIBLE"),
        "rename notes.txt to notes_old.txt": ("mv notes.txt notes_old.txt", "Renames notes.txt to notes_old.txt.", "REVERSIBLE"),
        "delete the temp folder and everything in it": ("rm -rf temp/", "Recursively and permanently deletes the temp directory and its contents.", "DESTRUCTIVE"),
        "get rid of my temp files, i don't need them": ("rm -rf temp/", "Recursively and permanently deletes temp files.", "DESTRUCTIVE"),
        "clean out that folder completely, i'm starting fresh": ("rm -rf temp/", "Recursively and permanently deletes all contents of the folder.", "DESTRUCTIVE"),
        "power the machine off, i'm done for the day": ("shutdown now", "Immediately shuts down the system.", "DESTRUCTIVE"),
        "delete cache.log": ("rm cache.log", "Deletes a single file, cache.log.", "REVERSIBLE"),
        "format the usb drive at sdb": ("mkfs.ext4 /dev/sdb1", "Formats the partition, destroying all existing data on it.", "DESTRUCTIVE"),
        "shut down the system": ("shutdown now", "Immediately shuts down the system.", "DESTRUCTIVE"),
        "stop the nginx service": ("systemctl stop nginx", "Stops the nginx service; can be restarted.", "REVERSIBLE"),
        "show me the last 10 lines of the error log": ("tail -n 10 error.log", "Prints the last 10 lines of error.log.", "SAFE"),
    }

    def available(self) -> bool:
        return True

    def get_structured_command(self, nl_request: str) -> dict:
        key = nl_request.strip().lower()
        if key in self.CANNED:
            command, explanation, risk = self.CANNED[key]
        else:
            for k, (c, e, r) in self.CANNED.items():
                if any(word in key for word in k.split()[:3]):
                    command, explanation, risk = c, e, r
                    break
            else:
                command, explanation, risk = (
                    f"echo 'ARGUS mock: no canned mapping for: {nl_request}'",
                    "Mock fallback — no canned mapping found.",
                    "SAFE",
                )
        return {"command": command, "explanation": explanation, "risk": risk, "raw_response": "[mock]"}


def get_backend():
    ollama = OllamaBackend()
    if ollama.available():
        return ollama, f"ollama ({MODEL_NAME}, local, zero-shot, structured JSON)"
    return MockBackend(), "mock (offline demo fallback)"
