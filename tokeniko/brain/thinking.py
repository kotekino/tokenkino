# --------------------------------------------------------------
# brain/thinking.py — the Thinking cognition (#4 D1a). Closes perceive -> evaluate -> ideas:
# it reads stored `memory` TKZips, evaluates each against the current KB via the PARSER-FREE
# evaluate_zip harness, maps the outcome to a reserved eval:* token, and fans it into ideas through
# the behavior layer (which Priorities then arbitrates into actions).
#
# PARSER-FREE by construction: imports only the harness + lib.core.* + brain.behavior — never the
# parser/compiler — so the brain process never loads spaCy/Stanza. One bounded memory item per tick
# (think_one) keeps Thinking cooperative with the coordinator's Actions/Priorities phases.
#
# D1b (landing here): theorem derivation + the eval:true novelty split — a RESOLVED-true input whose
# derivation carries a FORWARD-CHAINED materialization ("chain: ...") is genuine derived knowledge and
# is silently materialized as an active theorem (tier-2, speaker-irrelevant). See materialize_theorem.
# STILL next: wondering (self-prompted derivation over the wondering window), and the tier-1 split (an
# eval:true that is NOT KB-derivable but taught by a trusted speaker -> learn at teacher trust).
# --------------------------------------------------------------
import hashlib
import json
import logging
import os
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId

import lib.core.evaluation_harness as evaluation_harness
from lib.core.deixis import normalize_deixis, strip_vocative
from lib.core.evaluation_harness import evaluate_zip
from lib.core.evaluation import EvaluatorResult, EvaluatorStatus
from lib.core.io import get_tokeniko
from lib.core.memory import (EvalToken, LifeEventKind, MEMChannels, MEMProvenance,
                             ReductioStatus, TrustEpisodeKind)
from lib.core import trust
from lib.core.models import (
    TKAxiomDoc,
    TKBrainStateDoc,
    TKDefinitionDoc,
    TKMemoryItemDoc,
    TKMemoryStakeholdersDoc,
    TKReductioDoc,
    TKTheoremDoc,
)
from lib.core.tk import TKQuantifier
from lib.llc.evaluator.e_keys import role_key
from lib.core.zip_native import assemble_reportative_zip
from brain import api_client, behavior, context, mimicry

logger = logging.getLogger("tokeniko-brain")

# strong-conclusion bands on a RESOLVED fuzzy truth: only the confident corners spawn an idea.
# the mid band (between FALSE_CEIL and TRUE_FLOOR) is "resolved-mid" — no strong conclusion, no idea.
TRUE_FLOOR = 0.85
FALSE_CEIL = 0.15

# WONDERING tunables (see wonder_one).
WONDER_QUEUE_CAP = 256     # max pending re-examinations (lifespan-bounded work, not history-bounded)
DRIFT_INTERVAL = 60        # seconds of wondering-idle before a drift (random) batch is enqueued
DRIFT_BATCH = 4            # how many random memory ids a drift batch enqueues


# memory `timestamp` is stored tz-aware UTC, but the timeseries collection reads it back NAIVE
# (tzinfo=None). .timestamp() on a naive datetime is interpreted in LOCAL time — a tz-skewed epoch.
# normalize: a naive ts is UTC, so the cursor is consistent regardless of the host tz.
# KEEP SUB-SECOND precision (float, NOT int): the stored ts has ms precision, so truncating the cursor
# to whole seconds leaves the just-processed item still `> cursor` (X.7 > X.0) → it is re-found and
# re-thought every tick (the obsessive loop). A sub-second cursor excludes it (strict `>` at ms).
def _epoch_utc(ts: datetime) -> float:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.timestamp()


# map an evaluation result to its reserved eval:* trigger token (the meta-language trigger side).
# INCONSISTENT -> eval:inconsistent (logic violation); INSUFFICIENT -> eval:unknown (missing KB);
# RESOLVED splits by truth confidence: > TRUE_FLOOR -> eval:true, < FALSE_CEIL -> eval:false,
# else None (resolved but no strong conclusion -> no idea spawned).
def status_to_token(result: EvaluatorResult) -> Optional[str]:
    if result.status == EvaluatorStatus.INCONSISTENT:
        return EvalToken.INCONSISTENT.value
    if result.status == EvaluatorStatus.INSUFFICIENT:
        return EvalToken.UNKNOWN.value
    if result.status == EvaluatorStatus.RESOLVED:
        if result.truth > TRUE_FLOOR:
            return EvalToken.TRUE.value
        if result.truth < FALSE_CEIL:
            return EvalToken.FALSE.value
    return None


# THE ANECDOTE (compose 2.0 slice 5, case 3): on a QUIET channel moment (the item drew no outward
# reflex) whose directedness sits in the AMBIENT band — channel talk not addressed to him, but not
# someone else's thread (the polite eavesdropper stays quiet below) — try the ideas-association:
# the context ring's topic centroid against the KB (context.find_association, floor + cooldown +
# novelty inside). The urge scales with PROXIMITY — how close it is IS how much it itches —
# mapped (1+p)/2 so a floor-grade association can still clear the act threshold under the
# self-relevant directedness floor (the push comes from within, not from being addressed).
_ANECDOTE_D_LO = float(os.getenv("ANECDOTE_DIRECTEDNESS_LO", "0.5"))
_ANECDOTE_D_HI = float(os.getenv("ANECDOTE_DIRECTEDNESS_HI", "0.9"))


# the etiquette family (survey slice 4, hunch 8): the SOCIAL REACTOR. A social item was
# recognized at the compile seam (MEMItem.social) and is NEVER evaluated — this is the only
# thing thinking does with it. The reflex fires for a room-wide act or one naming tokeniko;
# an act naming ANOTHER is their exchange (the 2026-07-05 over-engagement note) — recognized,
# skipped, silent. The speaker's display name rides as {name} for the warm registers.
_SOCIAL_TRIGGER = {
    "greeting": EvalToken.GREETING.value,
    "thanks": EvalToken.THANKS.value,
    "farewell": EvalToken.FAREWELL.value,
}


def _social_react(item: TKMemoryItemDoc) -> bool:
    trigger = _SOCIAL_TRIGGER.get(item.social or "")
    if trigger is None:
        return False  # an unknown kind — recognized enough to skip evaluation, nothing to say
    at = (item.social_at or "").strip().lower()
    if at and at != get_tokeniko().name.strip().lower():
        logger.info("[thinking] social %s aimed at %r — their exchange, staying quiet",
                    item.social, at)
        return False
    soul = trust.resolve_canonical(item.sourceId)
    name = soul.name if (soul is not None and not soul.isMe) else None
    ideas = behavior.spawn_ideas_for(
        trigger, source=str(item.id), target=item.sourceId,
        answer={"name": name} if name else None,
    )
    logger.info("[thinking] social %s from %s -> %d idea(s)", item.social, name or "?", len(ideas))
    return bool(ideas)


def _try_anecdote(item) -> None:
    d = getattr(item, "directedness", None)
    if d is None or not (_ANECDOTE_D_LO <= d < _ANECDOTE_D_HI):
        return
    key = context.channel_key(item)
    assoc = context.find_association(key)
    if assoc is None:
        return
    ideas = behavior.spawn_ideas_for(
        EvalToken.ASSOCIATION.value, payload=item.zip, source=str(item.id),
        answer=assoc, target=item.sourceId,
        urge_scale=(1.0 + assoc["proximity"]) / 2.0,
    )
    if ideas:
        context.record_anecdote(key, assoc["notion_id"])
        logger.info("[thinking] ASSOCIATION «%s» (p=%.2f) on channel %s -> side-note idea",
                    assoc["notion"], assoc["proximity"], key)


# B1 (compose 2.0 slice 4, generalized for the reductio §0): the premise ids that resolve to
# stored KB sentences — homed in the harness since §0 slice 3 (the untangler shares it).
def _premise_docs(premises) -> list:
    return evaluation_harness.premise_docs(premises)


# the refuting BELIEF behind a FALSE verdict — the first resolvable premise sentence; None and
# the plain speakup speaks (the slot gate keeps belief-naming scaffolds unreachable).
def _refuting_belief(premises) -> Optional[str]:
    docs = _premise_docs(premises)
    return docs[0].original.strip() if docs else None


# the CONTENT's epistemic confidence for the verdict (compose 2.0 slice 2) — computed HERE, the
# decision site, where truth + premises are in hand. INCONSISTENT = 1.0 (logic-certain: logic is
# sacred, logic never hedges). TRUE/FALSE = truth EXTREMITY scaled by the premises' trust — a
# refutation through a 0.6-trust taught rule pushes back softer than one through 1.0 axioms.
# UNKNOWN/None = no hedgeable content (the reflex asks, it does not assert).
def verdict_confidence(token: Optional[str], result: EvaluatorResult) -> Optional[float]:
    if token == EvalToken.INCONSISTENT.value:
        return 1.0
    trust = evaluation_harness._conclusion_trust(result.premises) if result.premises else 1.0
    if token == EvalToken.TRUE.value:
        return max(0.0, min(1.0, result.truth * trust))
    if token == EvalToken.FALSE.value:
        return max(0.0, min(1.0, (1.0 - result.truth) * trust))
    return None


# the D1b novelty split. A RESOLVED-true input's `derivation` may carry several provenance strings;
# only a FORWARD-CHAINED materialization is theorem-worthy:
#   "chain: ..."   — a UNIVERSAL rule fired down the is_a taxonomy to derive a NEW property
#                    ("all carnivores eat meat" + cat is_a* carnivore => "a cat eats meat"). This is
#                    knowledge DEMONSTRATED from axioms + the hardwired operator math => a THEOREM.
#   "subsumed:"/"part_of:" — trivial taxonomy, re-derivable from the graph on demand => NOT a theorem.
#   "refuted:"/"KB-refuted:" — a refutation (truth~0), not a truth at all => never a theorem.
# A derived theorem is TIER-2 = speaker-irrelevant (sourceId=tokeniko, trusted 0.9): it follows from
# the universal KB, not from who said it. TIER-1 (an eval:true that is NOT KB-derivable but taught by
# a trusted speaker) is DEFERRED — it needs a real KB-novelty signal, which this is not.
_CHAIN_PREFIX = "chain: "


def _derived_theorem(result: EvaluatorResult) -> bool:
    return any(d.startswith(_CHAIN_PREFIX) for d in (result.derivation or []))


# --------------------------------------------------------------
# THE PROVENANCE GATE (blog P1) — "DM never public" is a CONSTITUTION-level rule: knowledge whose
# provenance traces to a PRIVATE conversation must never feed the public channel. A DM is a Discord
# item graded fully-directed (senses/inbound.grade_directedness: DM exactly 1.0; addressed 0.9,
# ambient 0.6 — the >= 0.95 bar separates the DM grade from every channel grade). INTERNAL items are
# not DMs regardless of directedness (self-speech defaults directedness 1.0 but is not private input).
def _is_dm(item) -> bool:
    return (getattr(item, "channel", None) == MEMChannels.DISCORD
            and getattr(item, "directedness", 1.0) >= 0.95)


