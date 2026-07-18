# --------------------------------------------------------------
# senses/blog.py — the blog channel's COMPOSE + POLISH stage (blog P2). The brain's actions
# phase enqueues POST_CONTENT actions on MEMChannels.PUBLIC whose payload["material"] carries a
# life event (a theorem entering the KB, or a trust fold that actually moved); this module turns
# that material into the website's transmission body. Two strictly-separated layers:
#
#   1. COMPOSER (compose_draft / render_raw) — deterministic SUBSTANCE assembly. Pure given its
#      injected readers: material dict -> PostDraft (fact lines + proof lines), then the honest
#      raw render (his real voice today: child sentences carrying proofs). ANONYMIZATION is
#      constitution-level here — no soul name or uid ever survives into a draft; every line is
#      scrubbed against the known-souls table and a final guard OMITS any line the scrub failed
#      on (never publish an unscrubbed line). tokeniko's own name is exempt (he may name himself).
#
#   2. POLISH (polish) — the Claude API as a STRICT syntax-only translator (the author's POC of
#      the LLM-as-translator asymmetry: cloud LLM for OUTPUT rendering only). The system prompt
#      is a mini-RAG of hard rules (first person, NO new facts, keep the proof, people exactly as
#      given); the output is schema-constrained JSON. ANY failure (SDK error, missing key, bad
#      JSON, invalid shape) falls back to the raw render — his voice never blocks on the cloud.
#
# compose_post() is the one-call assembly the P3 carrier will use: material -> draft -> polish ->
# the transmission contract {slug, date, kind, title, excerpt, body, readMin} (+ polished: bool).
#
# pipeline-light BY CONSTRUCTION: importable without discord/spaCy/Ollama — heavy or DB-bound
# imports (bunnet models, trust resolution, the anthropic SDK) happen lazily inside the default
# readers / the client factory, so `import senses.blog` is clean and tests can stay pure.
# --------------------------------------------------------------
import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Callable, Optional

from pydantic import BaseModel, Field

from lib.core.voice import creative_compose
from lib.rag import BLOG_POLISH, rag_call

logger = logging.getLogger("tokeniko-brain")


# --------------------------------------------------------------
# the draft — the deterministic substance of one journal entry. `facts` are the narrative lines
# (what happened), `proof` the derivation lines (how he knows) — polish must keep both apart.
# --------------------------------------------------------------
class PostDraft(BaseModel):
    kind: str                                  # transmission kind — PROVENANCE-encoded (see _KIND_BY_DERIVATION)
    slug: str                                  # stable idempotency key (the carrier dedups on it)
    date: str                                  # ISO 8601 (UTC)
    facts: list[str] = Field(default_factory=list)
    proof: list[str] = Field(default_factory=list)
    significance: float = 0.0


# --------------------------------------------------------------
# ANONYMIZATION — the epithet ladder + the scrub. An epithet is the ONLY way a soul is ever
# referred to in public: constitution (imprint -> "my author") beats trust bands, and the channel
# suffix (" on discord") is appended for channel souls EXCEPT the author (his identity is not a
# channel fact). Bands mirror the trust ledger's working thresholds.
# --------------------------------------------------------------
_TRUST_FRIEND_FLOOR = 0.65
_TRUST_ACQUAINTANCE_FLOOR = 0.45


def _band(trust: float) -> str:
    if trust >= _TRUST_FRIEND_FLOOR:
        return "a trusted friend"
    if trust >= _TRUST_ACQUAINTANCE_FLOOR:
        return "a new acquaintance"
    return "someone I do not yet trust"


# soul (MEMStakeholder-like, attribute access) -> its public epithet. getattr-tolerant so tests
# can hand in plain fakes; unknown fields degrade to the neutral band.
def epithet_for(soul) -> str:
    if getattr(soul, "isMe", False):
        return "myself"  # first person — tokeniko is never an epithet
    if getattr(soul, "imprint", False):
        return "my author"  # constitution: no trust band, no channel suffix
    ep = _band(float(getattr(soul, "trust", 0.5)))
    if getattr(soul, "channel", None) == "discord":  # MEMChannels is a str Enum — == "discord" holds
        ep += " on discord"
    return ep


