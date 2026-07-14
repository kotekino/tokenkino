# --------------------------------------------------------------
# senses/microscope.py — rag3, the MICROSCOPE (the instrument arc P1, 2026-07-14 summit).
#
# A continuous oracle over the parser/compiler: every sentence tokeniko HEARS becomes a judged
# test case. A post-hoc poller (never inline — zero latency risk to the live path, and it can
# re-scan history from day one) walks the memory collection, builds a deterministic STRUCTURAL
# DIGEST of each item's compiled zip, and asks ONE Claude judge — armed with a mini-RAG of the
# pipeline's CONTRACT — the single question: *does the structure say what the sentence says?*
# Findings land in the `tkzipdebug` collection as LEADS for the crew's triage (confirmed leads →
# doc/ref/test-feedback.md → regression tests → fixes: the self-growing seedbank).
#
# Constitution of the instrument:
#   - STRICTLY OBSERVER: writes to tkzipdebug and NOTHING else. The microscope never touches the
#     specimen — no belief path, no feedback into the mind, no auto-fixes.
#   - INPUTS-ONLY (author's call at the summit): speech from OTHER souls. The self-render path is
#     being retired by zip-native derivation, and the output rendering belongs to the translator
#     apparatus's verifier.
#   - Opus on everything (author's economics: judge hardest while traffic is small and errors are
#     dense). A judge failure skips the item with a log line — diagnostics never block or retry-storm.
#
# Env: ANTHROPIC_API_KEY (required to run live), RAG3_DISABLED=1 (escape hatch),
#      SENSES_RAG3_POLL (seconds between polls, default 60), RAG3_BATCH (items per poll, default 5).
# --------------------------------------------------------------
import asyncio
import json
import logging
import os
from typing import Optional

from lib.core.io import get_tokeniko
from lib.core.models import TKMemoryItemDoc, TKZipDebugDoc
from lib.core.tkzip import TKZip, TKZipContent

logger = logging.getLogger("tokeniko-senses")

_JUDGE_MODEL = "claude-opus-4-8"

# ---- the structural digest (pure) -------------------------------------------------------------
# a deterministic, human/judge-readable rendering of the zip's SYMBOLIC content: per leaf, the
# operator it folds with, the WSD senses per role, quantifier/negation/mood, identities and flags.
# No vectors (geometry is not the judge's business), no ids beyond what meaning needs.


def _digest_leaf(op: str, attitude, c: TKZipContent) -> str:
    parts = [f"op={op}"]
    if attitude is not None:
        parts.append(f"attitude={getattr(attitude, 'value', attitude)}")
    senses = getattr(c, "senses", None) or {}
    parts.append("senses={" + ", ".join(f"{k}: {v}" for k, v in senses.items()) + "}")
    q = getattr(c, "quantifier", None)
    parts.append(f"quantifier={getattr(q, 'value', q)}")
    parts.append(f"negated={bool(getattr(c, 'negated', False))}")
    dub = getattr(c, "dubitative", 0.5)
    wh = getattr(c, "wh_role", None)
    parts.append(f"mood={'question' if dub == 1.0 else 'statement'}")
    if wh is not None:
        parts.append(f"wh_role={getattr(wh, 'value', wh)}")
    identities = getattr(c, "identities", None) or {}
    if identities:
        parts.append("identities={" + ", ".join(f"{k}: {v}" for k, v in identities.items()) + "}")
    markers = getattr(c, "markers", None) or {}
    if markers:
        parts.append("markers={" + ", ".join(f"{k}: {v}" for k, v in markers.items()) + "}")
    for flag in ("unknown", "reflexive"):
        if getattr(c, flag, False):
            parts.append(f"{flag}=True")
    return " ".join(parts)


def _digest_items(item, out: list, depth: int = 0) -> None:
    c = item.content
    op = getattr(getattr(item, "op", None), "value", getattr(item, "op", "AND"))
    att = getattr(item, "attitude", None)
    if isinstance(c, TKZipContent):
        out.append(("  " * depth) + f"clause[{len(out)}] " + _digest_leaf(op, att, c))
        return
    if isinstance(c, list):
        if depth > 0 or att is not None:
            out.append(("  " * depth) + f"group op={op}" + (f" attitude={att}" if att else ""))
        for child in c:
            _digest_items(child, out, depth + (1 if depth > 0 or att is not None else 0))


def digest_zip(zp: TKZip) -> str:
    """Deterministic structural digest of a compiled zip (pure; no DB, no vectors)."""
    lines: list = []
    _digest_items(zp.items, lines)
    return "\n".join(lines) if lines else "(empty zip)"


