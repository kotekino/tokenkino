# --------------------------------------------------------------
# brain/api_client.py — the brain's FIRST OUTBOUND SEAM (#4 D3a). The brain process is PARSER-FREE
# (it never loads spaCy/Stanza/the compiler); when it needs the full pipeline — to compile a derived
# conclusion into a first-class zip theorem — it reaches the `api` process over HTTP rather than
# importing the parser. This module is that thin client.
#
# Stdlib-only (urllib) on purpose: a tiny, dependency-free, SYNCHRONOUS POST that fits the coordinator
# loop's one-bounded-unit-per-tick rhythm. GRACEFUL BY CONTRACT — if the API is down or errors, it
# LOGS and returns None; the brain never crashes on an unreachable seam (it simply retries next tick).
#
# D3a uses it for ONE call (materialize_theorem); D3b extends it (the senses target: speakup/answer/…).
# --------------------------------------------------------------
import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger("tokeniko-brain")

# base URL of the local `api` process (one body, one machine — see CLAUDE.md embodiment note).
_API_BASE = os.getenv("BRAIN_API_BASE", "http://localhost:8000")
_TIMEOUT = float(os.getenv("BRAIN_API_TIMEOUT", "30"))  # materialize compiles (~seconds); be patient


# POST a JSON body to `path` on the local API. Returns the parsed response dict, or None on ANY
# failure (connection refused, timeout, non-2xx, malformed JSON) — logged, never raised.
def _post_json(path: str, body: dict) -> dict | None:
    url = _API_BASE.rstrip("/") + path
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST", headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", "replace") if e.fp else ""
        logger.warning("[api_client] POST %s -> HTTP %s: %s", path, e.code, body_text[:200])
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        logger.warning("[api_client] POST %s unreachable (%s) — will retry next tick", path, e)
    except (ValueError, json.JSONDecodeError) as e:
        logger.warning("[api_client] POST %s — malformed response (%s)", path, e)
    return None


# MATERIALIZE a derived conclusion as a first-class theorem via the API pipeline. `tokens` is the
# rendered first-person NL ("I exist"); premises/chain/derived_by are its provenance (the proof). The
# API compiles it (talker=tokeniko ⇒ "I" → its own uid), semantic-dedups, and stores it ACTIVE +
# trusted. Returns the {status, data} dict (data = the theorem, existing or new), or None on failure.
def materialize_theorem(tokens: str, premises: list[str], chain: str, derived_by: str = "wondering") -> dict | None:
    return _post_json(
        "/api/v1/theorems/materialize",
        {"tokens": tokens, "premises": premises, "chain": chain, "derived_by": derived_by},
    )
