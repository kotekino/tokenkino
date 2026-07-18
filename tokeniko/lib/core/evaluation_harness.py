# --------------------------------------------------------------
# lib/core/evaluation_harness.py — the PARSER-FREE evaluate-a-zip harness.
#
# Shared by the api (EvaluationService) and the brain (brain/thinking.py). It loads the ACTIVE
# knowledge (definitions + axioms + theorems), builds the injected graph readers + the
# forward-chainer rules/facts, runs the DB-agnostic evaluator over a ready TKZip statement, and maps
# the best relational match back to a concrete document id.
#
# It imports ONLY lib.core.* + lib.llc.evaluator — NEVER lib.llc.parser / lib.llc.compiler. That is
# the whole point: the `brain` process stays parser-free (it only calls init_io, never loads
# spaCy/Stanza), so it cannot import EvaluationService (which imports the parser at module top). The
# evaluator package is parser-free, so the brain reuses this harness directly. The single parser step
# (sentence -> TKZip) stays in EvaluationService._compile_zip and is the only api-only piece.
# --------------------------------------------------------------
import logging
import os
import time
from typing import Optional

from lib.core.constants import _ME_UID
from lib.core.models import TKAxiomDoc, TKDefinitionDoc, TKDictionaryDoc, TKRelationDoc, TKDerivedRelationDoc, TKDerivedRuleDoc, TKTheoremDoc
from lib.core.tk import TKOperator, TKQuantifier
from lib.core.tkzip import TKZip, TKZipContent, TKZipItem
from lib.core.evaluation import AnswerKind, AnswerResult, AnswerVerdict, EvaluatorResult, EvaluatorStatus
# the UNIVERSAL EXTRACTOR (step 4): all "stored zip -> chainable logic" mining lives in kb_extract;
# _zip_leaves/_zip_leaf_items are re-exported here for the many probe/brain callers that import them
# from this module (the historical home).
from lib.core.kb_extract import _zip_leaves, _zip_leaf_items, extract_logic
from lib.core.places import place_contains, place_parent, place_type_of
from lib.llc.evaluator import evaluator_classifyForm, evaluator_evaluateStatement, evaluator_solveWh, evaluator_forwardChain

# verbose wondering trace — shares the brain's "tokeniko-brain" logger/handler so it prints to the
# console when the brain runs. Gated by WONDER_VERBOSE (default ON while we debug the enriched soak;
# set WONDER_VERBOSE=0 to silence). The API never calls kb_wonder, so this stays brain-only in practice.
logger = logging.getLogger("tokeniko-brain")
_WONDER_VERBOSE = os.getenv("WONDER_VERBOSE", "1").strip().lower() not in ("0", "false", "no", "")


def _short(sense: Optional[str]) -> str:
    return (sense or "?").split(".", 1)[0]


# the injected is_a graph reader: parents(sense) -> direct is_a hypernyms over the BEDROCK ~150k-triple
# `relations` collection (never loaded wholesale — only the per-sense edges actually touched). cached
# per evaluate_zip() call (rebuilt below) so repeated lookups during one BFS hit memory. This is the
# TRUSTED graph: the definitions-as-rules extractor + its dry-run probe GATE candidate edges against it
# (never against the union below — else already-inserted edges would look "redundant"), and the
# ingestion untangle disambiguates against it too.
def _make_relations_reader():
    cache: dict[str, list[str]] = {}

    def parents(sense: str) -> list[str]:
        hit = cache.get(sense)
        if hit is not None:
            return hit
        edges = TKRelationDoc.find({"subject": sense, "relation": "is_a"}).to_list()
        objs = [e.object for e in edges]
        cache[sense] = objs
        return objs

    return parents


# the EVALUATOR's is_a reader: bedrock UNION the LOW-TRUST `derived_relations` tier (definition-mined
# is_a edges, definitions-as-rules step 3) UNION the IN-MEMORY axiom-derived edges (`extra`,
# generic-taxonomy step 2 — mined per KB load, never persisted), so definitions AND generic axioms
# fuel grounding + chaining — without ever polluting bedrock (the tier is a physically separate,
# revocable collection; the axiom edges retract with their source axiom). Only `_load_active_kb`
# wires this into the evaluator/chainer; the gate + untangle deliberately keep the bedrock-only reader.
def _make_relations_reader_union(extra: Optional[dict] = None):
    cache: dict[str, list[str]] = {}

    def parents(sense: str) -> list[str]:
        hit = cache.get(sense)
        if hit is not None:
            return hit
        edges = TKRelationDoc.find({"subject": sense, "relation": "is_a"}).to_list()
        objs = [e.object for e in edges]
        for e in TKDerivedRelationDoc.find({"subject": sense, "relation": "is_a"}).to_list():
            if e.object not in objs:
                objs.append(e.object)
        for o in (extra or {}).get(sense, []):
            if o not in objs:
                objs.append(o)
        cache[sense] = objs
        return objs

    return parents


# the TIER-EDGE PROVENANCE reader: edge_source(subject, object) -> a stable premise KEY
# ("subject|is_a|object") when "subject is_a object" is a LOW-TRUST tier edge (definition-derived),
# else None. Lets the chainer record a tier edge it walks as a revocable premise (bedrock edges ->
# None -> stay substrate). The key is DETERMINISTIC (not the Mongo ObjectId) so it survives the
# extractor's delete-then-insert rebuilds, and self-documenting (a proof premise reads
# "air.n.01|is_a|mixture.n.01"). cached per call.
def _edge_key(subject: str, object: str) -> str:
    return f"{subject}|is_a|{object}"


def _make_edge_source_reader(extra: Optional[dict] = None):
    cache: dict[tuple, Optional[str]] = {}

    def edge_source(subject: str, object: str) -> Optional[str]:
        key = (subject, object)
        if key in cache:
            return cache[key]
        if object in (extra or {}).get(subject, []):
            cache[key] = _edge_key(subject, object)  # in-memory axiom-derived edge (step 2)
            return cache[key]
        e = TKDerivedRelationDoc.find_one(
            {"subject": subject, "object": object, "relation": "is_a"}).run()
        cache[key] = _edge_key(subject, object) if e else None
        return cache[key]

    return edge_source