# ---- the judge ---------------------------------------------------------------------------------
# the CONTRACT mini-RAG: what each digest field MEANS, and which divergences are LEGITIMATE —
# the judge flags real mismatches, not design choices.
_JUDGE_SYSTEM = """You are a meticulous QA oracle for a neuro-symbolic NLP pipeline. You receive a
SENTENCE (as heard, verbatim) and the structural DIGEST of what the pipeline compiled it into.
Your ONLY question: does the structure say what the sentence says?

The digest's contract:
- Each clause line is one predication leaf. `senses` maps grammatical roles (subject / predicate /
  direct / indirect0.. / *_mod0.. / predicate_nmod) to WordNet synset keys (e.g. coin.n.01).
- `op` is the operator the leaf folds with into the statement (AND / OR / IMPLY / CONV / THAT...).
  A conditional or complement clause MUST NOT appear as a bare AND assertion.
- `quantifier` reads the subject's determiner: universal (all/every), existential (a/some ~ also
  'indefinite'), negative (no/none), definite (the/this), generic (bare plural).
- `negated=True` means the clause asserts NOT-P. `mood` is question/statement; `wh_role` is the
  question's gap (subject/predicate/direct/location/time/manner/cause).
- `identities` binds a role to a named INDIVIDUAL's uid (name@channel:... for persons; a known
  place is GLOBAL: name@place, e.g. japan@place). A named person/place should carry an identity;
  a common noun should not. A place identity has no `senses` entry for its role BY DESIGN (a place
  is an individual, not a class — its type/containment live in the places knowledge base).
- `markers` carries the preposition/case lemma per marked role ("indirect0: in") — the RELATOR.
  A locative/prepositional complement is faithfully carried when its role shows the identity (or
  sense) plus the marker.
- `unknown=True` = out-of-vocabulary clause (legitimate for gibberish); `reflexive=True` = an
  identity claim (a = a).

LEGITIMATE divergences you must NOT flag:
- A leading/trailing address ("tokeniko, ...") is dropped by design (vocative strip).
- Sense granularity: the dictionary may hold only a subset of WordNet senses, so the chosen sense
  is the nearest AVAILABLE — flag it only when the chosen sense's MEANING contradicts the
  sentence's plain reading (that is a real lead: a dictionary coverage gap).
- Function words, articles, tense/aspect nuances and politeness carry no leaf of their own.
- The zip is PERSPECTIVE-RESOLVED by design: a second-person pronoun ("you") spoken TO tokeniko
  legitimately binds tokeniko's identity uid on its role, and a speaker's "I" binds the speaker's.
  Never flag this identity binding — it is the identity-bridge working, not a misattribution.

Judge honestly and conservatively: verdict "ok" when the structure faithfully carries the
sentence's predications, operators, polarity, quantification, mood and named individuals;
"mismatch" otherwise. Confidence is YOUR calibrated certainty in the verdict (0..1). On mismatch
pick the single dominant category: wrong-sense | wrong-structure | missed-negation |
missed-quantifier | missed-mood | dropped-content | operator-flattening | other. Severity: how
badly a reasoning engine would be misled (low/medium/high). The note: ONE terse paragraph naming
exactly what diverges — write it for the engineer who will turn it into a regression test."""

# NB no null unions: the structured-output validator rejects enum values against a
# ["string","null"] type array (live lesson, first sweep 2026-07-14) — sentinel "none"/"" strings
# instead, mapped back to None client-side in judge().
_JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["ok", "mismatch"]},
        "confidence": {"type": "number"},
        "severity": {"type": "string", "enum": ["low", "medium", "high", "none"]},
        "category": {"type": "string", "enum": ["wrong-sense", "wrong-structure",
                                                "missed-negation", "missed-quantifier",
                                                "missed-mood", "dropped-content",
                                                "operator-flattening", "other", "none"]},
        "note": {"type": "string"},
    },
    "required": ["verdict", "confidence", "severity", "category", "note"],
    "additionalProperties": False,
}

_client = None  # lazily-constructed module-level AsyncAnthropic (same pattern as the blog polish)


def _get_client():
    global _client
    if _client is None:
        import anthropic  # lazy: the module stays importable without the SDK
        _client = anthropic.AsyncAnthropic(timeout=60.0)  # ANTHROPIC_API_KEY from env
    return _client


# the GROUNDED GLOSSARY (2026-07-14, the thinker incident): the judge was hallucinating WordNet
# glosses from memory (it believed thinker.n.02 = "a philosopher" — actually "someone who
# exercises the mind" — and flagged a CORRECT pick). Fetch the digest's senses' REAL definitions
# from the dictionary and hand them to the judge, so sense-fidelity is judged against ground
# truth, never recall. Failure-safe: any error returns "" (the judge runs without it).
def sense_glossary(zp: TKZip) -> str:
    try:
        from lib.core.models import TKDictionaryDoc
        senses: set = set()
        def collect(item):
            c = item.content
            if isinstance(c, TKZipContent):
                senses.update(v for v in (getattr(c, "senses", None) or {}).values() if v)
            elif isinstance(c, list):
                for ch in c:
                    collect(ch)
        collect(zp.items)
        lines = []
        for s in sorted(senses):
            d = TKDictionaryDoc.find_one({"sense": s}).run()
            if d is not None and d.definition:
                lines.append(f"- {s}: {d.definition}")
        return "\n".join(lines)
    except Exception as error:
        logger.warning("[microscope] glossary failed (%s: %s) — judging without it",
                       type(error).__name__, error)
        return ""