# --------------------------------------------------------------
# SIGNIFICANCE (blog P1) — how noteworthy a life event is, in [0,1]. It MODULATES the spawned idea's
# urge at the source (idea.urge = rule.urge x significance, behavior.spawn_ideas_for urge_scale), so
# the act threshold in Priorities does the rest: a plain single-hop wondered theorem stays below the
# bar (no post), a multi-hop / personal / taught one clears it. PURE over its inputs (unit-testable);
# the DB-touching relevance checks live in the small readers below it.
_SIG_BASE = 0.7        # every genuinely-new theorem starts noteworthy-ish
_SIG_MULTIHOP = 0.1    # a >= 2-step derivation chain — real inference, not a restatement
_SIG_PERSONAL = 0.2    # about a known soul, or about tokeniko himself
_SIG_TAUGHT = 0.1      # someone TAUGHT him something new (the teaching channel)
ENCOUNTER_SIGNIFICANCE = 0.9  # flat: a fold move is already rare by construction


def life_theorem_significance(derived_by: str, chain: str, personal: bool) -> float:
    sig = _SIG_BASE
    if (chain or "").count(" -> ") >= 2:  # chain steps are " -> "-joined (e_chaining) — >= 2 = multi-hop
        sig += _SIG_MULTIHOP
    if personal:
        sig += _SIG_PERSONAL
    if derived_by == "teaching":
        sig += _SIG_TAUGHT
    return max(0.0, min(1.0, sig))


# is the theorem PERSONALLY relevant? — its zip's identities include a KNOWN soul uid (entity-linked
# to a stakeholder), or the subject is tokeniko himself (first-person original).
def _is_personal(zip_obj, original: str) -> bool:
    if (original or "").startswith("I "):
        return True
    if zip_obj is None:
        return False
    for leaf in evaluation_harness._zip_leaves(zip_obj.items):
        for uid in (getattr(leaf, "identities", None) or {}).values():
            if uid and trust.resolve_canonical(uid) is not None:
                return True
    return False


# the WONDERING premise-AND (blog P1): a conclusion is postable only if EVERY premise theorem it
# rests on is. Premises circulate as theorem Mongo ids (edge_trust currency) — and the spec's
# `original` lookup is kept as the fallback; an unmatched premise (an axiom id / a "|" graph-edge
# key) counts as postable (axioms and bedrock edges carry no privacy). One postable=False premise
# POISONS the conclusion — the DM taint cascades exactly like min-trust does.
def _premises_postable(premises) -> bool:
    for pid in (premises or []):
        thm = None
        try:
            thm = TKTheoremDoc.get(ObjectId(pid)).run()  # Bunnet: .run() executes the query
        except Exception:
            thm = None
        if thm is None:
            thm = TKTheoremDoc.find_one({"original": pid}).run()
        if thm is not None and not getattr(thm, "postable", True):
            return False
    return True


# --------------------------------------------------------------
# THE DIGEST MACHINERY (the author's ruling 2026-07-21) — novelty of reasoning ⇒ immediate post,
# repetition of reasoning ⇒ digest. Wondering's existence flood posts EVERY «X exists» 1:1 (dozens
# of near-identical transmissions a night); the cure is to batch the REPEATED reasoning shape into
# one cumulative post («since x, y, z exist, each …»). The classification hook lives HERE, where the
# post idea is born — NOT where the theorem is minted (minting is sacred; a non-postable theorem
# still batches nothing, it just never reaches this seam). The buffer is homed on brain_state
# (everything-is-KB, restart-proof); the flush sites (sleep-onset, count-cap, boot) live in
# brain/main.py + the count-cap below.
# --------------------------------------------------------------
# an entry reaching this many subjects flushes immediately (no monster posts). Raised 15 → 40
# (the author's ruling 2026-07-23, the first digest night's lesson): at cap 15 the existence
# flood — ~2.7 mints/min — filled a cap every ~5.5 minutes and the count-cap became the PRIMARY
# flush, a metronome of 21 same-key digests; at 40 the intra-night pulse stays alive at chapter,
# not page, granularity (sleep-onset remains the true summary edge).
DIGEST_COUNT_CAP = int(os.getenv("BRAIN_DIGEST_COUNT_CAP", "40"))
DIGEST_SIGNIFICANCE = 0.9      # a cumulative post is noteworthy by construction: 0.65 x 0.9 = 0.585 >= 0.5


# the ACTIVE rule source-ids (the KB's own labelling of which premises are RULES) — the flood's
# shared reasoning IS the rule that fired across many subjects. _load_active_kb is fingerprint-cached
# (the reactive/wondering passes already loaded it this tick), so this is essentially free.
def _active_rule_source_ids() -> set[str]:
    kb = evaluation_harness._load_active_kb()
    return {str(r.get("source_id")) for r in kb.get("rules", []) if r.get("source_id")}


# the DIGEST KEY — the shared reasoning shape, extracted from provenance. Returns (key, kind, shared)
# or None (not digestible -> 1:1, conservative). The key is STABLE across restarts (rule source-ids
# are Mongo ids / stable "rule:…" keys; a teacher uid is immutable).
#   wondering: the RULE premise(s) — the flood's «every thing that exists …» rule fires the same
#              across subjects, so its id is the constant the subject-specific fact premises are not.
#              key = "rule:<hash of the sorted rule premises>"; shared = those rule ids.
#   teaching:  the teacher — "taught:<uid>" is already the provenance-premise shape; shared = [uid].
# ONLY these two faculties digest (a reactive-thinking derivation is conversational -> always 1:1).
def digest_classify(derived_by: str, premises: list,
                    rule_ids: Optional[set] = None) -> Optional[tuple[str, str, list]]:
    prems = [str(p) for p in (premises or [])]
    if not prems:
        return None
    if derived_by == "teaching":
        for p in prems:
            if p.startswith("taught:"):
                return (p, "teacher", [p[len("taught:"):]])
        return None
    if derived_by == "wondering":
        rules = rule_ids if rule_ids is not None else _active_rule_source_ids()
        shared = sorted(p for p in prems if p in rules)
        if not shared:
            return None  # no extractable shared rule premise -> not digestible (conservative)
        key = "rule:" + hashlib.sha1("|".join(shared).encode("utf-8")).hexdigest()[:12]
        return (key, "rule", shared)
    return None


# flush ONE buffer entry: spawn its cumulative digest post (mirrors _spawn_life_theorem's material
# shape, kind="digest") and clear its accumulation — the entry itself STAYS as the "seen" marker so
# subsequent same-key mints keep batching instead of re-posting 1:1. No-op on an empty entry.
# Returns the spawned idea (or None). The caller owns the bs.save().
def _flush_digest_entry(key: str, entry: dict) -> Optional[TKIdeaDoc]:
    if not entry.get("theorem_ids"):
        return None
    entry["generation"] = int(entry.get("generation", 0)) + 1
    sig = float(entry.get("significance") or DIGEST_SIGNIFICANCE)
    material = {
        "kind": "digest",
        "digest_key": key,
        "digest_kind": entry.get("kind"),               # "rule" | "teacher" — the render branch
        "theorem_ids": list(entry.get("theorem_ids") or []),
        "subjects": list(entry.get("subjects") or []),  # the batched originals (the composer renders these)
        "shared": list(entry.get("shared") or []),      # rule ids (rule) / [teacher uid] (teacher)
        "significance": sig,
    }
    ideas = behavior.spawn_ideas_for(
        LifeEventKind.THEOREM.value,                    # the same life:theorem -> post pipeline
        source=f"digest:{key}:{entry['generation']}",   # unique per flush (idempotency key)
        material=material,
        urge_scale=sig,
    )
    entry["theorem_ids"] = []
    entry["subjects"] = []
    return ideas[0] if ideas else None


# ADMIT a freshly-minted theorem's post decision into the digest buffer on `bs`. Returns "post"
# (the key's FIRST occurrence — its reasoning is news, let the 1:1 post proceed) or "buffered" (a
# repetition — accumulated, no 1:1). Mutates + SAVES bs (the caller's coordinator object). A
# count-cap hit flushes the entry in place (no monster posts). Pure-ish: driven directly by tests.
def digest_admit(bs: TKBrainStateDoc, key: str, kind: str, theorem_id: Optional[str],
                 original: str, shared: list, significance: float) -> str:
    buf = dict(bs.digest_buffer or {})
    entry = buf.get(key)
    if entry is None:
        # first occurrence: open the entry (empty) as the "seen" marker and post 1:1.
        buf[key] = {"kind": kind, "theorem_ids": [], "subjects": [], "shared": list(shared or []),
                    "opened_at": int(time.time()), "generation": 0,
                    "significance": float(significance)}
        bs.digest_buffer = buf
        bs.save()
        return "post"
    entry.setdefault("theorem_ids", []).append(theorem_id or "")
    entry.setdefault("subjects", []).append(original)
    entry["significance"] = max(float(entry.get("significance") or 0.0), float(significance))
    if len(entry["theorem_ids"]) >= DIGEST_COUNT_CAP:
        _flush_digest_entry(key, entry)  # a full entry ships now
    bs.digest_buffer = buf
    bs.save()
    return "buffered"


# FLUSH the whole buffer — one cumulative digest post per entry that accumulated anything, then
# clear those entries' accumulation (the entries persist as "seen"). The sleep-onset goodnight
# summary + the boot recovery of an interrupted night both call this. Returns how many posts spawned.
def flush_digests(bs: TKBrainStateDoc) -> int:
    buf = dict(bs.digest_buffer or {})
    if not buf:
        return 0
    n = 0
    for key, entry in buf.items():
        if _flush_digest_entry(key, entry) is not None:
            n += 1
    bs.digest_buffer = buf
    bs.save()
    if n:
        logger.info("[digest] flushed %d cumulative post(s) from the digest buffer", n)
    return n


# SPAWN the life:theorem trigger for a genuinely-NEW postable theorem (the third trigger namespace,
# blog P1). source = the THEOREM doc id — NOT a memory item — so behavior._source_memory resolves
# None and effective_urge sees directedness 1.0: self-expression is never scaled down by addressing
# (posts are additionally addressing-exempt in Priorities via the PUBLIC channel).
#
# THE DIGEST GATE (2026-07-21): when a brain_state is in hand (the live coordinator always threads
# it; tests opt in), a REPEATED reasoning shape (same wondering rule / same teacher, past its first
# occurrence) is BATCHED into the digest buffer instead of posting 1:1 (digest_classify/digest_admit
# above). No brain_state (an un-threaded caller / a unit test) -> the historical 1:1 behavior.
def _spawn_life_theorem(theorem_id: Optional[str], original: str, derived_by: str,
                        premises: list, chain: str, personal: bool,
                        bs: Optional[TKBrainStateDoc] = None) -> None:
    sig = life_theorem_significance(derived_by, chain, personal)
    if bs is not None:
        classified = digest_classify(derived_by, premises)
        if classified is not None:
            key, kind, shared = classified
            if digest_admit(bs, key, kind, theorem_id, original, shared, sig) == "buffered":
                return  # a repetition — batched, no 1:1 post
            # a FIRST occurrence falls through to the normal 1:1 post below (its reasoning is news)
    behavior.spawn_ideas_for(
        LifeEventKind.THEOREM.value,
        source=theorem_id,
        material={
            "kind": "theorem",
            "theorem_id": theorem_id,
            "original": original,
            "derived_by": derived_by,
            "premises": list(premises or []),
            "chain": [chain] if chain else [],
            "significance": sig,
        },
        urge_scale=sig,
    )