# a derived theorem is only as trustworthy as its WEAKEST premise (min-trust inheritance — truth and
# trust are orthogonal: a chain through a derived item is validly derived, truth 1.0, but only as
# trustworthy as that item). axiom/rule/fact premises are Mongo ids (bedrock-trusted, the 0.9
# default); a DERIVED premise is a stable "|"-bearing key — a tier EDGE ("subj|is_a|obj") or a
# differentia RULE ("rule:subj|pred|obj") — resolved PER-PREMISE against the `edge_trust` map that
# `_load_active_kb` builds (definition-derived 0.3, axiom-derived generic edge 0.9, source-trusted).
# min over all premises: a chain through one 0.3 item is a 0.3 theorem, never laundered up; a chain
# purely over axiom-derived edges stays honestly 0.9. `edge_trust=None` falls back to the in-process
# KB cache (so the brain's materialize path is per-premise-accurate without threading the kb through),
# then to the conservative tier default for unknown "|" keys.
_DERIVED_DEFAULT_TRUST = 0.9
_DERIVED_TIER_TRUST = 0.3
_AXIOM_EDGE_TRUST = 0.9   # a generic-taxonomy edge mined from a curated AXIOM (step 2) — high trust
# a GENERIC rule is NOT a universal (Brain v1.1 2d): "humans create their gods" is a kind-level
# observation that tolerates exceptions ("birds fly" vs penguins), so a conclusion derived through it
# is DEFEASIBLE — stored below the 0.9 universal bar, revisable. (Generic TAXONOMY copulars — "a cat
# is a mammal" — stay high-trust: a generic taxonomic claim is definitional, not behavioral.)
_GENERIC_RULE_TRUST = 0.7


def _conclusion_trust(premise_ids, edge_trust: Optional[dict] = None) -> float:
    if edge_trust is None:
        edge_trust = (_kb_cache or {}).get("edge_trust") or {}
    trust = _DERIVED_DEFAULT_TRUST
    for pid in (premise_ids or []):
        if pid in edge_trust:
            trust = min(trust, edge_trust[pid])       # tier edge / derived rule / generic rule / theorem
        elif "|" in (pid or ""):
            trust = min(trust, _DERIVED_TIER_TRUST)   # unknown derived key — conservative
    return trust


# ------------------------------------------------------------------------------------------------
# TRANSITIVE CASCADE REVOCATION (Brain v1.1 step 3). Archive every ACTIVE theorem whose proof rests
# — directly or through OTHER theorems — on any of the given premise keys (axiom/theorem Mongo ids,
# tier-edge "subj|is_a|obj" keys, derived-rule "rule:…" keys). Recursion is what makes theorems-
# breeding-theorems safe: with theorems feeding the chainer, a grandchild's premises cite its PARENT
# theorem's id, not the original axiom — so retracting the axiom must walk the whole descent.
# Breadth-first over premise-key frontiers; a `seen` set makes cycles harmless. dry_run=True (default)
# only REPORTS the descent; dry_run=False archives (archived theorems are kept as history, out of
# active reasoning — never deleted). Returns the dependent theorems in discovery order.
# ------------------------------------------------------------------------------------------------
def revoke_dependents(premise_ids, dry_run: bool = True) -> list:
    out: list = []
    frontier = {str(p) for p in (premise_ids or []) if p}
    seen: set = set(frontier)
    now = int(time.time())
    while frontier:
        dependents = TKTheoremDoc.find(
            {"archived": False, "provenance.premises": {"$in": sorted(frontier)}}).to_list()
        frontier = set()
        for t in dependents:
            tid = str(t.id)
            if tid in seen:
                continue
            seen.add(tid)
            if not dry_run:
                t.archived = True
                t.archivedAt = now
                t.save()
                logger.info("[revoke] archived dependent theorem «%s» (cascade)", t.original)
            out.append(t)
            frontier.add(tid)  # its own dependents fall next round
    return out


# ------------------------------------------------------------------------------------------------
# BELIEF-REVISION v1 — the correction detector (retreat arc #4, Popper trust-gated). Is this zip a
# QUANTIFIED CORRECTION of a LEARNED generalization? A correction is an O-corner claim
# («not all S are P»: UNIVERSAL + negated) or an E-corner claim («no S is P»: NEGATIVE quantifier)
# whose is_a pair the ACTIVE union graph currently AFFIRMS through at least one LEARNED hop —
# i.e. exactly the claim the old evaluator would refute-back ("the bounce"). One counterexample
# defeats a universal (Popper's asymmetry); the TRUST GATE (corrector >= belief) is the caller's
# (brain policy, not harness mechanics).
#
# v1 scope: only hops asserted by ACTIVE AXIOM/THEOREM docs are retractable (archiving the doc IS
# the retreat — revocation durability by construction). Definition-tier hops (WordNet-gloss-mined)
# are never retracted on conversational say-so; a path learned ONLY through them yields None (the
# normal eval:false path stands). Pure-bedrock paths are substrate, not belief — None.
#
# The RETREAT DESTINATION (the square's subalternation): an O correction defeats A but leaves the
# subaltern I standing («some S are P» — consistent with «not all»), so `weakened` carries the
# I-mint (tokens + pinned senses). An E correction contests I too — nothing survives to mint.
# ------------------------------------------------------------------------------------------------
def correction_target(zip_obj: TKZip) -> Optional[dict]:
    from lib.llc.evaluator.e_statement import _isa_senses
    from lib.llc.evaluator.e_relations import relations_subsumes
    from lib.core.kb_extract import _leaf_is_crisp

    kb = _load_active_kb()
    for leaf in _zip_leaves(zip_obj.items):
        if not _leaf_is_crisp(leaf):
            continue  # a ◇-claim asserts nothing — it corrects nothing (Pillar 3)
        quantifier = getattr(leaf, "quantifier", TKQuantifier.GENERIC)
        negated = bool(getattr(leaf, "negated", False))
        # the O corner arrives two ways: the legacy UNIVERSAL+negated reading (old stored zips /
        # ∀¬ surface shapes) and the first-class NEGATED_UNIVERSAL (M6: «not all S are P» with the
        # negation on the quantifier slot, negated=False)
        is_o = (quantifier == TKQuantifier.UNIVERSAL and negated) or \
               (quantifier == TKQuantifier.NEGATED_UNIVERSAL and not negated)
        is_e = quantifier == TKQuantifier.NEGATIVE and not negated
        if not (is_o or is_e):
            continue
        pair = _isa_senses(leaf)
        if pair is None:
            continue
        subject_sense, object_sense = pair

        # the affirmed generalization, in either KB representation: the DIRECT key catches a
        # membership-RULE assertion («all softwares are minds» — no graph edge exists for it);
        # the subsumes walk catches (possibly multi-hop) EDGE-minted taxonomy.
        direct_key = _edge_key(subject_sense, object_sense)
        learned_keys: list[str] = []
        path = [subject_sense, object_sense]
        if kb["edge_doc_sources"].get(direct_key):
            learned_keys = [direct_key]
        else:
            walked = relations_subsumes(object_sense, subject_sense, kb["relations"])
            if walked is None or len(walked) < 2:
                continue  # the KB does not affirm the generalization — nothing to correct
            path = walked
            hops = list(zip(path, path[1:]))
            learned_keys = [
                _edge_key(s, o) for s, o in hops if kb["edge_source"](s, o) is not None
            ]
            if not learned_keys:
                continue  # pure bedrock — substrate, not a retractable belief
        sources = [
            src for k in learned_keys for src in kb["edge_doc_sources"].get(k, [])
        ]
        retractable = [
            s for s in sources
            if s["kind"] == "theorem"
            or (s["kind"] == "axiom" and not s.get("readonly", True))
        ]
        if not retractable:
            # v1: vocabulary (definition-tier) and READONLY axioms (the seeded imprinting — the
            # author's API privilege) are never retracted conversationally -> the normal
            # eval:false path stands (he defends his constitution, honestly).
            continue
        belief_trust = min(
            min((kb["edge_trust"].get(k) for k in learned_keys if k in kb["edge_trust"]),
                default=_DERIVED_DEFAULT_TRUST),
            min((kb["edge_trust"].get(s["id"]) for s in retractable if s["id"] in kb["edge_trust"]),
                default=_DERIVED_DEFAULT_TRUST),
        )
        corner = "O" if is_o else "E"
        weakened = None
        if is_o:  # retreat down the square: A -> its subaltern I (pinned senses; dedup at materialize)
            weakened = {
                "tokens": f"some {_short(subject_sense)} is a {_short(object_sense)}",
                "senses": {"subject": subject_sense, "predicate": object_sense},
            }
        return {
            "corner": corner,
            "subject": subject_sense,
            "object": object_sense,
            "path": path,
            "edge_keys": learned_keys,
            "sources": retractable,
            "belief_trust": belief_trust,
            "weakened": weakened,
        }
    return None