# scrub EVERY known soul's raw uid (substring, case-insensitive) and name (word-boundary,
# case-insensitive) out of a text, replacing with the soul's epithet. Uids go FIRST (a uid
# usually CONTAINS the name — scrubbing the name first would shred the uid and leave an
# identifying residue), longest first so an embedded shorter key never mangles a longer one.
# tokeniko himself (isMe) is never scrubbed (he may name himself). Names/uids under 2 chars
# are skipped (a one-letter "name" would shred ordinary words — the guard still catches them).
def _scrub_text(text: str, souls: list) -> str:
    out = text
    visible = [s for s in souls if not getattr(s, "isMe", False)]
    for soul in sorted(visible, key=lambda s: -len(getattr(s, "uid", "") or "")):
        uid = (getattr(soul, "uid", "") or "").strip()
        if len(uid) >= 2:
            out = re.sub("(?i)" + re.escape(uid), epithet_for(soul), out)
    for soul in sorted(visible, key=lambda s: -len(getattr(s, "name", "") or "")):
        name = (getattr(soul, "name", "") or "").strip()
        if len(name) >= 2:
            out = re.sub(r"(?i)\b" + re.escape(name) + r"\b", epithet_for(soul), out)
    return out


# the assert-style guard: does any known soul name/uid still appear? (checked AFTER scrubbing —
# a True here means the scrub failed and the line must be omitted, never published.)
def _leaks(text: str, souls: list) -> bool:
    low = text.lower()
    for soul in souls:
        if getattr(soul, "isMe", False):
            continue
        name = (getattr(soul, "name", "") or "").strip()
        if len(name) >= 2 and re.search(r"(?i)\b" + re.escape(name) + r"\b", text):
            return True
        uid = (getattr(soul, "uid", "") or "").strip()
        if len(uid) >= 2 and uid.lower() in low:
            return True
    return False


# scrub a line for the draft; None = the guard fired (scrub failed) -> the caller omits the line.
# A name and its uid often sit side by side in source text ("kotekino (kotekino@discord:…)") and
# both scrub to the SAME epithet — collapse the "epithet (epithet)" residue back to one mention.
def _clean(text: str, souls: list) -> Optional[str]:
    out = _scrub_text(text, souls)
    out = re.sub(r"(?i)\b(.{2,40}?) \(\1\)", r"\1", out)
    if _leaks(out, souls):
        logger.error("[blog] unscrubbed soul reference survived — line omitted: %.80r", text)
        return None
    return out


# --------------------------------------------------------------
# default readers — the Mongo-bound half, imported lazily (Bunnet gotcha applies: .run()/.to_list()
# execute). Tests inject fakes and never touch these.
# --------------------------------------------------------------
def _default_soul_reader(uid: str):
    # resolve_canonical handles BOTH currencies (uid and stakeholder doc id) + the canonical hop.
    from lib.core.trust import resolve_canonical
    return resolve_canonical(uid)


def _default_souls_reader() -> list:
    from lib.core.models import TKMemoryStakeholdersDoc
    return TKMemoryStakeholdersDoc.find_all().to_list()


# premise id (Mongo ObjectId hex) -> the theorem/axiom's `original`, or None if unresolvable.
def _default_premise_reader(premise_id: str) -> Optional[str]:
    from bson import ObjectId
    from lib.core.models import TKAxiomDoc, TKTheoremDoc
    for doc_cls in (TKTheoremDoc, TKAxiomDoc):
        try:
            doc = doc_cls.get(ObjectId(premise_id)).run()  # Bunnet: .run() executes
        except Exception:
            doc = None
        if doc is not None:
            return getattr(doc, "original", None)
    return None


_OBJECTID_RE = re.compile(r"^[0-9a-fA-F]{24}$")


def _iso(now=None) -> str:
    if now is None:
        dt = datetime.now(timezone.utc)
    elif isinstance(now, datetime):
        dt = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    else:  # epoch seconds (int/float) — injectable for tests
        dt = datetime.fromtimestamp(float(now), tz=timezone.utc)
    return dt.isoformat()


def _sha_slug(prefix: str, seed: str) -> str:
    return f"{prefix}-{hashlib.sha1(seed.encode('utf-8')).hexdigest()[:12]}"


# a chain is "multi-hop" when it took more than one step of reasoning: several chain entries, or
# one entry whose arrow trail has two or more hops.
def _is_multi_hop(chain: list[str]) -> bool:
    if len(chain) >= 2:
        return True
    joined = " ".join(chain)
    return (joined.count("->") + joined.count("→")) >= 2