# materialize a forward-chained truth as an ACTIVE theorem. SILENT learning (no idea/action) — it
# grows the KB, it does not speak. Idempotent by `original` (silence = consent: a re-derived truth
# already known is not re-stored). Caching the demonstrated conclusion lets future evals match it
# geometrically instead of re-deriving it every time. Returns True iff a NEW theorem was written.
def materialize_theorem(result: EvaluatorResult, item: TKMemoryItemDoc, derived_by: str = "thinking",
                        bs: Optional[TKBrainStateDoc] = None) -> bool:
    if item.zip is None or not _derived_theorem(result):
        return False
    # INTEGRITY INVARIANT: a derived theorem MUST rest on KB premises — only RULE/FACT derivations are
    # materialized (pure-taxonomic verdicts are already in the graph, never theorems). a premise-less
    # "derivation" should be structurally impossible; refuse it rather than store an unprovenanced
    # theorem. this keeps the proof object honest: every stored theorem can point back at what it rests on.
    if not result.premises:
        logger.warning("[thinking] refusing to materialize «%s» — derived but NO premises (invariant breach)", item.original)
        return False
    # DEIXIS NORMALIZATION at the knowledge boundary: the item's surface string is the SPEAKER's
    # utterance, so speaker-relative pronouns must be rewritten before the sentence becomes a held
    # belief (the zip is already perspective-resolved — this keeps `original` consistent with it).
    # The speaker is item.sourceId (both uid and doc-id currencies circulate → resolve_canonical).
    # A non-me speaker normalizes against their name; tokeniko's own speech or an unresolvable
    # speaker passes through ONLY deictic-free (speaker_name=None: deictics with no fixable
    # perspective → refuse). None → remembered, not believed — the memory item stays either way.
    speaker = trust.resolve_canonical(item.sourceId)
    speaker_name = speaker.name if (speaker is not None and not speaker.isMe) else None
    # the vocative is ADDRESS, not content («tokeniko, a coin has value») — strip it before the
    # perspective pass (the zip never carried it; this keeps `original` consistent with the zip).
    norm = normalize_deixis(strip_vocative(item.original, get_tokeniko().name), speaker_name)
    if norm is None:
        logger.info("[thinking] derived «%s» not normalizable (deixis) — remembered, not believed",
                    item.original)
        return False
    if TKTheoremDoc.find_one({"original": norm}).run() is not None:
        return False  # already a theorem — dedup by (normalized) original
    chain = next(d for d in result.derivation if d.startswith(_CHAIN_PREFIX))
    # provenance gate (blog P1): the perceived item is PART of the derivation, so a DM-sourced item
    # taints the theorem — stored (knowledge is knowledge) but never fed to the public channel.
    postable = not _is_dm(item)
    theorem = TKTheoremDoc(
        original=norm,
        zip=item.zip,
        sourceId=str(get_tokeniko().id),  # tier-2: tokeniko derived it — speaker-irrelevant
        channel=MEMChannels.INTERNAL,
        archived=False,                   # ACTIVE (model default is archived=True) -> joins reasoning
        # min-trust inheritance: a derivation through a low-trust tier edge is stored honestly low-trust,
        # never laundered to the 0.9 default (truth ⟂ trust).
        trusted=evaluation_harness._conclusion_trust(result.premises),
        provenance=MEMProvenance(premises=result.premises, chain=chain, derived_by=derived_by),
        postable=postable,
    )
    theorem.save()
    logger.info("[thinking] derived THEOREM «%s» <- %s (premises=%s)", norm, chain, result.premises)
    # life:theorem (blog P1): a genuinely-NEW postable theorem is a noteworthy life event. The
    # learning itself stays silent toward the SOURCE conversation; this is a separate self-expression
    # urge on the PUBLIC channel, arbitrated by Priorities like any idea.
    if postable:
        _spawn_life_theorem(str(theorem.id), norm, derived_by,
                            result.premises, chain, _is_personal(item.zip, norm), bs=bs)
    return True


# THE DREAM (§0 slice 3, the author's ruling): the untangler's report is how he tells the blog he
# had a DREAM — «while I slept, I untangled something: I no longer believe X, and here is why».
# Called by scripts/untangle.py after an --apply pass with convictions. The provenance gate holds
# in the dream too: only POSTABLE retractions are narrated (a DM-taught premise never dreams
# publicly); all excluded -> no dream idea at all (he keeps that night to himself). Significance
# is flat-high (an ENCOUNTER-style rare event: a belief revision during sleep is personal by
# nature); the PUBLIC channel is addressing-exempt, so the idea rides unscaled to Priorities.
DREAM_SIGNIFICANCE = 0.9


def spawn_dream(report: dict) -> bool:
    import hashlib
    retracted, seen = [], set()
    for c in report.get("convicted", []):
        # one premise may convict several absurdities (the same stale belief poisons many
        # subjects) — it is still ONE belief let go: dream it once, first absurd as the why.
        if c.get("postable", True) and c["original"] not in seen:
            seen.add(c["original"])
            retracted.append({"original": c["original"], "absurd": c["absurd"],
                              "guess": bool(c.get("guess"))})
    if not retracted:
        return False
    seed = "|".join(r["original"] for r in retracted)
    source = "dream:" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]  # idempotent per night
    ideas = behavior.spawn_ideas_for(
        LifeEventKind.DREAM.value,
        source=source,
        material={
            "kind": "dream",
            "retracted": retracted,
            "asked": len(report.get("asked", [])),
            "significance": DREAM_SIGNIFICANCE,
        },
        urge_scale=DREAM_SIGNIFICANCE,
    )
    if ideas:
        logger.info("[dream] the night's untangling -> dream idea (%d retraction(s), %d open)",
                    len(retracted), len(report.get("asked", [])))
    return bool(ideas)


# --------------------------------------------------------------
# THE OBSERVATION-FACT SEAM (2026-07-17): an eval:false verdict IS an observation — the speaker
# said something false. Mint it silently as a tier-2 theorem «<name> said false» via the
# parser-free zip-native reportative assembly (lib/core/zip_native.py): matrix (uid, state.v.01)
# + THAT complement (uid, false.a.01) — the SAME senses the taught «a person is wrong if he says
# false» rule extracts (aligned by construction, probed 2026-07-17) — so extract_facts'
# predicative-reportative branch feeds the chainer and the taught rule can FIRE on the next KB
# load. LOCAL write (the materialize_theorem precedent): the observation must not depend on the
# api process (the brain's only hard dependency stays MongoDB). Trust: "X said s" is
# eyewitness-certain (the memory item IS the evidence), "s is false" is only as strong as the
# refutation -> min = the refutation's conclusion trust; a premise-less FALSE (nothing to price
# it with) honestly skips. Idempotent by `original` — one "has said false" per speaker suffices;
# repeat offenses are the trust ledger's business, not the KB's.
# --------------------------------------------------------------
_OBS_SAY_SENSE = "state.v.01"    # what «said» compiles to — rule and mint sides share the pipeline
_OBS_FALSE_SENSE = "false.a.01"  # what «false» compiles to


def record_observation(item: TKMemoryItemDoc, result: EvaluatorResult) -> bool:
    speaker = trust.resolve_canonical(item.sourceId)
    if speaker is None or speaker.isMe or not speaker.uid:
        return False  # self-falsehoods are belief-revision territory, never observations
    if not result.premises:
        return False  # an unpriceable refutation grounds no observation
    original = f"{speaker.name} said false"
    if TKTheoremDoc.find_one({"original": original, "archived": False}).run() is not None:
        return False  # already observed (a re-mint under a rename is harmless — same uid inside)
    native = assemble_reportative_zip(speaker.uid, _OBS_SAY_SENSE, _OBS_FALSE_SENSE)
    if native is None:
        logger.warning("[thinking] observation unassemblable (uid=%s) — skipped", speaker.uid)
        return False
    chain = f"observation: «{item.original}» refuted -> {original}"
    theorem = TKTheoremDoc(
        original=original,
        zip=native,
        sourceId=str(get_tokeniko().id),  # tier-2: tokeniko observed it himself
        channel=MEMChannels.INTERNAL,
        archived=False,                   # ACTIVE -> joins reasoning on the next KB load
        trusted=evaluation_harness._conclusion_trust(result.premises),
        provenance=MEMProvenance(premises=list(result.premises) + [f"observed:{item.id}"],
                                 chain=chain, derived_by="observation"),
        postable=not _is_dm(item),        # provenance gate (blog P1): DM evidence never public
    )
    theorem.save()
    logger.info("[thinking] OBSERVATION «%s» <- %s", original, chain)
    return True


# --------------------------------------------------------------
# THE TEACHING CHANNEL (D P3 — TIER-1, the deferred D1b branch alive). A trusted speaker's novel
# assertion becomes KNOWLEDGE: an eval:UNKNOWN item (not KB-derivable, logic-clean by construction —
# INCONSISTENT would have been the verdict) from a soul at/above the teach bar materializes as a
# TAUGHT theorem. Below the bar it stays remembered-not-believed (the memory item is the episodic
# record either way — he remembers you SAID it without believing it).
#   - trusted = min(teacher_trust, 0.9): taught knowledge is capped below axiom level — the 1.0
#     axiom tier stays the author's API privilege; a theorem is revisable.
#   - sourceId = the TEACHER's soul (tier-1 is speaker-RELEVANT, unlike a derived tier-2 theorem).
#   - provenance premise "taught:<soul_uid>" — a stable revocation key: if a teacher is ever
#     disgraced, revoke_dependents(["taught:<uid>"]) cascade-archives everything they taught.
#   - unknown vocabulary never becomes knowledge (a wug stays a wug).
# Self-healing under contradiction: once taught, a later contradicting claim grounds FALSE against
# the theorem (not UNKNOWN), so it is never double-taught — it costs the speaker trust instead.
# --------------------------------------------------------------
_TEACH_BAR = 0.9


# the TEACHABILITY pre-check (NO write) — the exact gates materialize_taught enforces, shared so
# the decision site (think_one -> eval:novel, the B-wire) and the executor's mint always agree.
# Returns (soul, norm, teacher_trust) for a teachable novel lesson, else None.
def _taught_candidate(item: TKMemoryItemDoc):
    if item.zip is None:
        return None
    leaves = evaluation_harness._zip_leaves(item.zip.items)
    if not leaves or any(getattr(leaf, "unknown", False) for leaf in leaves):
        return None  # unknown vocabulary never becomes knowledge
    # a HEADLESS leaf (no subject sense, no subject identity — an ambient unresolved «you», a
    # fragment) asserts nothing about anyone: never knowledge (the coreference gate's belt,
    # 2026-07-18 — the mammal incident's taught «so I am a mammal» came through here).
    if any(not ((getattr(l, "senses", None) or {}).get("subject")
                or (getattr(l, "identities", None) or {}).get("subject")) for l in leaves):
        return None
    soul = trust.resolve_canonical(item.sourceId)
    if soul is None or soul.isMe:
        return None
    teacher_trust = 1.0 if soul.imprint else soul.trust
    if teacher_trust < _TEACH_BAR:
        return None  # remembered, not believed
    # DEIXIS NORMALIZATION at the knowledge boundary: the lesson's surface string is the TEACHER's
    # utterance — «I am your creator» held verbatim would flip meaning the moment tokeniko re-utters
    # it ("I" would mean HIM). The zip is already perspective-resolved (identities carry the
    # teacher's uid); normalizing `original` here keeps the dedup key + NL render source consistent
    # with it. Unnormalizable (a deictic the conservative table can't fix) → refuse the belief; the
    # memory item is the episodic record either way (remembered, not believed).
    # vocative first (address, not content), then perspective — both boundary passes, one norm.
    norm = normalize_deixis(strip_vocative(item.original, get_tokeniko().name), soul.name)
    if norm is None:
        logger.info("[thinking] taught «%s» not normalizable (deixis) — remembered, not believed",
                    item.original)
        return None
    existing = TKTheoremDoc.find_one({"original": norm}).run()
    if existing is not None and not (
            not existing.archived
            and getattr(existing.provenance, "derived_by", "") == "hypothesis"):
        return None  # already knowledge — dedup by (normalized) original
    # an ACTIVE hypothesis row is PROMOTABLE, not a duplicate (slice 5: corroboration by a
    # trusted teacher turns the guess into taught knowledge — materialize_taught upgrades it)
    return soul, norm, teacher_trust


