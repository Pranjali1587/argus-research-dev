"""
main.py — ARGUS Demo 1: minimal text-based front-end (Week 6 deliverable)

Runs the pipeline in-process (no need to have `uvicorn app:app` running
separately for the demo — one command, zero moving parts, zero risk of
a networking hiccup on stage). The exact same core.py logic is what
app.py exposes over HTTP if you want to show the API working too
(see README.md).

Run:
    python main.py            # dry-run mode (default, safe for a live demo)
    python main.py --execute  # actually runs commands (WSL/VM only)
"""

import argparse
import sys

import core
from logger import read_log

BANNER = r"""
   _   ____   ____ _   _ ____
  / \ |  _ \ / ___| | | / ___|
 / _ \| |_) | |  _| | | \___ \
/ ___ \  _ <| |_| | |_| |___) |
/_/   \_\_\_\\____|\___/|____/
 Adaptive Reasoning & Governance for Ubiquitous System-Intelligence
 Demo 1 -- safe text-based agent (zero-shot, governance layer v1)
"""


def handle_request(nl_request: str, dry_run: bool):
    proposal = core.propose(nl_request)

    print(f"\n  -> explanation:      {proposal['explanation']}")
    print(f"  -> proposed command: {proposal['command']}")
    print(f"  -> risk tier:        {proposal['risk_tier']}  ({proposal['reason']})  [{proposal['risk_source']}]")

    confirmed = True
    if proposal["requires_confirmation"]:
        answer = input(
            "  !  DESTRUCTIVE action requires confirmation. Type 'yes' to proceed, anything else to cancel: "
        ).strip().lower()
        confirmed = answer == "yes"
        if not confirmed:
            print("  x cancelled by user.")

    entry = core.execute_and_log(
        nl_request, proposal["command"], proposal["risk_tier"], proposal["reason"],
        proposal["rollback_hint"], confirmed, dry_run,
    )

    print(f"  -> {entry['execution_result']}")
    if proposal["rollback_hint"]:
        print(f"  <- rollback available: {proposal['rollback_hint']}")


def main():
    parser = argparse.ArgumentParser(description="ARGUS Demo 1 front-end")
    parser.add_argument("--execute", action="store_true", help="actually execute commands (default: dry-run)")
    parser.add_argument("--show-log", action="store_true", help="print the action log and exit")
    args = parser.parse_args()

    if args.show_log:
        for entry in read_log():
            print(entry)
        sys.exit(0)

    print(BANNER)
    print(f"  backend: {core.backend_label()}")
    print(f"  mode:    {'EXECUTE' if args.execute else 'DRY-RUN (safe)'}")
    print("  type a request in plain English, or 'exit' to quit.\n")

    while True:
        try:
            nl_request = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nexiting.")
            break
        if not nl_request:
            continue
        if nl_request.lower() in ("exit", "quit"):
            break
        try:
            handle_request(nl_request, dry_run=not args.execute)
        except Exception as e:
            # last-resort safety net: one bad request should never kill
            # the whole demo session
            print(f"  [ARGUS: unexpected error handling that request — {e}]")
            print("  (session still running — try another request)")


if __name__ == "__main__":
    main()