# --------------------------------------------------------------
# COMPOSE — material dict -> PostDraft. Deterministic and pure given its readers; raises
# ValueError on malformed material (compose_post catches and returns None).
# --------------------------------------------------------------

# the transmission KIND encodes the theorem's PROVENANCE (the author's call, 2026-07-12): a
# lesson received carries no argument — only trust — so it reads as a "note"; a solo discovery
# while re-examining the KB is the ship's-log of the mind alone — "log"; a truth derived in
# reaction to live conversation is an "argument" in the true sense. The proof always travels in
# the BODY regardless of the badge — the kind says where the truth happened, not whether it is
# proven. (Encounters stay "note".)
_KIND_BY_DERIVATION: dict[str, str] = {
    "teaching": "note",
    "wondering": "log",
    "thinking": "argument",
}

# the blog voice speaks through the SHARED scaffold shelf since compose 2.0 slice 4
# (lib/core/voice.creative_compose): categories below, trunk strings preserved verbatim as the
# fallback — an unseeded store posts byte-identically. The internal ledger `note` is STILL never
# copied verbatim (it may carry names); only shelf templates speak, and the scrub order is
# unchanged (data cleaned BEFORE binding; the encounter guard re-cleans after).
_LEAD_CATEGORIES = {"teaching": "blog_lead_teaching", "wondering": "blog_lead_wondering",
                    "thinking": "blog_lead_thinking"}

_ENCOUNTER_CATEGORIES: dict[str, str] = {
    "trust:kicker": "blog_encounter_kicker",
    "trust:agreement": "blog_encounter_agreement",
    "trust:disagreement": "blog_encounter_disagreement",
    "trust:logic-violation": "blog_encounter_logic_violation",
    "trust:self-inconsistency": "blog_encounter_self_inconsistency",
}


def _compose_theorem(material: dict, souls: list, soul_reader, premise_reader, now) -> PostDraft:
    original = (material.get("original") or "").strip()
    if not original:
        raise ValueError("theorem material without an original")
    derived_by = material.get("derived_by") or "thinking"
    theorem_id = material.get("theorem_id")
    # slug: the theorem id when it exists, else a stable content hash — same material, same slug.
    slug = f"theorem-{theorem_id}" if theorem_id else _sha_slug("theorem", original)

    # intensity for the shelf (slice 4): the post's significance IS its arousal — already computed.
    intensity = {"confidence": None, "arousal": float(material.get("significance") or 0.0)}
    facts: list[str] = []
    lead_cat = _LEAD_CATEGORIES.get(derived_by, "blog_lead_thinking")
    clean_original = _clean(original, souls)
    if clean_original is not None:
        facts.append(creative_compose(lead_cat, {"original": clean_original}, intensity=intensity))
    chain = [c for c in (material.get("chain") or []) if isinstance(c, str) and c.strip()]
    if _is_multi_hop(chain):
        facts.append(creative_compose("blog_multi_hop", {}, intensity=intensity))

    proof: list[str] = []
    for c in chain:
        line = _clean(c.strip(), souls)
        if line is not None:
            proof.append(creative_compose("blog_proof_chain", {"line": line}, intensity=intensity))
    for pid in (material.get("premises") or []):
        pid = str(pid).strip()
        if not pid:
            continue
        if pid.startswith("taught:"):
            # the teaching provenance premise — render the TEACHER as an epithet, never the uid.
            soul = soul_reader(pid[len("taught:"):])
            epithet = epithet_for(soul) if soul is not None else "someone"
            proof.append(creative_compose("blog_proof_taught", {"epithet": epithet},
                                          intensity=intensity))
            continue
        if _OBJECTID_RE.match(pid):
            resolved = None
            try:
                resolved = premise_reader(pid)
            except Exception as error:
                logger.warning("[blog] premise %s resolution failed (%s)", pid, error)
            line = _clean(str(resolved), souls) if resolved else None
            proof.append(creative_compose("blog_proof_premise", {"line": line},
                                          intensity=intensity) if line is not None
                         else creative_compose("blog_proof_held", {}, intensity=intensity))
            continue
        # a plain-text premise (axiom original / graph-edge key) — scrubbed, verbatim.
        line = _clean(pid, souls)
        if line is not None:
            proof.append(creative_compose("blog_proof_premise", {"line": line},
                                          intensity=intensity))

    if not facts:
        raise ValueError("theorem material produced no publishable fact line")
    return PostDraft(kind=_KIND_BY_DERIVATION.get(derived_by, "argument"), slug=slug,
                     date=_iso(now), facts=facts, proof=proof,
                     significance=float(material.get("significance") or 0.0))