# the MINT (survey slice 3, the B-wire): called by the learn EXECUTOR (brain/main._execute_learn)
# — never inline from think_one anymore: whether tokeniko accepts teaching is the eval:novel ->
# tokeniko:learn behavior rule (KB personality; no rule = a mind that doesn't learn from others).
# Returns the normalized original on a real mint, None on refusal (the candidate re-check makes
# the executor race-safe: a lesson learned by any other path meanwhile dedups to an honest no-op).
def materialize_taught(item: TKMemoryItemDoc,
                       bs: Optional[TKBrainStateDoc] = None) -> Optional[str]:
    cand = _taught_candidate(item)
    if cand is None:
        return None
    soul, norm, teacher_trust = cand
    # THE PROMOTION (slice 5, the analytic/synthetic seam): an active hypothesis row holding
    # this very sentence is corroborated — the guess becomes taught knowledge IN PLACE (same
    # doc, trust raised to the teacher's, provenance rewritten with the promotion recorded).
    # DM-taint stays conservative: one private premise poisons postability (constitution).
    existing = TKTheoremDoc.find_one({"original": norm}).run()
    if existing is not None:
        if existing.archived or getattr(existing.provenance, "derived_by", "") != "hypothesis":
            return None  # raced: became knowledge (or fell) since the candidate check
        chain = (f"taught by {soul.name} ({soul.uid}) at trust {teacher_trust:.2f} — "
                 f"promoted from hypothesis ({existing.provenance.chain})")
        existing.trusted = min(teacher_trust, 0.9)
        existing.sourceId = str(soul.id)
        existing.postable = bool(existing.postable) and not _is_dm(item)
        existing.provenance = MEMProvenance(
            premises=[f"taught:{soul.uid}"], chain=chain, derived_by="teaching")
        existing.save()
        logger.info("[thinking] PROMOTED hypothesis -> taught: «%s» <- %s (trust %.2f)",
                    norm, soul.uid, teacher_trust)
        if existing.postable:
            _spawn_life_theorem(str(existing.id), norm, "teaching",
                                [f"taught:{soul.uid}"], chain, _is_personal(item.zip, norm), bs=bs)
        return norm
    # provenance gate (blog P1): a lesson given in PRIVATE (a Discord DM) is learned but never
    # published — "DM never public" is constitution-level.
    postable = not _is_dm(item)
    chain = f"taught by {soul.name} ({soul.uid}) at trust {teacher_trust:.2f}"
    theorem = TKTheoremDoc(
        original=norm,
        zip=item.zip,
        sourceId=str(soul.id),            # tier-1: the TEACHER — speaker-relevant knowledge
        channel=MEMChannels.INTERNAL,
        archived=False,                   # ACTIVE — joins reasoning
        trusted=min(teacher_trust, 0.9),  # capped below the axiom tier
        provenance=MEMProvenance(
            premises=[f"taught:{soul.uid}"],
            chain=chain,
            derived_by="teaching",
        ),
        postable=postable,
    )
    theorem.save()
    logger.info("[thinking] TAUGHT theorem «%s» <- %s (trust %.2f)", norm, soul.uid, teacher_trust)
    # life:theorem (blog P1): being TAUGHT something new is a noteworthy life event (significance
    # carries the teaching bump) — postable lessons only. NOTE the normalized original feeds
    # _is_personal too: a taught "you are kind" → "I am kind" correctly reads personal ("I " prefix).
    if postable:
        _spawn_life_theorem(str(theorem.id), norm, "teaching",
                            [f"taught:{soul.uid}"], chain, _is_personal(item.zip, norm), bs=bs)
    return norm


# --------------------------------------------------------------
# THE HYPOTHESIS ENGINE (survey slice 5, the author-approved design 2026-07-19): a GUESS is
# CHARITABLE BELIEF WITH EVIDENCE — the speaker's ungroundable claim held provisionally when
# (1) it still grades UNKNOWN at execution time (non-refutation: a FALSE kills the guess, a
# TRUE needs no guessing) and (2) it geometrically RESEMBLES something already held
# (relationMatch >= the floor — the fuzzy layer doing induction: geometry proposes
# plausibility, the symbolic layer has already checked consistency). He invents nothing; he
# extends charity to what fits. A claim resembling nothing he knows stays merely remembered.
#
# The home is a THEOREM row (everything-is-KB, one reasoning surface): derived_by="hypothesis",
# trusted capped at HYPOTHESIS_TRUST — the containment already exists (the provenance cascade
# bounds every conclusion by min-premise-trust; verdict_confidence scales by it, so a speakup
# grounded in a guess speaks in the soft register by construction). The matched doc's id JOINS
# the premises: if the resembled belief ever falls, revoke_dependents takes the guess with it
# (the evidence died). SILENT formation (wondering's cousin — no idea, no post); the guess's
# DEATH gets the dream (the author's fork ruling — see untangle_pass + spawn_dream).
# Promotion (the analytic/synthetic seam): a trusted teacher later asserting the same sentence
# PROMOTES the row in materialize_taught — corroboration turns a guess into knowledge.
# --------------------------------------------------------------
HYPOTHESIS_TRUST = float(os.getenv("HYPOTHESIS_TRUST", "0.3"))
HYPOTHESIS_RESEMBLANCE_FLOOR = float(os.getenv("HYPOTHESIS_RESEMBLANCE_FLOOR", "0.6"))


def materialize_hypothesis(item: TKMemoryItemDoc) -> Optional[str]:
    # every refusal names its bar (author-agreed 2026-07-21): 151 live guess firings had produced
    # zero hypothesis rows with no way to tell WHICH gate held — the reason turns a silent no-op
    # into diagnosis. Log lines only; the bar sequence itself is unchanged.
    def bar(reason: str) -> None:
        logger.info("[thinking] hypothesis bar held — %s («%s»)", reason,
                    str(item.original)[:80])

    if item.zip is None:
        bar("no zip")
        return None
    leaves = evaluation_harness._zip_leaves(item.zip.items)
    if not leaves or any(getattr(l, "unknown", False) for l in leaves):
        bar("unknown vocabulary")  # a wug stays a wug — never guessed into knowledge
        return None
    if any(not ((getattr(l, "senses", None) or {}).get("subject")
                or (getattr(l, "identities", None) or {}).get("subject")) for l in leaves):
        bar("headless leaf")  # the headless belt, same as teaching
        return None
    soul = trust.resolve_canonical(item.sourceId)
    if soul is None or soul.isMe:
        bar("no soul or self-talk")
        return None
    out = evaluate_zip(item.zip)
    if status_to_token(out["result"]) != EvalToken.UNKNOWN.value:
        bar(f"not UNKNOWN anymore ({status_to_token(out['result'])})")  # refuted or derivable meanwhile
        return None
    match = out.get("relationMatch")
    if match is None or match < HYPOTHESIS_RESEMBLANCE_FLOOR:
        # the measured value is the diagnostic gold: 0.55 vs the 0.6 floor is a tuning story,
        # None is a no-evidence story — charity needs evidence either way.
        bar("resembles nothing he holds" if match is None
            else f"resemblance {match:.2f} under the {HYPOTHESIS_RESEMBLANCE_FLOOR:.2f} floor")
        return None
    norm = normalize_deixis(strip_vocative(item.original, get_tokeniko().name), soul.name)
    if norm is None:
        bar("deixis not normalizable")
        return None
    if TKTheoremDoc.find_one({"original": norm}).run() is not None:
        bar("already knowledge or already guessed")
        return None
    speaker_trust = 1.0 if soul.imprint else soul.trust
    chain = (f"hypothesis: resembles «{out.get('matchedOriginal')}» at {match:.2f}; "
             f"said by {soul.name} ({soul.uid}) at trust {speaker_trust:.2f}")
    premises = [f"hypothesis:{soul.uid}"] + ([out["matchedId"]] if out.get("matchedId") else [])
    theorem = TKTheoremDoc(
        original=norm,
        zip=item.zip,
        sourceId=str(soul.id),
        channel=MEMChannels.INTERNAL,
        archived=False,
        trusted=min(speaker_trust, HYPOTHESIS_TRUST),
        provenance=MEMProvenance(premises=premises, chain=chain, derived_by="hypothesis"),
        # the flag follows the source (DM never public); a public-born guess may be DREAMED
        # when it dies (the author's ruling: the drop deserves a dream)
        postable=not _is_dm(item),
    )
    theorem.save()
    logger.info("[thinking] HYPOTHESIS held: «%s» (resembles «%s» at %.2f, trust %.2f)",
                norm, out.get("matchedOriginal"), match, theorem.trusted)
    return norm


# --------------------------------------------------------------
# BELIEF-REVISION v1 (retreat arc #4) — the correction path. A FALSE verdict may actually be THE
# BOUNCE (2026-07-14 bold-test finding): a quantified correction («not all softwares are minds»)
# evaluated against the very generalization it targets, refuted, and — worse — costing the CORRECTOR
# trust ("contradicts what I hold"). The detector (harness `correction_target`) recognizes the shape:
# an O/E-corner claim the active graph affirms through a LEARNED, doc-retractable hop.
#
# THE TRUST GATE (Popper, gated — the author's D2 ruling): one counterexample defeats a universal,
# but only from a corrector whose trust >= the belief's own trust tier — a stranger cannot demolish
# the imprinting (hunch 17: the gate is what keeps falsificationism from being a crowbar). Gate
# holds -> the normal eval:false + DISAGREEMENT path stands (scaled by belief trust, as ever).
#
# Gate passes -> the correction REPLACES refute-back entirely:
#   eval:correction  -> tokeniko:retreat (INTERNAL: archive source docs + revoke_dependents cascade
#                       + mint the weakened subaltern I — executed in actions_phase)
#   trust:correction -> more-trust (a valid correction is a LESSON, never a ding)
# and the caller must ALSO skip the cross-item conflict check for this item: a self-correction
# («actually, not all…» after teaching «all…») is deliberate revision — the very act this arc
# exists to honor — not the honest-liar's unwitting contradiction.
# --------------------------------------------------------------
def _try_correction(item: TKMemoryItemDoc) -> bool:
    ct = evaluation_harness.correction_target(item.zip)
    if ct is None:
        return False
    soul = trust.resolve_canonical(item.sourceId)
    if soul is None or soul.isMe:
        return False
    corrector_trust = 1.0 if soul.imprint else soul.trust
    if corrector_trust < ct["belief_trust"]:
        logger.info(
            "[thinking] correction detected on «%s» (%s-corner vs %s) but the trust gate holds "
            "(corrector %.2f < belief %.2f) — the belief stands",
            item.original, ct["corner"], " -> ".join(ct["path"]),
            corrector_trust, ct["belief_trust"],
        )
        return False
    answer = dict(ct)
    answer["corrector"] = soul.uid
    answer["corrector_trust"] = corrector_trust
    behavior.spawn_ideas_for(
        EvalToken.CORRECTION.value, payload=item.zip, source=str(item.id),
        answer=answer, target=item.sourceId,
    )
    behavior.spawn_ideas_for(
        TrustEpisodeKind.CORRECTION.value, payload=item.zip, source=str(item.id),
        answer={"note": f"a valid correction: {ct['corner']}-corner defeats "
                        f"«{ct['sources'][0]['original']}» (Popper, trust-gated)"},
        target=item.sourceId,
    )
    logger.info(
        "[thinking] CORRECTION accepted: «%s» (%s, corrector %.2f >= belief %.2f) -> retreat of %s",
        item.original, ct["corner"], corrector_trust, ct["belief_trust"],
        [s["original"] for s in ct["sources"]],
    )
    return True