# the injected part_of (meronymy) graph reader: wholes(sense) -> direct part_of wholes (the
# senses Y such that `sense` is part_of Y). kept SEPARATE from the is_a reader — is_a and part_of
# are different relations with different truth semantics. cached per evaluate_zip() call, same shape.
def _make_partof_reader():
    cache: dict[str, list[str]] = {}

    def wholes(sense: str) -> list[str]:
        hit = cache.get(sense)
        if hit is not None:
            return hit
        edges = TKRelationDoc.find({"subject": sense, "relation": "part_of"}).to_list()
        objs = [e.object for e in edges]
        cache[sense] = objs
        return objs

    return wholes


# the injected "sibling senses" reader: given a synset sense ("tiger.n.01") -> every dictionary sense
# of the SAME lemma+POS ("tiger.n.01", "tiger.n.02"). lets the is_a grounder try a charitable
# cross-product when the WSD-chosen sense is wrong but another sense of the same word subsumes.
def _make_senses_reader():
    def senses_of(sense: str) -> list[str]:
        parts = (sense or "").rsplit(".", 2)
        if len(parts) != 3:
            return [sense] if sense else []
        word, pos = parts[0], parts[1]
        docs = TKDictionaryDoc.find({"word": word, "pos": pos}).to_list()
        out = [d.sense for d in docs if d.sense]
        return out or ([sense] if sense else [])
    return senses_of


# the injected antonym reader: antonyms(sense) -> the senses directly antonym-linked to `sense`.
# feeds the intra-statement contrary-predicate check (same-subject + antonym predicate senses).
# cached per evaluate_zip() call, same shape as the is_a / part_of readers.
def _make_antonym_reader():
    cache: dict[str, list[str]] = {}

    def antonyms(sense: str) -> list[str]:
        hit = cache.get(sense)
        if hit is not None:
            return hit
        edges = TKRelationDoc.find({"subject": sense, "relation": "antonym"}).to_list()
        objs = [e.object for e in edges]
        cache[sense] = objs
        return objs

    return antonyms


# the flat set of every WSD sense referenced anywhere in a zip (across all leaf clauses' role->sense
# maps), sorted+unique. used to stamp TKMemoryItemDoc.senses at write time so associative wondering can
# find the memories a KB change is relevant to via an indexable {"senses": {"$in": [...]}} query.
def zip_senses(statement) -> list[str]:
    out: set[str] = set()
    for leaf in _zip_leaves(statement.items):
        senses = getattr(leaf, "senses", None) or {}
        for s in senses.values():
            if s:
                out.add(s)
    return sorted(out)


# the surface lemma of a synset key ("exist.v.01" -> "exist", "give_up.v.01" -> "give up"). "" if empty.
def _sense_surface(sense: Optional[str]) -> str:
    if not sense:
        return ""
    return sense.split(".", 1)[0].replace("_", " ")


# conjugate a base verb to its 3rd-person-singular form ("exist" -> "exists", "carry" -> "carries",
# "go" -> "goes", "kiss" -> "kisses"). irregulars handled explicitly. used to render a conclusion
# about a third-person-singular subject (a named individual or a generic class).
_IRREGULAR_3SG = {"have": "has", "be": "is", "do": "does"}
_VOWELS = "aeiou"


def _verb_3sg(base: str) -> str:
    if base in _IRREGULAR_3SG:
        return _IRREGULAR_3SG[base]
    if not base:
        return base
    if base.endswith(("s", "x", "z", "ch", "sh")):
        return base + "es"
    if base.endswith("y") and len(base) >= 2 and base[-2] not in _VOWELS:
        return base[:-1] + "ies"
    if base.endswith("o"):
        return base + "es"
    return base + "s"


