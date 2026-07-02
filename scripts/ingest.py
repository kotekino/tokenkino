#!/usr/bin/env python3
# ------------------------------------------------------------------------------------------------
# ingest.py — interactive fuel-feeder for a RUNNING tokeniko (the `task api` server must be up).
# Type a sentence → choose Axiom or Definition → it POSTs to the API (which compiles + stores it) →
# loop. Handy for feeding curated fuel (kotekino's personality axioms, selected definitions) into a
# live brain while it wonders. Uses only the stdlib.
#
#   python scripts/ingest.py                         # talks to http://localhost:8000
#   API_BASE=http://host:8000 python scripts/ingest.py
#
# At the prompt: type the sentence, then a/d (axiom/definition). Empty line or q/quit/Ctrl-D to exit.
# ------------------------------------------------------------------------------------------------
import json
import os
import sys
import urllib.request
import urllib.error

API_BASE = os.getenv("API_BASE", "http://localhost:8000").rstrip("/")
_ENDPOINT = {"a": "/api/v1/axioms", "d": "/api/v1/definitions"}
_LABEL = {"a": "axiom", "d": "definition"}


def _post(path: str, body: dict, timeout: float = 120.0):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(API_BASE + path, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8"))
        except Exception:
            return e.code, {"detail": e.reason}
    except urllib.error.URLError as e:
        return None, {"detail": f"cannot reach {API_BASE} — is `task api` running? ({e.reason})"}


def _ask_kind() -> str | None:
    while True:
        try:
            k = input("   [A]xiom or [D]efinition? ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return None
        if k in ("a", "axiom"):
            return "a"
        if k in ("d", "definition", "def"):
            return "d"
        if k in ("", "q", "quit", "exit"):
            return None
        print("   (type a or d — or q to cancel this one)")


def main():
    print(f"tokeniko fuel-feeder → {API_BASE}")
    print("Type a sentence, choose axiom/definition, and it posts. Empty line / q / Ctrl-D to quit.\n")
    n = 0
    while True:
        try:
            sentence = input("› ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if sentence.lower() in ("", "q", "quit", "exit"):
            break

        kind = _ask_kind()
        if kind is None:
            print("   skipped.\n")
            continue

        status, resp = _post(_ENDPOINT[kind], {"tokens": sentence})
        if status is None:
            print(f"   ✗ {resp.get('detail')}\n")
            continue
        if status == 200 and resp.get("status") == "complete":
            data = resp.get("data") or {}
            raw = data.get("raw")
            oid = data.get("_id") or data.get("id")
            n += 1
            print(f"   ✓ stored {_LABEL[kind]}  (id {oid})")
            if raw:
                print(f"     raw: {raw}")
            print()
        else:
            # domain error (e.g. 422 contradiction guard) or a failed write
            detail = resp.get("detail") or resp.get("data") or resp
            print(f"   ✗ {_LABEL[kind]} rejected [{status}]: {detail}\n")

    print(f"done — {n} item(s) ingested.")


if __name__ == "__main__":
    main()