# --------------------------------------------------------------
# THE REDUCT-ANSWER BINDING (§0 slice 2, the author's fork-A ruling) — the answer-form gap's cure.
# The correction detector consumes O/E CORNERS; but the natural answer to the reduct question is
# the GENERIC denial («a mind is not a software»), which is no corner — without this, tokeniko
# would push back on the answer to his own question (the bounce, inside the very conversation he
# opened). The CONTEXT disambiguates it, exactly as it does for humans: when the ASKED teacher
# (an OPEN reductio row's target) denies one of THAT row's premises (pinned senses match, net
# polarity flipped), the denial binds as a correction of that premise — same Popper trust gate,
# same downstream (retreat + cascade + concede; the next saturation resolves the row). Scoped
# three ways: only the asked teacher, only the asked premises, only while the row is OPEN.
# Corner "R"; weakened=None — a flat denial licenses no subaltern (the teacher said the belief is
# false, not that «some» survives): archive, mint nothing (epistemic caution). Readonly axioms
# stay non-retractable (the constitution, v1 rule); archived premises never re-bind.
# --------------------------------------------------------------

# a leaf's NET comparison key: (subject, predicate, direct, net-negation) — the net folds the
# surface split between negation-on-copula and negation-on-quantifier (NEGATIVE «no S is P»,
# NEGATED_UNIVERSAL «not all S are P»), so a denial matches its premise whichever way either
# was phrased. Each role keys by its WSD sense OR, failing that, its identity uid (the
# identity-bridge): an INDIVIDUAL-subject belief («so I am a mammal» — subject tokeniko, a uid,
# never a sense) is exactly what a reductio about HIMSELF rests on, and the teacher's addressed
# denial («you are not a mammal» — «you»→tokeniko) carries the same uid; sense-only keys left
# both sides None and the asked premise unmatchable (found live 2026-07-19: the answer bounced
# to clarify). Uid and sense strings live in disjoint formats — no cross-collision. None when a
# role has neither (an unresolved ambient «you» stays honestly unbindable — the coreference
# gate's caution is preserved, not bypassed).
def _leaf_net_key(leaf) -> Optional[tuple]:
    subj = role_key(leaf, "subject")
    pred = role_key(leaf, "predicate")
    if not subj or not pred:
        return None
    q = getattr(leaf, "quantifier", None)
    neg = bool(getattr(leaf, "negated", False)) != (
        q in (TKQuantifier.NEGATIVE, TKQuantifier.NEGATED_UNIVERSAL))
    return (subj, pred, role_key(leaf, "direct"), neg)


def _try_reduct_answer(item: TKMemoryItemDoc) -> bool:
    from lib.core.kb_extract import _leaf_is_crisp
    if item.zip is None:
        return False
    soul = trust.resolve_canonical(item.sourceId)
    if soul is None or soul.isMe:
        return False
    rows = TKReductioDoc.find(
        {"status": ReductioStatus.OPEN.value, "target": soul.uid}).to_list()
    if not rows:
        return False  # the cheap gate: no open question aimed at this speaker
    answer_keys = set()
    for leaf in evaluation_harness._zip_leaves(item.zip.items):
        if not _leaf_is_crisp(leaf):
            continue  # a ◇-claim asserts nothing — it answers nothing
        key = _leaf_net_key(leaf)
        if key:
            answer_keys.add(key)
    if not answer_keys:
        return False
    corrector_trust = 1.0 if soul.imprint else soul.trust
    for row in rows:
        for doc in _premise_docs(row.premises):
            if getattr(doc, "archived", False):
                continue  # already retreated — nothing left to bind
            if isinstance(doc, TKAxiomDoc) and getattr(doc, "readonly", True):
                continue  # the constitution is never conversationally retractable (v1)
            if doc.zip is None:
                continue
            for pleaf in evaluation_harness._zip_leaves(doc.zip.items):
                pk = _leaf_net_key(pleaf)
                if pk is None or (pk[0], pk[1], pk[2], not pk[3]) not in answer_keys:
                    continue
                # the context binds — same Popper gate as every correction
                if corrector_trust < doc.trusted:
                    logger.info(
                        "[thinking] reduct answer «%s» denies asked premise «%s» but the trust "
                        "gate holds (answerer %.2f < belief %.2f) — the belief stands",
                        item.original, doc.original, corrector_trust, doc.trusted)
                    return False
                kind = "axiom" if isinstance(doc, TKAxiomDoc) else "theorem"
                answer = {
                    "corner": "R",  # reduct-context binding (no square corner — the row is the context)
                    "corrector": soul.uid, "corrector_trust": corrector_trust,
                    "belief_trust": doc.trusted, "edge_keys": [],
                    "sources": [{"kind": kind, "id": str(doc.id), "original": doc.original}],
                    "weakened": None,
                    "signature": row.signature,  # audit: which absurdity this answer resolves
                }
                behavior.spawn_ideas_for(
                    EvalToken.CORRECTION.value, payload=item.zip, source=str(item.id),
                    answer=answer, target=item.sourceId,
                )
                behavior.spawn_ideas_for(
                    TrustEpisodeKind.CORRECTION.value, payload=item.zip, source=str(item.id),
                    answer={"note": f"answered my reductio: the denial retires "
                                    f"«{doc.original}» (context-bound, Popper trust-gated)"},
                    target=item.sourceId,
                )
                logger.info(
                    "[thinking] REDUCT ANSWER accepted: «%s» from %s retires asked premise «%s» "
                    "(answerer %.2f >= belief %.2f)",
                    item.original, soul.name, doc.original, corrector_trust, doc.trusted)
                return True
    return False


# --------------------------------------------------------------
# WONDERING (#4 D1c) — the lowest-priority REFLECTIVE pass. Where think_one REACTS to fresh memory,
# wonder_one RE-EXAMINES memory tokeniko has ALREADY lived through, *because the KB has grown since*:
# a new definition/axiom/theorem can make an old, once-INSUFFICIENT input now KB-derivable. It is
# SILENT — knowledge only: it spawns NO ideas and NO actions, and it does NOT cross-item-check; a
# re-derived truth is materialized straight into a theorem (materialize_theorem, which dedups by
# `original` — that is what makes wondering converge instead of churning).
#
# Two drivers feed the wonder_queue (work-item ids), drained ONE per idle tick:
#   ASSOCIATIVE (driver 1) — KB-CHANGE-GATED: when active knowledge created AFTER last_wondered_kb_at
#       appears, its senses pick out the memory items that touch it (the deltas to recheck). Targeted.
#   DRIFT (driver 2) — when the queue is empty and a throttle has elapsed, enqueue a small RANDOM
#       batch of past items. Covers items the associative driver missed (e.g. queue overflow) and
#       keeps idle wondering alive even when the KB is static.
#
# Cost is FLAT per tick regardless of history: the queue is capped (WONDER_QUEUE_CAP), the KB load is
# fingerprint-cached (evaluate_zip), and drift is throttled (DRIFT_INTERVAL) + bounded ($sample).
# Coordinator wiring (when wonder_one runs vs think_one) lives in brain/main.py — NOT here.


# the active-knowledge createdAt watermark, computed CHEAPLY (one indexed newest-first row per model,
# never a full .to_list()). mirrors kb_fingerprint's _count_and_max but returns only the max ts.
def _kb_max_createdat() -> int:
    mx = 0
    for model in (TKDefinitionDoc, TKAxiomDoc, TKTheoremDoc):
        newest = model.find({"archived": False}).sort("-createdAt").limit(1).to_list()
        if newest:
            mx = max(mx, newest[0].createdAt)
    return mx


# KB-WONDERING (#4 D3a) — the autonomous-derivation half of wondering. Where memory-wondering (below)
# re-examines lived MEMORY because the KB grew, KB-wondering forward-saturates the KB ITSELF — deriving
# what the rules+facts IMPLY but no one asserted ("matching memory against itself"). kb_wonder() returns
# the genuinely-new (>=2-premise, deduped) conclusions; each is RENDERED to NL and POSTed to the API,
# which compiles it into a first-class zip theorem carrying its proof. This is the seam by which "I
# exist" enters the world by tokeniko's OWN in-loop act (the reserved cogito), not by our hand.
#
# SILENT: a direct API call, NOT via the Actions phase — wondering grows knowledge, it does not speak.
# CONVERGENCE is by construction: materialize stores original = the rendered NL, so once a conclusion is
# materialized its render lands in `held` and is skipped forever after. ONE conclusion per tick (bounded,
# cooperative). FLAT-COST on the small KB; a future optimization can watermark-gate the re-saturation so
# it only runs when the KB changed (mirrors the associative driver) — not needed at current KB size.
#
# Returns True iff it materialized one new theorem this tick. On an unreachable/failed API it returns
# False (leave the conclusion for next tick — never advances past it, never churns a stored theorem).
#
# DEDUP HONESTY: materialize semantic-dedups server-side and returns the EXISTING theorem (status
# complete, no write). Its `original` differs from our render, so the render never enters `held` —
# without suppression the same conclusion would be re-"derived" every tick forever (the void spin,
# 2026-07-09 soak). A deduped render is recorded in _dedup_suppressed (per-process; re-derivation
# after a restart costs one round-trip, then re-suppresses) and the scan CONTINUES to the next
# conclusion, so the tick still does real work or honestly reports quiet.
_dedup_suppressed: set[str] = set()


# --------------------------------------------------------------
# THE REDUCTIO ACTION (roadmap §0 slice 1, 2026-07-18) — the other half of the r.a.a. The
# derivation mirror RECOGNIZES an absurd (a∧¬a in one chain: never materialized, never decides);
# these consumers turn it into a QUESTION to the premise-givers: «one of these must be false —
# if all were true I would conclude {absurd}. Which is the false assumption?» (clarify's
# derivational cousin). The resolution consumer is the EXISTING correction/retreat path: the
# natural answer («a is false») retreats the premise, the conflict vanishes from the next
# saturation, and the ledger row resolves — the r.a.a. closes through the door every other
# correction walks through. The reductio_ledger is the asked-once memory (one row per live
# contradicted conclusion), so the same conflict re-surfacing every wondering pass never re-asks.
# --------------------------------------------------------------