# pick a SINGULAR, natural dictionary word for a class sense, for the "a <word>" generic subject.
# query the dictionary for every word mapped to this sense, drop the plurals (an "-s" word that has a
# non-"-s" sibling), then PREFER the longest remaining singular (favours "human" over "homo"). cheap
# single DB query; parser-free. falls back to the synset lemma surface if nothing is found.
# IN-PROCESS CACHED: the sense->word mapping is stable for a process lifetime, and kb-wondering
# re-renders every derivable conclusion each pass to test it against `held` — uncached, a converged
# KB still paid one dictionary query per conclusion per tick (the 2026-07-16 wondering freeze).
_class_word_cache: dict[str, str] = {}


def _class_word(sense: str) -> str:
    if not sense:
        return ""
    cached = _class_word_cache.get(sense)
    if cached is None:
        cached = _class_word_uncached(sense)
        _class_word_cache[sense] = cached
    return cached


def _class_word_uncached(sense: str) -> str:
    docs = TKDictionaryDoc.find({"sense": sense}).to_list()
    words = [d.word for d in docs if getattr(d, "word", None)]
    if not words:
        return _sense_surface(sense)
    word_set = set(words)
    # PREFER the sense's OWN lemma (the canonical, round-trip-stable name for THIS exact synset) — so
    # chat.n.01 renders "chat", not the longest synonym "confabulation" (which reads as a different
    # sense and misleads). This is round-trip-correct (the lemma re-parses back to this sense) and
    # honest even when the subject WSD is itself wrong (a bad "chat.n.01" edge reads plausibly as "chat"
    # rather than screaming "confabulation"). Only when the lemma isn't a stored word do we fall back to
    # the longest-singular heuristic.
    lemma = _sense_surface(sense)
    if lemma in word_set:
        return lemma
    # drop a plural "-s" form when its singular sibling is also a candidate
    singulars = [w for w in words if not (w.endswith("s") and w[:-1] in word_set)]
    candidates = singulars or words
    return max(candidates, key=len)


# render a DERIVED conclusion about ANY subject into round-trippable natural language, so it can be
# compiled back through the real pipeline into a first-class zip theorem that re-yields the SAME
# (subject, predicate, object, negated). subject is one of: tokeniko's uid (-> first-person "I"), an
# individual uid like "mari@internal:tokeniko" (-> the capitalized name, 3rd-sing), or a class sense
# like "homo.n.02" (-> a generic "a <word>", 3rd-sing). the predicate POS is read off the sense key
# (".v." verb, ".a."/".s." adjective, ".n." noun) and drives the verbalization + agreement:
#   verb     -> conjugated ("I exist", "Mari exists"); negated -> "do/does not <base>".
#   adjective-> copula + adjective ("I am finite", "Mari is mortal"); negated -> "is not <adj>".
#   noun     -> copula + article + noun ("Mari is a human"); negated -> "is not a <noun>".
# returns "" if no predicate.
def render_conclusion(subject: str, predicate: str, object: Optional[str] = None,
                      negated: bool = False, subject_kind: Optional[str] = None) -> str:
    word = _sense_surface(predicate)
    if not word:
        return ""

    # ---- subject phrase + grammatical agreement (person/number) ----
    if subject == _ME_UID:
        subject_text, first_person = "I", True
    elif subject_kind == "individual":
        name = (subject or "").split("@", 1)[0]
        subject_text = (name[:1].upper() + name[1:]) if name else subject
        first_person = False
    elif subject_kind == "class":
        subject_text = "a " + _class_word(subject)
        first_person = False
    else:
        # fallback: looks like a noun sense -> treat as a generic class, else surface it
        if subject and ".n." in subject:
            subject_text = "a " + _class_word(subject)
        else:
            subject_text = _sense_surface(subject) or subject
        first_person = False

    base_copula = "am" if first_person else "is"
    obj = _sense_surface(object)

    # ---- predicate verbalization, POS-driven ----
    if ".v." in (predicate or ""):
        if first_person:
            verb = f"do not {word}" if negated else word
        else:
            verb = f"does not {word}" if negated else _verb_3sg(word)
        head = f"{subject_text} {verb}"
        return f"{head} {obj}" if obj else head

    if ".a." in (predicate or "") or ".s." in (predicate or ""):
        adj = f"not {word}" if negated else word
        head = f"{subject_text} {base_copula} {adj}"
        return f"{head} {obj}" if obj else head

    if ".n." in (predicate or ""):
        article = "an" if word[:1].lower() in _VOWELS else "a"
        comp = f"not {article} {word}" if negated else f"{article} {word}"
        head = f"{subject_text} {base_copula} {comp}"
        return f"{head} {obj}" if obj else head

    # unknown POS: best-effort surface
    return f"{subject_text} {word}"


# the SEMANTIC conclusion key of a compiled zip — its meaning, independent of surface wording. each leaf
# contributes (subject_ref, predicate_sense, object_sense, negated) where subject_ref prefers the
# IDENTITY uid (a named individual) over the sense. two zips with the same key assert the SAME thing
# ("I exist" and "tokeniko exists" share it) -> the dedup signature for materialized theorems. sorted
# tuple of per-leaf keys so it is order-independent and works for single- or multi-clause conclusions.
def conclusion_key(statement) -> tuple:
    leaves = []
    for leaf in _zip_leaves(statement.items):
        senses = getattr(leaf, "senses", None) or {}
        identities = getattr(leaf, "identities", None) or {}
        subject = identities.get("subject") or senses.get("subject")
        # the ¬∀ discriminator joins the key (M6): with NEGATED_UNIVERSAL first-class, «not all S
        # are P» carries negated=False — without this slot it would collide with «all S are P».
        # Deliberately a BOOL, not the full quantifier value: widening the key by quantifier would
        # break dedup continuity with every stored theorem (generic-vs-indefinite re-derivation
        # churn); only the O corner needs the distinction.
        leaves.append((subject, senses.get("predicate"), senses.get("direct"),
                       bool(getattr(leaf, "negated", False)),
                       getattr(leaf, "quantifier", None) == TKQuantifier.NEGATED_UNIVERSAL))
    # sort key: stringify every slot — `x or ""` left the negated bool as True (bool<str TypeError
    # when two leaves tie on senses and differ only in negation, e.g. «clouds can produce rain but
    # not every cloud produces rain»). The KEY tuples are unchanged; only the ordering is normalized.
    # SET-collapse (zip-native P1): identical leaves assert the SAME thing — a duplicated leaf is
    # the round-trip's stutter (the parser split «a cat feels curiosity» wrongly and the sense-pin
    # stamped the true conclusion onto BOTH halves), not a second assertion. Collapsing makes the
    # stored stutter equal its honest native single-leaf form — dedup continuity without migration.
    return tuple(sorted(set(leaves), key=lambda t: tuple("" if x is None else str(x) for x in t)))


