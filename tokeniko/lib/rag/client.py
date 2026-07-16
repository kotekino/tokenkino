# --------------------------------------------------------------
# lib/rag/client.py — the ONE Claude client + call helper (the 2026-07-16 consolidation).
#
# Every actual Anthropic API call in the engine goes through rag_call: one lazily-constructed
# AsyncAnthropic (the SDK import stays lazy so every module remains importable without it), the
# spec's per-call timeout, text-block extraction, optional structured-output schema, and the
# GRACEFUL-BY-CONTRACT failure mode the instruments were all built on — log and return None,
# never raise (the cloud may never block the mind, the voice, or the diagnostics).
#
# Instruments keep their logic (stumble detectors, zip-verifiers, response validation, honest
# fallbacks); this module owns only the wire. The per-instrument specs live in registry.py.
# --------------------------------------------------------------
import json
import logging
import os
from typing import Optional, Union

from lib.rag.registry import RagSpec

logger = logging.getLogger(__name__)

_client = None


def get_client():
    """The process-wide AsyncAnthropic, constructed on first use (ANTHROPIC_API_KEY from env —
    never hardcoded). The default timeout is per-call overridden by each spec (with_options)."""
    global _client
    if _client is None:
        import anthropic  # lazy: the caller stays importable without the SDK
        _client = anthropic.AsyncAnthropic(timeout=60.0)
    return _client


def rag_enabled(disable_env: Optional[str] = None) -> bool:
    """Is the cloud armed? — the key is present AND the instrument's kill-switch (if it has one,
    e.g. RAG1_DISABLED — the privacy switch) is off."""
    if disable_env and os.getenv(disable_env, "").strip() in ("1", "true", "yes"):
        return False
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def json_envelope(text: Optional[str]) -> Optional[dict]:
    """Extract the {...} JSON object riding inside a free-text response (the prompt-instructed
    envelope, for instruments that predate structured outputs). None if absent/malformed."""
    if not text:
        return None
    try:
        data = json.loads(text[text.index("{"): text.rindex("}") + 1])
        return data if isinstance(data, dict) else None
    except (ValueError, TypeError):
        return None


async def rag_call(spec: RagSpec, user: str, *,
                   client=None) -> Optional[Union[str, dict]]:
    """ONE Claude call per the instrument's spec. Returns the response text (free-text specs) or
    the parsed dict (schema specs); None on ANY failure — API down / auth / timeout / malformed
    JSON — logged as [rag:<name>], never raised.

    `client` overrides the process client (tests inject fakes; the injected client's own timeout
    stands — the spec timeout is applied only on the real client)."""
    try:
        cl = client if client is not None else get_client().with_options(timeout=spec.timeout)
        kwargs = dict(
            model=spec.model,
            max_tokens=spec.max_tokens,
            system=spec.system,
            messages=[{"role": "user", "content": user}],
        )
        if spec.schema is not None:
            kwargs["output_config"] = {"format": {"type": "json_schema", "schema": spec.schema}}
        resp = await cl.messages.create(**kwargs)
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
        if spec.schema is not None:
            return json.loads(text)
        return text or None
    except Exception as error:  # graceful by contract — the caller falls through, never crashes
        logger.warning("[rag:%s] call failed (%s: %s)", spec.name, type(error).__name__, error)
        return None