# Fork B (author's ruling): ONE question, aimed at the most trusted premise-giver of the pair —
# the external souls behind the resolvable premise docs; when none is external (graph edges,
# self-derived theorems), the KB's gardener: the most-trusted external soul with a channel route.
# The carrier's destination fallback (senses/outbound) DMs via the contextKey — provenance-safe
# by construction (a DM never leaks a premise to a shared room).
def _reduct_target(premise_docs) -> Optional[TKMemoryStakeholdersDoc]:
    souls: dict[str, TKMemoryStakeholdersDoc] = {}
    for doc in premise_docs:
        src = getattr(doc, "sourceId", None)
        if not src:
            continue
        soul = trust.resolve_canonical(str(src))
        if soul is not None and not getattr(soul, "isMe", False):
            souls[soul.uid] = soul
    if not souls:  # the gardener fallback: every reachable external soul, most trusted first
        for soul in TKMemoryStakeholdersDoc.find(
            {"isMe": {"$ne": True}, "kind": {"$ne": "individual"}}
        ).to_list():
            if soul.contextKey and ":" in soul.contextKey:
                souls[soul.uid] = soul
    if not souls:
        return None
    return max(souls.values(),
               key=lambda s: (bool(getattr(s, "imprint", False)), getattr(s, "trust", 0.0)))


# the rendered absurd pair — both polarities of the contradicted conclusion, joined. This is the
# {absurd} the question names («kotekino is an animal and kotekino is not an animal»).
def _conflict_absurd(c: dict) -> Optional[str]:
    pos = evaluation_harness.render_conclusion(
        c["subject"], c["predicate"], c.get("object"), False, c["subject_kind"])
    neg = evaluation_harness.render_conclusion(
        c["subject"], c["predicate"], c.get("object"), True, c["subject_kind"])
    if pos and neg:
        return f"{pos.rstrip('.')} and {neg.rstrip('.')}"
    return None


# reconcile the ledger against THIS pass's full conflict set (kb_wonder saturates every seed, so
# the set is complete per tick): open rows whose signature vanished are RESOLVED (a premise was
# retreated — the r.a.a. closed); new signatures spawn eval:absurdity (rule-gated); a signature
# returning after resolution re-opens at generation+1 (the spawn-dedup key changes -> re-asked).
def _reductio_reconcile(conflicts: list[dict]) -> None:
    groups: dict[str, dict] = {}
    for c in conflicts:  # the two polarity twins of one incident share the signature — union them
        sig = f"{c['subject']}|{c['predicate']}|{c.get('object') or ''}"
        g = groups.setdefault(sig, {"c": c, "premises": set()})
        g["premises"].update(str(p) for p in c.get("premises", []))

    now = int(time.time())
    open_rows = TKReductioDoc.find({"status": ReductioStatus.OPEN.value}).to_list()
    for row in open_rows:
        if row.signature not in groups:
            row.status = ReductioStatus.RESOLVED
            row.resolvedAt = now
            row.save()
            logger.info("[reductio] RESOLVED «%s» — the conflict is gone from the saturation "
                        "(a premise retreated; the r.a.a. closed)", row.absurd or row.signature)
    open_sigs = {r.signature for r in open_rows if r.status == ReductioStatus.OPEN}

    new_sigs = [s for s in groups if s not in open_sigs]
    if not new_sigs:
        return
    if not behavior.behavior_for(EvalToken.ABSURDITY.value):
        logger.warning("[reductio] %d unasked conflict(s) but no enabled eval:absurdity rule — "
                       "the question stays unledgered until the personality learns the reflex",
                       len(new_sigs))
        return
    for sig in new_sigs:
        g = groups[sig]
        absurd = _conflict_absurd(g["c"])
        premise_ids = sorted(g["premises"])
        docs = _premise_docs(premise_ids)
        sentences = list(dict.fromkeys(d.original.strip() for d in docs))  # unique, order kept
        if not absurd or not sentences:
            logger.warning("[reductio] conflict %s not askable (absurd=%s, nameable premises=%d) "
                           "— left to the untangler", sig, bool(absurd), len(sentences))
            continue
        target = _reduct_target(docs)
        row = TKReductioDoc.find_one({"signature": sig}).run()  # Bunnet: .run() executes
        if row is None:
            row = TKReductioDoc(signature=sig, premises=premise_ids, absurd=absurd,
                                target=target.uid if target else None)
            row.insert()
        else:  # resolved before, the poison returned — re-open one generation up (re-asked)
            row.status = ReductioStatus.OPEN
            row.generation += 1
            row.premises = premise_ids
            row.absurd = absurd
            row.target = target.uid if target else None
            row.resolvedAt = None
            row.save()
        ideas = behavior.spawn_ideas_for(
            EvalToken.ABSURDITY.value,
            source=f"reductio:{row.id}:{row.generation}",  # per-asking-round dedup key
            answer={"premises": sentences, "absurd": absurd,
                    "premise_ids": premise_ids, "signature": sig},
            target=target.uid if target else None,
            confidence=1.0,  # the r.a.a. is logic — logic never hedges
        )
        if ideas:
            logger.warning("[reductio] ABSURD «%s» — asking %s which premise is false "
                           "(%d nameable: %s)", absurd,
                           target.name if target else "nobody-reachable",
                           len(sentences), "; ".join(f"«{s}»" for s in sentences))


# THE MORNING QUESTIONS (author's ruling 2026-07-18, the obsession guard): waking up with a
# tangle the night could NOT decide is itself a reason to ask — whether he asked before or not.
# An old question drowns in the message stream; silently re-discovering the same absurd every
# night would be a quiet fixation. For each stashed undecidable signature whose ledger row is
# still OPEN, spawn a fresh reduct question with a per-night dedup key (the asked-once
# discipline holds WITHIN a night; each new sighting re-asks). Rows resolved while he slept
# (the answer landed overnight) are skipped honestly. Returns how many questions were asked.
def ask_morning_questions(stash: dict) -> int:
    signatures = list((stash or {}).get("signatures") or [])
    night = int((stash or {}).get("at") or 0)
    if not signatures or not behavior.behavior_for(EvalToken.ABSURDITY.value):
        return 0
    asked = 0
    for sig in signatures:
        row = TKReductioDoc.find_one(
            {"signature": sig, "status": ReductioStatus.OPEN.value}).run()  # Bunnet: .run()
        if row is None:
            continue  # resolved (or never ledgered) — nothing left to ask
        docs = _premise_docs(row.premises)
        sentences = list(dict.fromkeys(d.original.strip() for d in docs
                                       if not getattr(d, "archived", False)))
        if not row.absurd or not sentences:
            continue  # nothing nameable anymore — left to the untangler
        target = _reduct_target(docs)
        ideas = behavior.spawn_ideas_for(
            EvalToken.ABSURDITY.value,
            source=f"reductio:{row.id}:{row.generation}:night:{night}",  # per-night dedup key
            answer={"premises": sentences, "absurd": row.absurd,
                    "premise_ids": list(row.premises), "signature": sig},
            target=target.uid if target else row.target,
            confidence=1.0,  # the r.a.a. is logic — logic never hedges
        )
        if ideas:
            asked += 1
            logger.warning("[reductio] MORNING QUESTION «%s» — still tangled after the night, "
                           "asking %s again", row.absurd,
                           target.name if target else row.target or "nobody-reachable")
    return asked


def _kb_wonder_one(bs: Optional[TKBrainStateDoc] = None) -> bool:
    conflicts: list[dict] = []
    conclusions = evaluation_harness.kb_wonder(collect_conflicts=conflicts)
    try:  # ledger trouble must never kill the wondering tick
        _reductio_reconcile(conflicts)
    except Exception as error:
        logger.error("[reductio] reconcile failed (%s) — wondering continues", error)
    if not conclusions:
        return False
    # `held` needs only the original strings — project them (a full .to_list() would pull every
    # active theorem's zip, tens of MB per tick, for a set of strings).
    held = {
        row["original"]
        for row in TKTheoremDoc.get_motor_collection().find(
            {"archived": False}, {"original": 1, "_id": 0}
        )
        if row.get("original")
    }
    n_held_skip = 0
    for c in conclusions:
        nl = evaluation_harness.render_conclusion(
            c["subject"], c["predicate"], c.get("object"), c.get("negated", False), c["subject_kind"]
        )
        if not nl or nl in held or nl in _dedup_suppressed:
            n_held_skip += 1
            continue  # unrenderable, or this conclusion is already a held theorem -> converged
        chain = _CHAIN_PREFIX + c["chain"]  # same proof convention as the memory-wondering path
        # ZIP-NATIVE (instrument arc #2): the conclusion's STRUCTURE is the thought — the API
        # assembles the zip directly from it; the render above is only the human label. No parser
        # in the belief path, nothing to pin.
        structure = {"subject": c["subject"], "predicate": c["predicate"],
                     "object": c.get("object"), "negated": c.get("negated", False),
                     "subject_kind": c["subject_kind"]}
        # provenance gate (blog P1): postability = the AND over the conclusion's premise theorems —
        # one DM-tainted (postable=False) premise poisons the conclusion; axioms/graph edges pass.
        postable = _premises_postable(c["premises"])
        resp = api_client.materialize_theorem(nl, c["premises"], chain, derived_by="wondering",
                                              trusted=c.get("trust", 0.9), structure=structure,
                                              postable=postable)
        if resp is None or resp.get("status") != "complete":
            logger.warning("[wondering] KB-derive «%s» — API unavailable/failed, will retry", nl)
            return False  # leave it for next tick (not in `held`, so it is re-attempted)
        data = resp.get("data") or {}
        stored = data.get("original")
        if stored and stored != nl:
            _dedup_suppressed.add(nl)
            logger.info("[wondering] KB-derive «%s» deduped onto held «%s» — suppressed", nl, stored)
            continue  # the conclusion is already held under other wording; keep scanning this tick
        logger.info("[wondering] KB-derived THEOREM «%s» <- %s (premises=%s)", nl, chain, c["premises"])
        # life:theorem (blog P1): reaching here means a genuinely-NEW theorem was written (a held
        # render was skipped above; a semantic dedup took the `stored != nl` branch). Personal =
        # an individual-seeded conclusion about a known soul, or about tokeniko himself.
        if postable:
            personal = nl.startswith("I ") or (
                c["subject_kind"] == "individual" and trust.resolve_canonical(c["subject"]) is not None
            )
            theorem_id = str(data.get("_id") or data.get("id") or "")
            _spawn_life_theorem(theorem_id or None, nl, "wondering", c["premises"], chain,
                                personal, bs=bs)
        return True  # one bounded unit per tick
    logger.info("[wondering] KB-wonder quiet: %d conclusions, all %d already held (converged)",
                len(conclusions), n_held_skip)
    return False  # every derivable conclusion already held -> KB-wondering is quiet