# classifyForm over a synthetic conjunction of clauses (TKZipContent). Returns classifyForm's detail
# string on a contradiction, else None. The shared kernel for both the union check and the
# self-contradiction guards below.
def _clauses_contradict(clauses: list) -> Optional[str]:
    if len(clauses) < 1:
        return None
    synthetic = TKZip(
        map=[0.0] * 8,
        items=TKZipItem(
            op=TKOperator.AND,
            content=[TKZipItem(content=c) for c in clauses],
        ),
    )
    form = evaluator_classifyForm(synthetic, antonyms=_make_antonym_reader())
    return form.detail if form.contradiction else None


# the CROSS-ITEM consistency engine (parser-free). Compare two memory items' clause-sets (e.g. the
# same speaker's prior vs new claim) and detect a contradiction that EMERGES from combining them. A
# genuine cross-item conflict means the UNION is contradictory YET NEITHER item is self-contradictory
# alone. We exclude the self-contradictory halves so that an internally-INCONSISTENT prior or new item
# (e.g. "the cat is dead and alive") does NOT poison every pairwise check by making every union
# trivially contradictory — that case is an intra-statement INCONSISTENT (X∧¬X within ONE statement),
# handled elsewhere, NOT a revisable context conflict. The cross-item contradiction we keep IS a
# revisable CONTEXT conflict. The caller keeps each set small (pairwise) to stay under classifyForm's
# atom cap (_MAX_ATOMS=16).
def cross_item_conflict(clauses_a: list, clauses_b: list) -> Optional[str]:
    if len(clauses_a) < 1 or len(clauses_b) < 1:
        return None
    union = _clauses_contradict(clauses_a + clauses_b)
    if union is None:
        return None
    if _clauses_contradict(clauses_a) is not None:
        return None  # intra, not cross
    if _clauses_contradict(clauses_b) is not None:
        return None  # poisoned prior
    return union


# evaluate a ready TKZip statement against the ACTIVE knowledge (archived=False). loads the
# definitions/axioms/theorems, builds the readers + forward-chainer rules/facts, runs the evaluator,
# and resolves the best relational match (matchedKind + matchedIndex) back to that document's
# id/original. PURE — stores nothing. Returns the api-shape dict MINUS "original" (the caller, which
# knows the source text, adds that): {"result", "matchedId", "matchedOriginal", "relationMatch"}.
# NB: theorems default to archived=True, so the theorem pool is empty until a theorem is promoted
# (archived=False) — expected with the current model; not worked around here.
# load the ACTIVE knowledge (archived=False) ONCE: the definition leaf clauses, the axiom/theorem
# zips + their docs (for id mapping), the injected graph readers, and the forward-chainer rules/facts.
# shared by evaluate_zip (assertions) and answer_zip (questions) so both pay the load once per call.
# a cheap signature of the ACTIVE knowledge — changes whenever a definition/axiom/theorem is added,
# archived, or re-created (incl. the brain's own materialize_theorem AND an axiom added via the api,
# since it is DB-derived and cross-process). Used to invalidate the in-process KB cache below.
def kb_fingerprint() -> str:
    def _count_and_max(model):
        n = model.find({"archived": False}).count()
        newest = model.find({"archived": False}).sort("-createdAt").limit(1).to_list()
        mx = newest[0].createdAt if newest else 0
        return n, mx
    nd, td = _count_and_max(TKDefinitionDoc)
    na, ta = _count_and_max(TKAxiomDoc)
    nt, tt = _count_and_max(TKTheoremDoc)
    return f"{nd}:{td}:{na}:{ta}:{nt}:{tt}"


# in-process KB cache, keyed by the cheap fingerprint above. _load_active_kb stays PURE (reads only;
# the cache is read-state). The reader closures it builds (relations/part_of/antonyms) are safe to
# persist across ticks — the `relations` WordNet graph is static.
_kb_cache: Optional[dict] = None
_kb_cache_fp: Optional[str] = None