async def judge(original: str, digest: str, client=None, glossary: str = "") -> Optional[dict]:
    """One judged verdict for (sentence, digest), or None on ANY failure (logged, never raised).

    A None simply skips the item this pass — the microscope is diagnostics, never a blocker."""
    try:
        cl = client if client is not None else _get_client()
        user = f"SENTENCE:\n{original}\n\nDIGEST:\n{digest}"
        if glossary:
            user += ("\n\nGLOSSARY (the chosen senses' ACTUAL dictionary definitions — judge "
                     f"sense fidelity against THESE, never your recall):\n{glossary}")
        response = await cl.messages.create(
            model=_JUDGE_MODEL,
            max_tokens=1024,
            system=_JUDGE_SYSTEM,
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": _JUDGE_SCHEMA}},
        )
        text = next(b.text for b in response.content if b.type == "text")
        data = json.loads(text)
        if data["verdict"] not in ("ok", "mismatch"):
            raise ValueError(f"invalid verdict {data['verdict']!r}")
        confidence = max(0.0, min(1.0, float(data["confidence"])))
        # sentinel -> None (the schema carries no null unions; see the schema note above)
        severity = data.get("severity") if data.get("severity") not in ("none", "", None) else None
        category = data.get("category") if data.get("category") not in ("none", "", None) else None
        note = data.get("note") if (data.get("note") or "").strip() else None
        return {
            "verdict": data["verdict"],
            "confidence": confidence,
            "severity": severity,
            "category": category,
            "note": note,
            "model": _JUDGE_MODEL,
        }
    except Exception as error:
        logger.warning("[microscope] judge failed (%s: %s) — item skipped this pass",
                       type(error).__name__, error)
        return None


# ---- the poller ---------------------------------------------------------------------------------

def pending_items(me_id: str, judged_ids: set, batch: int) -> list:
    """The next unjudged INPUT items (zip present, spoken by another soul), oldest first —
    so the day-one pass re-scans history in biography order."""
    items = TKMemoryItemDoc.find(
        {"sourceId": {"$ne": me_id}, "zip": {"$ne": None}}
    ).sort("+timestamp").to_list()
    return [i for i in items if str(i.id) not in judged_ids][:batch]


async def microscope_pass(client=None, batch: int = 5) -> int:
    """One poll: judge up to `batch` pending items; returns how many verdicts were written."""
    me_id = str(get_tokeniko().id)
    judged_ids = {d.item_id for d in TKZipDebugDoc.find({}).to_list()}
    written = 0
    for item in pending_items(me_id, judged_ids, batch):
        dig = digest_zip(item.zip)
        verdict = await judge(item.original, dig, client=client, glossary=sense_glossary(item.zip))
        if verdict is None:
            continue  # judge failure: leave unjudged, the next pass retries
        TKZipDebugDoc(item_id=str(item.id), original=item.original, digest=dig,
                      **verdict).save()
        written += 1
        if verdict["verdict"] == "mismatch":
            logger.info("[microscope] LEAD (%s/%s): «%s» — %s",
                        verdict.get("category"), verdict.get("severity"),
                        item.original, (verdict.get("note") or "")[:140])
    return written


async def microscope_task():
    """The senses task: poll forever (RAG3_DISABLED=1 to disarm; key-less runs disarm themselves)."""
    if os.getenv("RAG3_DISABLED", "0").strip() in ("1", "true", "yes"):
        logger.info("[microscope] disabled by RAG3_DISABLED — not polling")
        return
    if not os.getenv("ANTHROPIC_API_KEY", "").strip():
        logger.info("[microscope] no ANTHROPIC_API_KEY — not polling")
        return
    poll_s = float(os.getenv("SENSES_RAG3_POLL", "60"))
    batch = int(os.getenv("RAG3_BATCH", "5"))
    logger.info("[microscope] 🔬 armed — poll=%ss batch=%s judge=%s", poll_s, batch, _JUDGE_MODEL)
    while True:
        try:
            n = await microscope_pass(batch=batch)
            if n:
                logger.info("[microscope] pass complete — %d verdict(s) written", n)
        except Exception as error:
            logger.warning("[microscope] pass failed (%s: %s) — retrying next poll",
                           type(error).__name__, error)
        await asyncio.sleep(poll_s)