# Returns the tick's FRUITFULNESS (the sleep phase reads it): "derived" = new knowledge entered
# the KB (resets the sleep clock); "checked" = a re-examination that found nothing new (a unit of
# work, but the mind is running dry — without this distinction the drift driver's random batches
# would count as fruit forever and he could never fall asleep); False = nothing to do at all.
# Both strings are truthy, so every boolean caller keeps its old behavior.
def wonder_one(brain_state: TKBrainStateDoc):
    # 0. KB-WONDERING FIRST — derive what the KB implies and materialize ONE new theorem (the cogito's
    #    autonomous birth). When it has nothing new (converged), fall through to memory-wondering below.
    if _kb_wonder_one(bs=brain_state):
        return "derived"

    # 1. FIRST-RUN GUARD. Anchor the associative watermark at "now" so the entire seeded KB is not
    #    one giant delta on first wonder (mirrors think_one's wake_at first-run guard). No work yet.
    if brain_state.last_wondered_kb_at == 0:
        brain_state.last_wondered_kb_at = _kb_max_createdat() or int(time.time())
        brain_state.save()
        return False

    queue = list(brain_state.wonder_queue or [])

    # 2. ASSOCIATIVE ENQUEUE — active DELTA knowledge created after the watermark drives a re-check
    #    of the memory items whose senses overlap the delta's senses.
    delta_docs = []
    for model in (TKDefinitionDoc, TKAxiomDoc, TKTheoremDoc):
        delta_docs += model.find(
            {"archived": False, "createdAt": {"$gt": brain_state.last_wondered_kb_at}}
        ).to_list()
    if delta_docs:
        delta_senses: set[str] = set()
        for d in delta_docs:
            if d.zip is not None:
                delta_senses.update(evaluation_harness.zip_senses(d.zip))
        # advance the watermark past every delta doc we just serviced.
        brain_state.last_wondered_kb_at = max(
            brain_state.last_wondered_kb_at, max(d.createdAt for d in delta_docs)
        )
        if delta_senses:
            touched = (
                TKMemoryItemDoc.find({"senses": {"$in": list(delta_senses)}})
                .sort("-timestamp")
                .to_list()
            )
            in_queue = set(queue)
            dropped = 0
            for it in touched:
                sid = str(it.id)
                if sid in in_queue:
                    continue
                if len(queue) >= WONDER_QUEUE_CAP:
                    dropped += 1  # overflow — drift will sweep it up later
                    continue
                queue.append(sid)
                in_queue.add(sid)
            if dropped:
                logger.info("[wondering] associative: dropped %d over cap (queue=%d)", dropped, len(queue))
        brain_state.wonder_queue = queue
        brain_state.save()
        logger.info(
            "[wondering] associative: delta=%d senses=%d -> queued (queue=%d)",
            len(delta_docs), len(delta_senses), len(queue),
        )

    # 3. DRIFT ENQUEUE — only when there is no associative work pending. Throttled, and bounded by a
    #    Mongo $sample aggregation (random regardless of history size, no full scan).
    if not queue:
        now = int(time.time())
        last = brain_state.last_wondering_at
        if last is None or now - last >= DRIFT_INTERVAL:
            sampled = TKMemoryItemDoc.get_motor_collection().aggregate(
                [{"$match": {"zip": {"$ne": None}}},
                 {"$sample": {"size": DRIFT_BATCH}},
                 {"$project": {"_id": 1}}]
            )
            for row in sampled:
                queue.append(str(row["_id"]))
            # advance the drift throttle on every RUN — NOT only when an item is later processed
            # (step 4). On an EMPTY memory the sample returns 0, no item is ever processed, so
            # last_wondering_at would never advance and drift would re-fire every idle tick (the
            # empty-memory drift spin — surfaced by the first soak). Stamping it here engages the
            # DRIFT_INTERVAL throttle regardless, so idle drift checks at most once per interval.
            brain_state.last_wondering_at = now
            brain_state.wonder_queue = queue
            brain_state.save()
            logger.info("[wondering] drift: queued %d random", len(queue))
        if not queue:
            return False  # nothing to do (no delta, drift throttled/empty)

    # 4. PROCESS ONE queued item. Pop + persist the cursor FIRST so a crash mid-eval doesn't re-pop it.
    item_id = queue.pop(0)
    brain_state.wonder_queue = queue
    brain_state.last_wondering_at = int(time.time())
    brain_state.save()

    try:
        oid = ObjectId(item_id)
    except Exception:
        return "checked"  # stale/garbage id — consumed, nothing learned
    item = TKMemoryItemDoc.get(oid).run()  # Bunnet: .run() executes the query
    if item is None or item.zip is None:
        return "checked"  # gone / no zip — consumed, nothing learned

    # SKIP questions — answered, not believed (wondering learns only assertions).
    leaves = evaluation_harness._zip_leaves(item.zip.items)
    if any(getattr(leaf, "dubitative", 0.5) >= 0.999 for leaf in leaves):
        return "checked"

    out = evaluate_zip(item.zip)  # fingerprint-cached KB load
    result: EvaluatorResult = out["result"]
    tok = status_to_token(result)
    logger.info("[wondering] memory-item «%s» -> %s (truth=%.2f)", item.original, tok, result.truth)
    if tok == EvalToken.TRUE.value and materialize_theorem(result, item, derived_by="wondering",
                                                           bs=brain_state):
        return "derived"  # SILENT learning: a NEW theorem entered the KB — fruit
    return "checked"


# process ONE memory item (a bounded work-unit for the coordinator). PER-USER-GROUPED scan (#1):
# rather than one global oldest-first stream, it focuses on the LIVELIEST conversation — the speaker
# who owns the single newest unprocessed message — and drains THAT speaker's window oldest-first
# (advancing only that speaker's cursor) before the focus moves on. So tokeniko reads as present in
# the live chat: a fresh message makes its speaker the focus and an action spawns within a tick or
# two; quiet backlogs are served once the lively conversation is drained (and, eventually, by the
# wondering state). Per-speaker cursors are what let the focus jump between speakers without a single
# global cursor leaping past — and dropping — another conversation's unprocessed backlog.
#
# It evaluates the chosen item, maps the outcome to an eval:* token, and (if a strong conclusion)
# fans it into ideas; then cross-checks the same speaker's priors for a context conflict. Advances +
# persists that speaker's cursor so the item is never reprocessed. Returns True iff it processed one.
#
# ----------------------------------------------------------------------------------------------
# THE OPEN-WHY DERIVATION (senses B2, 2026-07-09) — conversational context is NEVER volatile state:
# it is ALWAYS derivable from the memory timeseries (the author's architecture call). When an inbound
# assertion arrives, ask the biography: did I recently ask this speaker a question they might be
# answering? Two derivations, structural first:
#   1. STRUCTURAL — the inbound reply-threads (Discord reply_to) to a question I sent (B1 records my
#      speech with its sent message_id; B3 forwards the inbound's reply_to).
#   2. RECENCY — my newest message to this speaker inside the window is a question, and the speaker
#      said nothing in between → their next message is the candidate answer (timeseries recency is
#      cheap by construction — the collection type was chosen for this).
# v1 CONSUMES the derivation minimally: an eval:unknown "because" does not re-trigger the why reflex
# (no why-about-the-because regress); the explanation LINK as learning fuel is the D-phase teaching
# channel. A false "because" still speaks up — disagreement outranks etiquette.
# ----------------------------------------------------------------------------------------------
_OPEN_QUESTION_WINDOW = 900  # seconds a question stays "open" for the recency derivation

_self_source_id: Optional[str] = None


def _self_id() -> Optional[str]:
    global _self_source_id
    if _self_source_id is None:
        me = TKMemoryStakeholdersDoc.find_one({"isMe": True}).run()  # Bunnet: .run() executes
        _self_source_id = str(me.id) if me is not None else None
    return _self_source_id


def _meta(item) -> dict:
    try:
        data = json.loads(item.metadata or "{}")
        return data if isinstance(data, dict) else {}
    except (ValueError, TypeError):
        return {}


def _derive_reply_context(item) -> Optional[TKMemoryItemDoc]:
    """The inbound item answers WHICH of my recent questions? Returns my question item, or None."""
    me = _self_id()
    if me is None:
        return None
    window_lo = item.timestamp - timedelta(seconds=_OPEN_QUESTION_WINDOW)
    mine = (
        TKMemoryItemDoc.find({"sourceId": me, "targetId": item.sourceId,
                              "timestamp": {"$gt": window_lo, "$lt": item.timestamp}})
        .sort("-timestamp")
        .to_list()
    )
    if not mine:
        return None
    # 1. structural: the inbound replies to one of my sent messages
    reply_to = _meta(item).get("reply_to")
    if reply_to:
        for m in mine:
            if _meta(m).get("message_id") == reply_to:
                return m if (m.original or "").rstrip().endswith("?") else None
    # 2. recency: my newest message is an open question and the speaker said nothing since
    latest = mine[0]
    if not (latest.original or "").rstrip().endswith("?"):
        return None
    interleaved = TKMemoryItemDoc.find(
        {"sourceId": item.sourceId, "timestamp": {"$gt": latest.timestamp, "$lt": item.timestamp}}
    ).count()
    return latest if interleaved == 0 else None


# ----------------------------------------------------------------------------------------------
# D P2: the verdict's LEDGER ECHO — which trust episode (if any) an assertion's verdict implies.
# Returns (trust_trigger, answer_dict) or (None, None). Self-speech never echoes (no ledger on
# himself — also guarded downstream by record_episode). The mapping:
#   TRUE  + closes my open question -> KICKER (the strong kicker, fork 2: the speaker's «because»
#           grounded against my KB — novel-valid-bridging through conversation)
#   TRUE                            -> AGREEMENT (redundant corroboration — silence-is-consent's echo)
#   FALSE                           -> DISAGREEMENT, scaled by the refuted BELIEF's own trust
#           (min over the refutation's premise docs via _conclusion_trust — contradicting a 0.3
#           tier-hunch ≈ noise, contradicting a 1.0 axiom ≈ full weight)
#   INCONSISTENT                    -> LOGIC_VIOLATION (logic is sacred)
# (SELF_INCONSISTENCY is spawned from the cross-item conflict branch, not here; UNKNOWN is neither.)
# ----------------------------------------------------------------------------------------------
def _trust_echo(token: str, item, result) -> tuple[Optional[str], Optional[dict]]:
    if _self_id() is not None and item.sourceId == _self_id():
        return None, None
    if token == EvalToken.TRUE.value:
        closes = _derive_reply_context(item)
        if closes is not None:
            return (TrustEpisodeKind.KICKER.value,
                    {"note": f"closed my question «{closes.original}» with a KB-true justification"})
        return TrustEpisodeKind.AGREEMENT.value, {"note": "corroborated by my KB"}
    if token == EvalToken.FALSE.value:
        belief_trust = None
        premises = list(getattr(result, "premises", None) or [])
        if premises:
            belief_trust = evaluation_harness._conclusion_trust(premises)
        return (TrustEpisodeKind.DISAGREEMENT.value,
                {"belief_trust": belief_trust, "note": "contradicts what I hold"})
    if token == EvalToken.INCONSISTENT.value:
        return TrustEpisodeKind.LOGIC_VIOLATION.value, {"note": "a logic violation"}
    return None, None