def _load_active_kb() -> dict:
    global _kb_cache, _kb_cache_fp
    fp = kb_fingerprint()
    if _kb_cache is not None and _kb_cache_fp == fp:
        return _kb_cache

    definition_docs = TKDefinitionDoc.find({"archived": False}).to_list()
    axiom_docs = TKAxiomDoc.find({"archived": False}).to_list()
    theorem_docs = TKTheoremDoc.find({"archived": False}).to_list()

    # definitions are now full TKZips (single OR multi clause); flatten each into its leaf
    # clauses so the evaluator still grounds against a flat list[TKZipContent].
    definitions = [
        leaf
        for d in definition_docs if d.zip is not None
        for leaf in _zip_leaves(d.zip.items)
    ]

    # the UNIVERSAL EXTRACTOR (step 4): axioms and theorems run through the SAME front door
    # (extract_logic) — the source never gates WHAT is extracted, only the trust attached below.
    # Edges are mined IN-MEMORY at KB load, never persisted: archiving the source doc retracts its
    # logic on the next load — revocation durability by construction (finding #4). The gate judges
    # against BEDROCK only (never the union, else its own edges would look redundant).
    # THEOREM FUEL (step 3 — theorems breed theorems): active theorems yield rules/facts/edges like
    # axioms (a theorem is just a zip with provenance — the Unified-KB thesis). A derivation that
    # fires one records the THEOREM's id as a premise, so (a) provenance walks generationally (the
    # cascade follows it) and (b) min-trust flows generationally via the trust map below. Convergence
    # is safe: a theorem restating its own conclusion is a 1-premise derivation (novelty gate drops
    # it) and materialize dedups semantically.
    bedrock = _make_relations_reader()
    axiom_logic = extract_logic(axiom_docs, "axiom", bedrock)
    theorem_logic = extract_logic(theorem_docs, "theorem", bedrock)
    axiom_rules, axiom_edges = axiom_logic["rules"], axiom_logic["edges"]
    theorem_rules, theorem_facts = theorem_logic["rules"], theorem_logic["facts"]

    # UNION the low-trust definition-derived rules into the chainer's rule set — the differentia
    # PROPERTY rules (step 5, the necessary direction) and the SUFFICIENT rules (step 4, the
    # recognition direction). source_id is a stable "rule:…" key (contains "|") so a derived rule a
    # derivation fires is recorded as a revocable premise AND lowers the conclusion's trust (via
    # _conclusion_trust's per-premise map lookup), exactly like a tier edge.
    def _derived_rule_entry(r) -> dict:
        if r.kind == "sufficient":
            conds = r.conds or []
            key = (f"rule:sufficient:{r.subject}|{r.genus}|"
                   + ",".join(f"{c.get('predicate')}:{c.get('object') or ''}" for c in conds))
            return {"kind": "sufficient", "klass": r.subject, "genus": r.genus, "conds": conds,
                    "original": r.source_original, "source_id": key}
        return {
            "subject": r.subject, "predicate": r.predicate, "object": r.object,
            "negated": r.negated, "kind": r.kind, "original": r.source_original,
            "source_id": f"rule:{r.subject}|{r.predicate}" + (f"|{r.object}" if r.object else ""),
        }

    derived_rule_docs = TKDerivedRuleDoc.find({}).to_list()
    derived_rules = [_derived_rule_entry(r) for r in derived_rule_docs]

    # the in-memory edge union: axiom edges at curated-source trust; a theorem-derived edge (rare —
    # noun-noun copular conclusions barely materialize today, but the shape extracts source-agnostically)
    # at the SOURCE THEOREM's own trust (generational min-trust, same principle as theorem rules).
    theorem_trust_by_id = {str(t.id): t.trusted for t in theorem_docs}
    axiom_children: dict[str, list[str]] = {}
    for e in axiom_edges + theorem_logic["edges"]:
        axiom_children.setdefault(e["subject"], []).append(e["object"])

    # PER-PREMISE trust map ("|"-bearing premise key -> source trust), consumed by _conclusion_trust
    # (min-trust inheritance). Definition-derived edges/rules carry their stored tier trust; an
    # axiom-derived generic edge is curated-source high trust; a theorem-derived edge carries its
    # source theorem's `trusted` (so a child of a 0.7 theorem never exceeds 0.7). On a key collision
    # (same edge asserted by two sources) the HIGHER-trust source wins — insertion order does that
    # (definition 0.3 -> theorem ≤0.9 -> axiom 0.9).
    derived_edge_docs = TKDerivedRelationDoc.find({}).to_list()
    edge_trust: dict[str, float] = {}
    for d in derived_edge_docs:
        edge_trust[_edge_key(d.subject, d.object)] = d.trust
    for r_doc, r in zip(derived_rule_docs, derived_rules):
        edge_trust[r["source_id"]] = r_doc.trust
    for e in theorem_logic["edges"]:
        edge_trust[_edge_key(e["subject"], e["object"])] = theorem_trust_by_id.get(
            e["source_id"], _DERIVED_DEFAULT_TRUST)
    for e in axiom_edges:
        edge_trust[_edge_key(e["subject"], e["object"])] = _AXIOM_EDGE_TRUST
    for t in theorem_docs:
        edge_trust[str(t.id)] = t.trusted            # generational min-trust (step 3)

    # EDGE -> SOURCE DOCS (belief-revision v1, retreat arc #4): which stored docs an in-memory edge
    # was mined from. The retreat mechanism IS "archive the source doc" (revocation durability by
    # construction — an archived doc simply stops yielding its edges at the next KB load), so a
    # correction needs to walk from the defeated edge back to the docs that assert it. Definition-tier
    # edges are mapped too but marked: v1 never retracts vocabulary on conversational say-so.
    edge_doc_sources: dict[str, list[dict]] = {}
    doc_originals = {str(a.id): a.original for a in axiom_docs}
    doc_originals.update({str(t.id): t.original for t in theorem_docs})
    axiom_readonly = {str(a.id): bool(a.readonly) for a in axiom_docs}
    for e in axiom_edges:
        edge_doc_sources.setdefault(_edge_key(e["subject"], e["object"]), []).append(
            {"kind": "axiom", "id": e["source_id"], "original": doc_originals.get(e["source_id"], ""),
             # readonly = the hardwired seed-tier protection: a readonly axiom cannot be archived,
             # so it is NEVER conversationally retractable (the author's API privilege only).
             "readonly": axiom_readonly.get(e["source_id"], True)})
    for e in theorem_logic["edges"]:
        edge_doc_sources.setdefault(_edge_key(e["subject"], e["object"]), []).append(
            {"kind": "theorem", "id": e["source_id"], "original": doc_originals.get(e["source_id"], "")})
    for d in derived_edge_docs:
        edge_doc_sources.setdefault(_edge_key(d.subject, d.object), []).append(
            {"kind": "definition-tier", "id": str(d.id), "original": d.source_original})
    # a generalization has TWO KB representations (kb_extract): a generic copular mints an EDGE,
    # an explicit universal («all softwares are minds») becomes a MEMBERSHIP RULE. Both assert
    # "subject is_a predicate" — a correction must reach either, so unconditioned positive
    # membership rules enter the same map under the same edge key.
    for r, kind in ([(r, "axiom") for r in axiom_rules] + [(r, "theorem") for r in theorem_rules]):
        if (r.get("kind") == "membership" and not r.get("negated")
                and not r.get("cond_props") and r.get("subject") and r.get("predicate")):
            entry = {"kind": kind, "id": r["source_id"], "original": r.get("original", "")}
            if kind == "axiom":
                entry["readonly"] = axiom_readonly.get(r["source_id"], True)
            edge_doc_sources.setdefault(_edge_key(r["subject"], r["predicate"]), []).append(entry)
    # 2d: a conclusion derived THROUGH a generic rule is defeasible — the rule's source id enters the
    # trust map at generic strength (min with any theorem trust already there), and min-trust does
    # the rest (both materialize paths).
    for r in axiom_rules + theorem_rules:
        if r.get("strength") == "generic":
            edge_trust[r["source_id"]] = min(
                edge_trust.get(r["source_id"], _DERIVED_DEFAULT_TRUST), _GENERIC_RULE_TRUST)

    # every DISTINCT subject of a derived rule/edge (definition tier OR axiom-mined) is a wondering
    # SEED, so the cascade fires from the vocabulary itself (a subclass inherits a superclass's
    # rule via a derived edge -> >=2 premises), not only from axiom-rule subjects + individuals.
    # (sufficient rules carry no "subject" — they conclude a class, they don't describe one; they
    # fire on individuals via property facts, so they contribute no class seed.)
    tier_subjects = sorted({e.subject for e in derived_edge_docs}
                           | {r["subject"] for r in derived_rules if "subject" in r}
                           | set(axiom_children.keys()))

    kb = {
        "definition_docs": definition_docs,
        "axiom_docs": axiom_docs,
        "theorem_docs": theorem_docs,
        "definitions": definitions,
        "axiom_zips": [a.zip for a in axiom_docs],
        "theorem_zips": [t.zip for t in theorem_docs],
        # evaluator/chainer see bedrock ∪ derived tier ∪ in-memory axiom edges
        "relations": _make_relations_reader_union(axiom_children),
        # derived-edge provenance (revocable premises), axiom edges included
        "edge_source": _make_edge_source_reader(axiom_children),
        "part_of": _make_partof_reader(),
        "antonyms": _make_antonym_reader(),
        "senses_of": _make_senses_reader(),
        # the PLACES BRIDGE readers (lib/core/places.py, module-cached — the table is static):
        # containment over the complete path_admin/path_geo chains, the type-column is_a synthesis,
        # and the immediate container ("where is Rome?" -> "lazio"). lazy reads of the curated 4.7M
        # table — never materialized into the relations collection.
        "place_contains": place_contains,
        "place_type": place_type_of,
        "place_parent": place_parent,
        "rules": axiom_rules + derived_rules + theorem_rules,
        "facts": axiom_logic["facts"] + theorem_facts,
        "tier_subjects": tier_subjects,
        "axiom_edges": axiom_edges,
        "edge_trust": edge_trust,
        "edge_doc_sources": edge_doc_sources,   # belief-revision v1: edge key -> the docs asserting it
    }
    _kb_cache, _kb_cache_fp = kb, fp
    return kb


