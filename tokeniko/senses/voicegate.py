# --------------------------------------------------------------
# senses/voicegate.py — the shared rag2-out voice gate (lifted here 2026-07-24 so BOTH consumers
# refer to ONE seam, never a copy). It asks the API whether a polish still compiles to the raw's
# meaning: POST /api/v1/voice/verify → verifier_voice (consensus-with-the-compiler). Consumers:
#   - senses/outbound.py:_voice_out — one verified fluency pass over a whole composed chat reply.
#   - senses/blog.py:polish        — the SAME seam, per line, on a line-aligned blog polish.
# Graceful None on any trouble (API down / malformed reply) — every caller ships the raw on None.
#
# pipeline-light BY CONSTRUCTION: stdlib only (json/os/urllib/logging) — importable without discord,
# spaCy, or the bunnet DB models, so senses/blog.py keeps its own import-lightness by importing HERE
# rather than dragging in outbound.py's DB-bound module surface.
# --------------------------------------------------------------
import json
import logging
import os
import urllib.request
from typing import Optional

logger = logging.getLogger("tokeniko-brain")

_API_BASE = os.getenv("BRAIN_API_BASE", "http://localhost:8000")  # same seam as inbound
_VERIFY_TIMEOUT = float(os.getenv("SENSES_VOICE_VERIFY_TIMEOUT", "120"))  # two compiles; patient


# ask the API whether the polish still compiles to the raw's meaning. Graceful None on any trouble
# (API down / malformed reply) — the caller ships the raw. Sync (urllib): callers on an event loop
# run it off-thread (asyncio.to_thread), as _voice_out and blog.polish do.
def _verify_voice(raw: str, polished: str) -> Optional[dict]:
    body = json.dumps({"raw": raw, "polished": polished}).encode("utf-8")
    req = urllib.request.Request(
        f"{_API_BASE.rstrip('/')}/api/v1/voice/verify", data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=_VERIFY_TIMEOUT) as resp:
            out = json.loads(resp.read().decode("utf-8"))
        return out.get("data") if out.get("status") == "complete" else None
    except Exception as error:
        logger.warning("[voicegate] voice verify unreachable (%s) — raw ships", error)
        return None