# First-run guard: if wake_at is None, initialize it to the latest memory ts and return False —
# tokeniko only reacts to memory that ARRIVES AFTER it first wakes, never re-thinks all of history.
def think_one(brain_state: TKBrainStateDoc) -> bool:
    wake = brain_state.wake_at
    if wake is None:
        latest = (
            TKMemoryItemDoc.find({})
            .sort("-timestamp")
            .limit(1)
            .to_list()
        )
        if latest:
            brain_state.wake_at = _epoch_utc(latest[0].timestamp)
        else:
            brain_state.wake_at = datetime.now(timezone.utc).timestamp()
        brain_state.save()
        return False

    wake_dt = datetime.fromtimestamp(wake, timezone.utc)
    # every memory item past the wake boundary, with a zip, NEWEST-first (so the first eligible item
    # we hit is the single newest unprocessed message across all speakers → its speaker is the focus).
    candidates = (
        TKMemoryItemDoc.find({"timestamp": {"$gt": wake_dt}})
        .sort("-timestamp")
        .to_list()
    )
    cursors = dict(brain_state.source_cursors or {})
    # eligible = unprocessed per its OWN speaker's cursor (default floor = the wake boundary).
    eligible = [
        c
        for c in candidates
        # a zip to evaluate OR a social act to react to (slice 4: pure social items carry no zip)
        if (c.zip is not None or getattr(c, "social", None))
        and _epoch_utc(c.timestamp) > cursors.get(c.sourceId, wake)
    ]
    if not eligible:
        return False

    # FOCUS = the speaker who owns the newest eligible message (candidates are newest-first, so it is
    # eligible[0]'s speaker). Within that speaker, process the OLDEST eligible item — draining their
    # window chronologically (priors before posteriors, which the cross-item check below relies on).
    focus_source = eligible[0].sourceId
    item = min(
        (c for c in eligible if c.sourceId == focus_source),
        key=lambda c: c.timestamp,
    )

    # the SHORT-TERM CONTEXT ring (compose 2.0 slice 5): every processed item is channel talk —
    # feed it (a derivable RAM cache; the anecdote's topic centroid + hunch 20's social column).
    try:
        context.context_add(item)
    except Exception as error:
        logger.warning("[thinking] context ring feed failed (%s) — continuing", error)

    # LEARNED SCAFFOLDS (§1, stage one): pick up a decently-trusted talker's phrasing mid-
    # conversation as a person-scoped MIMIC row (social acts + slot-less whole-zip matches). Runs
    # for BOTH social and zipped items; an error logs + continues (never blocks thinking).
    try:
        mimicry.mimic_observe(item)
    except Exception as error:
        logger.warning("[thinking] mimicry observe failed (%s) — continuing", error)

    # --------------------------------------------------------------
    # SOCIAL ACT (survey slice 4, hunch 8): recognized at the ears, NEVER evaluated — no truth
    # verdict, no trust echo, no teachability, no why-ask (the «hello John» junk path is cured
    # here even when no reflex fires). React (or stay politely quiet), advance the cursor, done.
    # --------------------------------------------------------------
    if getattr(item, "social", None):
        _social_react(item)
        cursors[focus_source] = _epoch_utc(item.timestamp)
        brain_state.source_cursors = cursors
        brain_state.save()
        return True

    # --------------------------------------------------------------
    # QUESTION vs ASSERTION (#4 D, questions P3): a question is ANSWERED, not believed. answer_zip
    # returns None for a declarative (a cheap mood check BEFORE any KB load), so the assertion path
    # below is unchanged. For a question it computes the AnswerResult (polar yes/no/idk reusing the
    # truth machinery; wh value-solving) and fans an eval:question idea carrying the answer + the
    # asker (item.sourceId) as the reply target. A question is NOT a belief, so it does NOT run the
    # assertion eval (no speakup/etc.) and is NOT cross-item-conflict-checked.
    # --------------------------------------------------------------
    qout = evaluation_harness.answer_zip(item.zip)
    if qout is not None:
        answer = qout["answer"]
        ideas = behavior.spawn_ideas_for(
            EvalToken.QUESTION.value,
            payload=item.zip,
            source=str(item.id),
            answer=answer.model_dump(),
            target=item.sourceId,
        )
        logger.info(
            "[thinking] question memory=%s -> answer %s/%s conf=%.2f (%d idea(s))",
            str(item.id), answer.kind.value, answer.verdict.value, answer.confidence, len(ideas),
        )
    else:
        out = evaluate_zip(item.zip)
        result: EvaluatorResult = out["result"]
        token = status_to_token(result)

        # BELIEF-REVISION v1 (retreat arc #4): a FALSE may be a valid quantified CORRECTION of a
        # learned generalization — the correction path replaces refute-back (no eval:false, no
        # DISAGREEMENT ding) AND the cross-item conflict check below (self-correction is deliberate
        # revision, not the honest-liar's contradiction). See _try_correction.
        corrected = token == EvalToken.FALSE.value and _try_correction(item)
        # the reduct-answer binding (§0 slice 2, fork A): the asked teacher's generic denial of
        # an asked premise binds regardless of corner AND of verdict (inside the conflict zone
        # the mirror abstains, so the denial may grade UNKNOWN — the context still binds it).
        if not corrected:
            corrected = _try_reduct_answer(item)

        if corrected:
            pass  # the correction path spawned its own ideas (retreat + trust echo)
        elif token:
            # B2 (the open-why): an UNKNOWN that answers my own recent question is a candidate
            # explanation — do not re-interrogate it (the why-regress). Other verdicts unaffected
            # (a false "because" still speaks up; a true one still corroborates/learns).
            because_of = (
                _derive_reply_context(item) if token == EvalToken.UNKNOWN.value else None
            )
            if because_of is not None:
                logger.info(
                    "[thinking] «%s» answers my question «%s» (memory=%s) — candidate explanation; "
                    "why-regress suppressed (open-why v1)",
                    item.original, because_of.original, str(because_of.id),
                )
            else:
                # B1 (slice 4): a FALSE verdict carries the refuting belief so the speakup can
                # NAME it («…— I hold that a calculator never thinks»); resolves to None ->
                # the plain speakup speaks, unchanged.
                belief = (_refuting_belief(result.premises)
                          if token == EvalToken.FALSE.value else None)
                # the topic-slotted why (survey 2026-07-19): an UNKNOWN carries the ungroundable
                # claim (vocative stripped — address is not content) so the why can name what it
                # is asking about; the compose slot gate keeps the bare shelf as the fallback.
                topic = (strip_vocative(item.original, get_tokeniko().name).strip()
                         if token == EvalToken.UNKNOWN.value and item.original else None)
                answer = ({"belief": belief} if belief
                          else {"topic": topic} if topic else None)
                ideas = behavior.spawn_ideas_for(token, payload=item.zip, source=str(item.id),
                                                 confidence=verdict_confidence(token, result),
                                                 answer=answer)
                logger.info(
                    "[thinking] evaluated memory=%s status=%s truth=%.3f -> %s (%d idea(s))",
                    str(item.id),
                    result.status.value,
                    result.truth,
                    token,
                    len(ideas),
                )
            # D1b: a forward-chained eval:true is genuine derived knowledge -> learn it (silently).
            if token == EvalToken.TRUE.value:
                materialize_theorem(result, item, derived_by="thinking", bs=brain_state)
            # D P3 (tier-1, the TEACHING CHANNEL) — the B-WIRE (survey slice 3, author's ruling):
            # a teachable novel assertion spawns eval:novel; the eval:novel -> tokeniko:learn RULE
            # is the personality switch of teachability, and the MINT runs in the learn executor
            # (brain/main._execute_learn). No rule = a mind that doesn't accept teaching. Runs on
            # BOTH unknown paths (a trusted teacher's «because» is itself teachable).
            if token == EvalToken.UNKNOWN.value and _taught_candidate(item) is not None:
                behavior.spawn_ideas_for(EvalToken.NOVEL.value, payload=item.zip,
                                         source=str(item.id), target=item.sourceId)
            # THE OBSERVATION-FACT SEAM: a refuted assertion is itself knowledge — the speaker
            # said false (silent, like all learning; the DISAGREEMENT echo below prices the
            # trust side; an accepted CORRECTION never reaches here — no offense in revision).
            if token == EvalToken.FALSE.value:
                record_observation(item, result)

            # D P2: the verdict's LEDGER ECHO — spawn the trust:* trigger beside the eval reflex
            # (its own namespace: no collapse-collision, so he can push back AND distrust). The
            # trigger/urge mapping is KB personality (behavior_rules); the episode kind rides in
            # the trigger, the scale/note in `answer`, the speaker in `target`. The STRONG KICKER
            # (author's fork 2) = the closed why-loop: a TRUE that answers one of my own open
            # questions means the speaker's justification GROUNDED against my KB — novel-valid-
            # bridging, literally through conversation. Epistemics stay pure: this is bookkeeping
            # ABOUT the verdict, computed after it.
            trust_trigger, trust_answer = _trust_echo(token, item, result)
            if trust_trigger is not None:
                behavior.spawn_ideas_for(
                    trust_trigger, payload=item.zip, source=str(item.id),
                    answer=trust_answer, target=item.sourceId,
                )
        else:
            logger.info(
                "[thinking] evaluated memory=%s status=%s truth=%.3f -> no strong conclusion",
                str(item.id),
                result.status.value,
                result.truth,
            )

        # THE ANECDOTE (slice 5, case 3): only on the QUIET verdicts — a TRUE (silence-is-consent)
        # or no strong conclusion. Every other verdict already speaks (speakup/why/clarify) or
        # revises; a question is answered above. The gates (ambient band, floor, cooldown,
        # novelty) live in _try_anecdote/context.
        if not corrected and token in (None, EvalToken.TRUE.value):
            _try_anecdote(item)

        # ----------------------------------------------------------
        # CROSS-ITEM CONSISTENCY (#4 D): cross-check this ASSERTION against the SAME speaker's recent
        # priors for a contradiction. A cross-item contradiction is a REVISABLE CONTEXT conflict
        # ("you said the cat is alive, now you say it's dead — which holds?") — NOT the hardwired
        # logic INCONSISTENT (X∧¬X within ONE statement). On a conflict, emit eval:conflict (the
        # seeded personality maps it to tokeniko:clarify). classifyForm over a synthetic union.
        #
        # DEFERRED: (1) cross-SPEAKER patterns — SAME-SPEAKER only; (2) inference-implied conflicts
        # ("eating" vs "dead") needing forward-chaining — DIRECT contraries (X∧¬X / antonym) only.
        # SKIPPED for an accepted correction (retreat arc #4): a self-correction is deliberate
        # revision — never the honest-liar signal.
        n_clauses = evaluation_harness._zip_leaves(item.zip.items) if not corrected else []
        priors = (
            TKMemoryItemDoc.find(
                {"sourceId": item.sourceId, "timestamp": {"$lt": item.timestamp}}
            )
            .sort("-timestamp")
            .limit(25)
            .to_list()
        ) if not corrected else []
        for m in priors:
            if m.zip is None:
                continue
            detail = evaluation_harness.cross_item_conflict(
                n_clauses, evaluation_harness._zip_leaves(m.zip.items)
            )
            if detail:
                behavior.spawn_ideas_for(
                    EvalToken.CONFLICT.value, payload=item.zip, source=str(item.id)
                )
                # D P2: the honest-liar proxy — contradicting YOURSELF is the strongest ledger
                # signal (unreliability matters regardless of intent). Echoed beside the clarify
                # reflex (own namespace, no collapse-collision).
                behavior.spawn_ideas_for(
                    TrustEpisodeKind.SELF_INCONSISTENCY.value, payload=item.zip,
                    source=str(item.id),
                    answer={"note": f"self-contradiction across own claims ({detail})"},
                    target=item.sourceId,
                )
                logger.info(
                    "[thinking] cross-item conflict: memory=%s vs %s -> eval:conflict (%s)",
                    str(item.id),
                    str(m.id),
                    detail,
                )
                break  # one conflict idea per N (idempotent dedups re-ticks anyway)

    # advance ONLY the focus speaker's cursor past this item (sub-second, so the just-processed item
    # is strictly excluded next tick — the obsessive-loop guard). Other speakers' cursors are untouched,
    # so their backlogs survive the focus jump. Reassign the dict so the doc-save persists the mutation.
    cursors[focus_source] = _epoch_utc(item.timestamp)
    brain_state.source_cursors = cursors
    brain_state.save()
    return True