# ------------------------------------------------------------------------------------------------
# KB-WONDERING (wondering-v2 1d) — the parser-free SEED DRIVER for self-prompted KB derivation.
# Where memory-wondering re-examines stored ASSERTIONS, KB-wondering forward-SATURATES the KB itself:
# it seeds the forward-chainer from every entity tokeniko knows and derives what the KB collectively
# IMPLIES but no one ever asserted ("matching memory against itself"). The genuinely-new theorems.
#
# SEEDS (flat-cost — bounded by the small rule/fact counts, NEVER the 150k-edge graph):
#   INDIVIDUALS — every uid that has a fact (tokeniko, Mari, …): forward-chain from the uid. Yields
#       concrete derivations ("Mari is mortal" = the membership fact + the mortality rule).
#   CLASSES — every sense that is a rule subject (carnivore, homo, …): forward-chain from the sense.
#
# NOVELTY GATE — materialize ONLY a derivation that COMBINES >= 2 KB premises. A 1-premise derivation
# is a single rule fired on its own subject class ("all birds have feathers" -> "bird has feathers"),
# a restatement that adds nothing; >= 2 premises means genuine inference across KB items. (Stricter
# than 1b's >=1 "not pure-taxonomic" floor — this is the "is it WORTH keeping" bar.) DEDUP by the
# semantic conclusion signature (subject, predicate, object, negated) so each truth surfaces once.
#
# RETURNS the genuinely-new conclusions: {subject, subject_kind, predicate, object, negated, chain,
# premises}. PURE — derives only; rendering + materialization is the caller's (1d-B renderer + the API).
_NOVELTY_MIN_PREMISES = 2

def kb_wonder(kb: Optional[dict] = None, collect_conflicts: Optional[list] = None) -> list[dict]:
    kb = kb or _load_active_kb()
    rules, facts, parents = kb["rules"], kb["facts"], kb["relations"]
    edge_source = kb.get("edge_source")

    # seeds: (subject, subject_uid, subject_sense, kind). individuals chain from the uid; classes
    # from the sense. dedup the seed set itself (a uid/sense appears in many facts/rules).
    seeds: list[tuple] = []
    seen_seeds: set = set()
    for f in facts:
        uid = f.get("subject_uid")
        if uid and uid not in seen_seeds:
            seen_seeds.add(uid)
            seeds.append((uid, uid, None, "individual"))
    for r in rules:
        cs = r.get("subject")
        if cs and cs not in seen_seeds:
            seen_seeds.add(cs)
            seeds.append((cs, None, cs, "class"))
    # + every definition-derived (tier) subject, so the differentia cascade fires from the vocabulary
    # itself: a subclass reaching a superclass rule via a tier edge yields a >=2-premise theorem.
    for cs in kb.get("tier_subjects", []):
        if cs and cs not in seen_seeds:
            seen_seeds.add(cs)
            seeds.append((cs, None, cs, "class"))

    if _WONDER_VERBOSE:
        n_ind = sum(1 for s in seeds if s[3] == "individual")
        n_cls = len(seeds) - n_ind
        n_derived_rules = sum(1 for r in rules if str(r.get("source_id", "")).startswith("rule:"))
        logger.info(
            "[kb_wonder] seeds=%d (%d individuals, %d classes) | rules=%d (%d axiom + %d differentia) | facts=%d | axiom edges=%d",
            len(seeds), n_ind, n_cls, len(rules), len(rules) - n_derived_rules, n_derived_rules,
            len(facts), len(kb.get("axiom_edges", [])),
        )

    out: list[dict] = []
    seen_conclusions: set = set()
    n_1prem = 0    # dropped by the novelty gate (single-rule restatement)
    n_dup = 0      # dropped by semantic dedup
    n_conflict = 0  # dropped by the derivation mirror (a self-contradicted chain)
    n_total_derived = 0
    for subject, uid, sense, kind in seeds:
        derived, _ = evaluator_forwardChain(sense, uid, rules, parents, facts, edge_source=edge_source)
        n_total_derived += len(derived)
        for d in derived:
            # THE DERIVATION MIRROR (2026-07-18, the not-an-animal theorem): a conclusion whose
            # own chain also supports its opposite is proof the PREMISES are inconsistent, never a
            # truth — logic is sacred, it must not materialize. Logged LOUDLY: it is a lead that
            # some premise is wrong (the premise-retreat consumer is D-phase work).
            if d.get("conflict"):
                n_conflict += 1
                logger.warning("[kb_wonder] DERIVATION CONFLICT on %s: %s — not materialized "
                               "(a premise is wrong; premises=%s)",
                               subject, d["chain"], sorted(d.get("premises", [])))
                # the reductio action (roadmap §0 slice 1): recognition is only half the r.a.a. —
                # surface the conflict to the caller (brain/thinking's reductio reconcile), which
                # turns it into a QUESTION to the premise-givers. Same shape as a conclusion.
                if collect_conflicts is not None:
                    collect_conflicts.append({
                        "subject": subject, "subject_kind": kind,
                        "predicate": d["predicate"], "object": d.get("object"),
                        "negated": bool(d.get("negated", False)),
                        "chain": d["chain"], "premises": d.get("premises", []),
                    })
                continue
            premises = d.get("premises", [])
            if len(premises) < _NOVELTY_MIN_PREMISES:
                n_1prem += 1
                continue  # novelty gate: a single-rule restatement is not a new theorem
            sig = (subject, d["predicate"], d.get("object"), bool(d.get("negated", False)))
            if sig in seen_conclusions:
                n_dup += 1
                continue  # semantic dedup across seeds
            seen_conclusions.add(sig)
            trust = _conclusion_trust(premises, kb.get("edge_trust"))
            out.append({
                "subject": subject,
                "subject_kind": kind,
                "predicate": d["predicate"],
                "object": d.get("object"),
                "negated": bool(d.get("negated", False)),
                "chain": d["chain"],
                "premises": premises,
                # min-trust inheritance: a conclusion resting on a low-trust tier edge is stored honestly
                # low-trust + revisable, never laundered to the 0.9 default (truth ⟂ trust).
                "trust": trust,
            })
            if _WONDER_VERBOSE:
                obj = f" {_short(d.get('object'))}" if d.get("object") else ""
                logger.info(
                    "[kb_wonder]   NEW  %s(%s) %s%s%s  | trust=%.2f premises=%d  chain=%s",
                    _short(subject), kind, "NOT " if d.get("negated") else "",
                    _short(d["predicate"]), obj, trust, len(premises), d["chain"],
                )
    if _WONDER_VERBOSE:
        logger.info(
            "[kb_wonder] done: %d NEW conclusions | %d derivations across %d seeds "
            "| dropped(1-premise=%d, dup=%d, CONFLICT=%d)",
            len(out), n_total_derived, len(seeds), n_1prem, n_dup, n_conflict,
        )
    return out