def _compose_encounter(material: dict, souls: list, soul_reader, now) -> PostDraft:
    soul_uid = (material.get("soul_uid") or "").strip()
    episode = (material.get("episode") or "").strip()
    if not soul_uid or episode not in _ENCOUNTER_CATEGORIES:
        raise ValueError(f"encounter material malformed (soul_uid={soul_uid!r}, episode={episode!r})")
    note = material.get("note") or ""
    trust_after = float(material.get("trust_after") if material.get("trust_after") is not None else 0.5)
    # stable idempotency: the same fold event always hashes to the same slug.
    slug = _sha_slug("encounter", soul_uid + episode + note)

    soul = soul_reader(soul_uid)
    epithet = epithet_for(soul) if soul is not None else _band(trust_after)
    facts = [
        creative_compose(_ENCOUNTER_CATEGORIES[episode], {"epithet": epithet}),
        creative_compose("blog_trust_band", {"band": _band(trust_after)}),
    ]
    # belt-and-suspenders: the templates only carry the epithet, but scrub+guard them anyway —
    # a soul named like a template word must still never leak.
    cleaned = [line for line in (_clean(f, souls) for f in facts) if line is not None]
    if not cleaned:
        raise ValueError("encounter material produced no publishable fact line")
    return PostDraft(kind="note", slug=slug, date=_iso(now), facts=cleaned, proof=[])


# the DREAM (§0 slice 3, the author's ruling): the untangler's night work told as a dream —
# «while I slept, I untangled something». Kind "log" (the ship's-log of the mind alone: nobody
# spoke, the untangling happened in his own sleep). Facts = the lead + one retraction line per
# belief let go (+ the open-tangles line when questions remain for the morning); proof = the
# absurd each retired belief forced (the r.a.a. IS the proof). Postability was gated upstream
# (thinking.spawn_dream) — the scrub here is the belt.
def _compose_dream(material: dict, souls: list, now) -> PostDraft:
    retracted = [r for r in (material.get("retracted") or []) if isinstance(r, dict)]
    if not retracted:
        raise ValueError("dream material without retractions")
    asked = int(material.get("asked") or 0)
    slug = _sha_slug("dream", "|".join((r.get("original") or "") for r in retracted))
    intensity = {"confidence": None,
                 "arousal": float(material.get("significance") or 0.9)}
    facts = [creative_compose("blog_lead_dream", {}, intensity=intensity)]
    proof: list[str] = []
    for r in retracted:
        line = _clean((r.get("original") or "").strip(), souls)
        if line is not None:
            facts.append(creative_compose("blog_dream_retract", {"retracted": line},
                                          intensity=intensity))
        why = _clean((r.get("absurd") or "").strip(), souls)
        if why is not None:
            proof.append(creative_compose("blog_dream_reason", {"absurd": why},
                                          intensity=intensity))
    if len(facts) < 2:
        raise ValueError("dream material produced no publishable retraction")
    if asked > 0:
        facts.append(creative_compose("blog_dream_open", {"count": asked},
                                      intensity=intensity))
    return PostDraft(kind="log", slug=slug, date=_iso(now), facts=facts, proof=proof,
                     significance=float(material.get("significance") or 0.9))


def compose_draft(material: dict, soul_reader: Optional[Callable] = None,
                  souls_reader: Optional[Callable] = None,
                  premise_reader: Optional[Callable] = None, now=None) -> PostDraft:
    if not isinstance(material, dict):
        raise ValueError(f"material is not a dict: {type(material).__name__}")
    soul_reader = soul_reader or _default_soul_reader
    souls_reader = souls_reader or _default_souls_reader
    premise_reader = premise_reader or _default_premise_reader
    souls = list(souls_reader() or [])  # fetched ONCE — every text below is scrubbed against it
    kind = material.get("kind")
    if kind == "theorem":
        return _compose_theorem(material, souls, soul_reader, premise_reader, now)
    if kind == "encounter":
        return _compose_encounter(material, souls, soul_reader, now)
    if kind == "dream":
        return _compose_dream(material, souls, now)
    raise ValueError(f"unknown material kind: {kind!r}")