def evaluate_zip(statement: TKZip) -> dict:
    kb = _load_active_kb()
    axiom_docs, theorem_docs = kb["axiom_docs"], kb["theorem_docs"]
    result = evaluator_evaluateStatement(
        statement, kb["definitions"], kb["axiom_zips"], kb["theorem_zips"],
        relations=kb["relations"], part_of=kb["part_of"], antonyms=kb["antonyms"],
        senses_of=kb["senses_of"],
        rules=kb["rules"], facts=kb["facts"], edge_source=kb["edge_source"],
        place_contains=kb["place_contains"], place_type=kb["place_type"],
    )

    # map the best (kind, index) back to a concrete document
    matchedId = None
    matchedOriginal = None
    if result.matchedKind == "axiom" and result.matchedIndex is not None:
        doc = axiom_docs[result.matchedIndex]
        matchedId, matchedOriginal = str(doc.id), doc.original
    elif result.matchedKind == "theorem" and result.matchedIndex is not None:
        doc = theorem_docs[result.matchedIndex]
        matchedId, matchedOriginal = str(doc.id), doc.original

    return {
        "result": result,
        "matchedId": matchedId,
        "matchedOriginal": matchedOriginal,
        "relationMatch": result.relationMatch,
    }


# strong-conclusion bands (mirror brain.thinking): a polar question -> YES / NO / I-don't-know.
_TRUE_FLOOR = 0.85
_FALSE_CEIL = 0.15


# map a grounded EvaluatorResult to a POLAR answer. logic-is-sacred: a self-contradictory polar
# question ("the cat is dead and alive?") is a definitive, confident NO — not a mid/insufficient.
def _polar_answer(result: EvaluatorResult) -> AnswerResult:
    if result.status == EvaluatorStatus.INCONSISTENT:
        return AnswerResult(
            kind=AnswerKind.POLAR, verdict=AnswerVerdict.NO, confidence=1.0,
            reason=result.inconsistency or "logically inconsistent", derivation=list(result.derivation),
        )
    if result.status == EvaluatorStatus.RESOLVED:
        if result.truth > _TRUE_FLOOR:
            return AnswerResult(kind=AnswerKind.POLAR, verdict=AnswerVerdict.YES,
                                confidence=result.truth, derivation=list(result.derivation))
        if result.truth < _FALSE_CEIL:
            return AnswerResult(kind=AnswerKind.POLAR, verdict=AnswerVerdict.NO,
                                confidence=1.0 - result.truth, derivation=list(result.derivation))
    return AnswerResult(kind=AnswerKind.POLAR, verdict=AnswerVerdict.UNKNOWN, confidence=0.5,
                        reason="insufficient knowledge to answer")


# answer a QUESTION zip (mood read from the leaves: dubitative=1 -> question, wh_role -> the gap).
# returns None when the statement is NOT interrogative (caller uses evaluate_zip instead). a question
# is ANSWERED, never believed — this stores nothing, and the brain skips the assertion/cross-item
# paths. POLAR -> reuse the grounded truth (inconsistent -> confident NO); WH -> solve the gap role.
def answer_zip(statement: TKZip) -> Optional[dict]:
    leaves = _zip_leaves(statement.items)
    if not any(getattr(l, "dubitative", 0.5) >= 0.999 for l in leaves):
        return None  # not interrogative
    wh_leaf = next((l for l in leaves if getattr(l, "wh_role", None) is not None), None)

    kb = _load_active_kb()
    result = evaluator_evaluateStatement(
        statement, kb["definitions"], kb["axiom_zips"], kb["theorem_zips"],
        relations=kb["relations"], part_of=kb["part_of"], antonyms=kb["antonyms"],
        senses_of=kb["senses_of"],
        rules=kb["rules"], facts=kb["facts"], edge_source=kb["edge_source"],
        place_contains=kb["place_contains"], place_type=kb["place_type"],
    )

    if wh_leaf is None:
        answer = _polar_answer(result)
    else:
        answer = evaluator_solveWh(wh_leaf, kb["axiom_zips"], kb["theorem_zips"], kb["relations"],
                                   assertion=result, place_parent=kb["place_parent"])

    return {"answer": answer, "result": result}