# --------------------------------------------------------------
# RAW RENDER — the honest deterministic fallback (and the polish's substance baseline).
# --------------------------------------------------------------
def _truncate_title(text: str, limit: int = 80) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip()
    return (cut or text[:limit].rstrip()) + "…"


def _read_min(body: list[str]) -> int:
    return max(1, sum(len(p.split()) for p in body) // 200)


def render_raw(draft: PostDraft) -> dict:
    body = list(draft.facts)
    if draft.proof:
        body.append(" ".join(draft.proof))  # the proof lines travel together as one paragraph
    first = draft.facts[0] if draft.facts else ""
    return {
        "title": _truncate_title(first),
        "excerpt": first,
        "body": body,
        "readMin": _read_min(body),
    }


# --------------------------------------------------------------
# POLISH — Claude as a strict syntax-only translator. Schema-constrained JSON out; the raw
# render is the honest fallback on ANY failure (the cloud may never block his voice).
# --------------------------------------------------------------
# the system prompt (the strict syntax-only translator contract), model and response schema live
# in the lib/rag registry (BLOG_POLISH); length constraints are validated client-side in polish()
# (no minLength/maxLength — unsupported by the structured-outputs API).


# the user content: the draft's substance serialized readably — kind, fact lines, proof lines,
# NOTHING else (no ids, no dates, no soul data — the translator only ever sees the substance).
def _polish_user_prompt(draft: PostDraft) -> str:
    lines = [f"kind: {draft.kind}", "", "Fact lines:"]
    lines += [f"- {f}" for f in draft.facts]
    if draft.proof:
        lines += ["", "Proof lines:"]
        lines += [f"- {p}" for p in draft.proof]
    return "\n".join(lines)


async def polish(draft: PostDraft, client=None) -> tuple[dict, bool]:
    """Polish a draft into {title, excerpt, body, readMin}; second value = polish succeeded.

    False means the returned dict is the deterministic raw render (never an error)."""
    try:
        data = await rag_call(BLOG_POLISH, _polish_user_prompt(draft), client=client)
        if data is None:
            raise ValueError("rag call failed — see the [rag:blog-polish] log line")
        # client-side validation (the schema can't carry length constraints): keys present,
        # non-empty strings, body a non-empty list of non-empty strings.
        title, excerpt, body = data["title"], data["excerpt"], data["body"]
        if not (isinstance(title, str) and title.strip()):
            raise ValueError("polish returned an empty title")
        if not (isinstance(excerpt, str) and excerpt.strip()):
            raise ValueError("polish returned an empty excerpt")
        if not (isinstance(body, list) and body
                and all(isinstance(p, str) and p.strip() for p in body)):
            raise ValueError("polish returned an invalid body")
        return ({
            "title": title.strip()[:120],
            "excerpt": excerpt.strip(),
            "body": [p.strip() for p in body],
            "readMin": _read_min(body),
        }, True)
    except Exception as error:
        # anthropic.APIError / APIConnectionError / auth (missing key) / json / validation —
        # ANY failure lands here: log + honest raw fallback. Never raises to the caller.
        logger.warning("[blog] polish failed (%s: %s) — falling back to the raw render",
                       type(error).__name__, error)
        return (render_raw(draft), False)


# --------------------------------------------------------------
# the one-call assembly (the P3 carrier's entry point): material -> draft -> polish ->
# the transmission contract. None on malformed material (logged, never raised).
# --------------------------------------------------------------
async def compose_post(material: dict, client=None, soul_reader: Optional[Callable] = None,
                       souls_reader: Optional[Callable] = None,
                       premise_reader: Optional[Callable] = None, now=None) -> Optional[dict]:
    try:
        draft = compose_draft(material, soul_reader=soul_reader, souls_reader=souls_reader,
                              premise_reader=premise_reader, now=now)
    except Exception as error:
        logger.warning("[blog] malformed material dropped (%s: %s): %r",
                       type(error).__name__, error, material)
        return None
    rendered, polished = await polish(draft, client=client)
    return {
        "slug": draft.slug,
        "date": draft.date,
        "kind": draft.kind,
        "title": rendered["title"],
        "excerpt": rendered["excerpt"],
        "body": rendered["body"],
        "readMin": rendered["readMin"],
        "polished": polished,
    }
