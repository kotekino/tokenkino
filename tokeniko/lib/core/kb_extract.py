# --------------------------------------------------------------
# lib/core/kb_extract.py — the definition→is_a EXTRACTOR + gate (definitions-as-rules, step 3).
#
# PURE + parser-free: mine each definition's main copular clause ("an X is a ⟨genus⟩") into a candidate
# is_a edge (subject_sense -> genus_sense), then GATE it against tokeniko's OWN bedrock is_a graph so
# only clean, graph-consistent edges reach the low-trust tier. The single source of truth for the gate
# — the read-only probe (scripts/probe_extractor.py, the ruler) and the writer (scripts/extract_
# definitions.py) both call extract_isa_edges(), so they can never drift.
#
# Governing principle: asymmetric risk -> reject-on-doubt (a false is_a edge poisons ALL downstream
# reasoning). The gate (validated in the step-3 dry-run, see doc/ref/landed.md):
#   REDUNDANT     — the bedrock graph already derives subject is_a genus -> drop (adds nothing).
#   PLACEHOLDER   — a metalinguistic genus (name/term/word/designation) is a gloss artifact, not a
#                   hypernym ("a beer is a general NAME for…") -> drop structurally.
#   CYCLE         — subject is already an is_a ancestor of the genus -> subject->genus closes a loop.
#   DISJOINT(1/2) — the senses are disjoint at a RELIABLE ontological tier (1 biological kingdoms /
#                   2 organism-artifact-substance). tier 3 (physical⊥abstract) is DROPPED for admission
#                   — it false-rejects true cross-abstraction edges (agent→cause); a coarse REFUTATION
#                   tool must not be repurposed as an ADMISSION gate (see doc reference geometry-not-isa).
# Everything else is ACCEPTED. The caller (writer) attaches trust/method/provenance and persists.
# --------------------------------------------------------------
from collections import Counter

from lib.core.evaluation_harness import _zip_leaves
from lib.core.tk import TKQuantifier
from lib.llc.evaluator.e_relations import relations_subsumes, relations_disjoint, relations_isa_ancestors

# reliable disjointness tiers for ADMISSION. tier 1 (biological kingdoms) + tier 2 (organism/artifact/
# substance) are trustworthy; tier 3 (physical⊥abstract) is NOT — WordNet arbitrarily files polysemous
# nouns on either side. We reject a candidate ONLY when the disjointness fires at tier 1 or 2.
_T1 = {"animal.n.01", "plant.n.02", "fungus.n.01", "fungus.n.02", "bacteria.n.01", "microorganism.n.01"}
_T2 = {"organism.n.01", "artifact.n.01", "natural_object.n.01", "substance.n.01"}
_T3 = {"physical_entity.n.01", "abstraction.n.06"}

# metalinguistic placeholder heads that are NEVER a real is_a hypernym (gloss artifacts). conservative:
# only the unambiguously-metalinguistic words, so no legitimate abstract genus (process/state/group…)
# is ever dropped.
_PLACEHOLDER_GENERA = {"name", "term", "word", "designation"}


def _is_noun(sense) -> bool:
    return bool(sense) and ".n." in sense


def _genus_lemma(sense: str) -> str:
    return (sense or "").split(".", 1)[0]


def _pos(sense: str) -> str:
    for tag in (".n.", ".v.", ".a.", ".s.", ".r."):
        if sense and tag in sense:
            return tag.strip(".")
    return "?"


# ================================================================================================
# DIFFERENTIA → universal PROPERTY RULES (definitions-as-rules, step 5). Mine "an X is a <genus> that
# <differentia>" into the rule "all X <differentia>", gated STRICTLY (a false rule poisons every
# subclass it fires on). The gate, validated in the step-5.1 dry-run (scripts/probe_differentia.py):
#   ABSTRACT genus  — genus under abstraction.n.06 (not physical_entity) -> the differentia describes
#                     the BEARER, not X ("an ability is the QUALITY of being able to PERFORM").
#   NOUN differentia — a genus-disjunction alt ("a structure OR object") / appositive -> noise.
#   VERB w/o object  — a passive reduced-relative ("equipped WITH") or unconfirmed intransitive; agency
#                      isn't recoverable from the zip -> drop (verb recovery is PARKED: parser voice).
#   CIRCULAR         — predicate ~ X ("ability -> able").
# An AGENTIVE transitive verb carries its direct object ("eat MEAT"); an adjective is "X is <adj>".
# ================================================================================================
_ABSTRACTION_ROOT = "abstraction.n.06"
_PHYSICAL_ROOT = "physical_entity.n.01"


def _make_is_abstract(parents):
    cache: dict[str, bool] = {}

    def is_abstract(sense: str) -> bool:
        if sense not in cache:
            anc = set(relations_isa_ancestors(sense, parents).keys()) | {sense}
            cache[sense] = (_ABSTRACTION_ROOT in anc) and (_PHYSICAL_ROOT not in anc)
        return cache[sense]

    return is_abstract


# the gate verdict for one differentia candidate. Returns "abstract" | "circular" | "noun" |
# "verb_noobj" | "accept".
def gate_differentia(X: str, genus: str, pred: str, obj, is_abstract) -> str:
    if is_abstract(genus):
        return "abstract"
    if _genus_lemma(pred)[:4] and _genus_lemma(pred)[:4] == _genus_lemma(X)[:4]:
        return "circular"
    pos = _pos(pred)
    if pos == "n":
        return "noun"
    if pos == "v" and not obj:
        return "verb_noobj"
    return "accept"


# extract the ACCEPTED low-trust universal property RULES from the definitions' differentia, gated
# against the bedrock is_a graph (`parents`). Returns (rules, stats):
#   rules = [{subject, predicate, object, negated, source_id, source_original}, ...]  (kind=property; caller adds trust/method)
#   stats = Counter {candidate, abstract, circular, noun, verb_noobj, accept}
def extract_differentia_rules(definition_docs, parents) -> tuple[list[dict], Counter]:
    is_abstract = _make_is_abstract(parents)
    stats: Counter = Counter()
    rules: list[dict] = []
    seen: set = set()
    for d in definition_docs:
        leaves = _zip_leaves(d.zip.items) if d.zip else []
        X = genus = genus_leaf = None
        for lf in leaves:
            s = getattr(lf, "senses", None) or {}
            subj, pred = s.get("subject"), s.get("predicate")
            if subj and pred and ".n." in subj and ".n." in pred and subj != pred:
                X, genus, genus_leaf = subj, pred, lf
                break
        if not X or not genus:
            continue
        for lf in leaves:
            if lf is genus_leaf:
                continue
            s = getattr(lf, "senses", None) or {}
            if s.get("subject") != X:
                continue
            pred = s.get("predicate")
            if not pred or pred == genus:
                continue
            obj = s.get("direct")
            stats["candidate"] += 1
            verdict = gate_differentia(X, genus, pred, obj, is_abstract)
            stats[verdict] += 1
            if verdict != "accept":
                continue
            negated = bool(getattr(lf, "negated", False))
            key = (X, pred, obj, negated)
            if key in seen:
                continue
            seen.add(key)
            rules.append({
                "subject": X,
                "predicate": pred,
                "object": obj,
                "negated": negated,
                "source_id": str(d.id),
                "source_original": d.original,
            })
    return rules, stats


def _disjoint_tier(note: str) -> int:
    for tok in note.replace(" ⊥", " ").split():
        if tok in _T1:
            return 1
        if tok in _T2:
            return 2
        if tok in _T3:
            return 3
    return 0


# candidate genus edges (one per definition, main clause): the FIRST leaf whose subject + predicate are
# both noun senses (the taxonomic spine), no self-edge. Reads the STORED (recompiled, sense-faithful)
# zips — no parser. Returns [(subject_sense, genus_sense, doc), ...].
def _candidate_edges(definition_docs):
    out = []
    for d in definition_docs:
        leaves = _zip_leaves(d.zip.items) if d.zip else []
        for lf in leaves:
            s = getattr(lf, "senses", None) or {}
            subj, genus = s.get("subject"), s.get("predicate")
            if _is_noun(subj) and _is_noun(genus) and subj != genus:
                out.append((subj, genus, d))
                break  # main clause only
    return out


# the gate verdict for one candidate edge, given the bedrock is_a reader `parents`. Returns one of:
# "redundant" | "placeholder" | "cycle" | "disjoint" | "accept".
def gate_edge(subject_sense: str, genus_sense: str, parents) -> str:
    if relations_subsumes(genus_sense, subject_sense, parents) is not None:
        return "redundant"                                       # bedrock already derives it
    if _genus_lemma(genus_sense) in _PLACEHOLDER_GENERA:
        return "placeholder"                                     # gloss artifact
    if relations_subsumes(subject_sense, genus_sense, parents) is not None:
        return "cycle"                                           # subject already an ancestor of genus
    witness = relations_disjoint(subject_sense, genus_sense, parents)
    if witness is not None and _disjoint_tier(witness[-1]) in (1, 2):
        return "disjoint"                                        # reliable-tier ontological conflict
    return "accept"


# ================================================================================================
# GENERIC-COPULAR AXIOM → is_a EDGES (Brain v1.1, step 2 — the universal-extractor v0). Mine a
# GENERIC-quantified copular noun predication ("a cat is a mammal", "cats are mammals") out of the
# AXIOMS into a candidate is_a edge (subject_sense -> predicate_sense), gated by the SAME gate_edge
# as the definition tier (single source of truth: the step-2 probe and the writer both call this).
#
# The candidate SHAPE (finding #1's gap — today these leaves reach neither _extract_rules, which
# requires UNIVERSAL, nor _extract_facts, which requires an identity-linked individual subject):
#   - subject sense + predicate sense both NOUN, subject != predicate, NO direct object (bare copular
#     class predication, mirroring the definition extractor's taxonomic spine);
#   - NO subject identity uid (an individual "kotekino is a human" is a FACT, never a class edge);
#   - quantifier in `quantifiers` (default GENERIC + INDEFINITE — the step-2 probe showed the
#     indefinite generic "a cat is a mammal" is admissible once "a/an" is split off EXISTENTIAL,
#     while the true existential "some birds are pets" must NOT become an edge and stays excluded);
#   - NOT negated (a negated generic "a dog is not a cat" is a DISJOINTNESS candidate — future work,
#     counted in stats as negated_skip, never silently dropped);
#   - NOT a question (dubitative >= 0.75 or a wh gap — questions are answered, not believed).
# Accepted edges carry provenance (source axiom); the caller attaches trust/method and persists.
# ================================================================================================
def extract_generic_isa_edges(axiom_docs, parents,
                              quantifiers=(TKQuantifier.GENERIC, TKQuantifier.INDEFINITE),
                              ) -> tuple[list[dict], Counter]:
    stats: Counter = Counter()
    edges: list[dict] = []
    seen: set = set()
    for doc in axiom_docs:
        leaves = _zip_leaves(doc.zip.items) if getattr(doc, "zip", None) else []
        for lf in leaves:
            s = getattr(lf, "senses", None) or {}
            subj, pred = s.get("subject"), s.get("predicate")
            # the taxonomic SHAPE first (noun-noun bare copular, class subject)
            if not (_is_noun(subj) and _is_noun(pred)) or subj == pred or s.get("direct"):
                continue
            stats["shape"] += 1
            if (getattr(lf, "identities", None) or {}).get("subject"):
                stats["individual_fact"] += 1                    # _extract_facts territory
                continue
            q = getattr(lf, "quantifier", None)
            if q == TKQuantifier.UNIVERSAL:
                stats["universal_rule"] += 1                     # _extract_rules territory
                continue
            if q not in quantifiers:
                stats["quantifier_skip"] += 1
                continue
            if getattr(lf, "dubitative", 0.5) >= 0.75 or getattr(lf, "wh_role", None) is not None:
                stats["question_skip"] += 1
                continue
            if bool(getattr(lf, "negated", False)):
                stats["negated_skip"] += 1                       # future: disjointness candidate
                continue
            if any(k.startswith("subject_mod") for k in s):
                stats["restricted"] += 1                         # "a THINKING machine is a mind":
                continue                                         # a graph edge can't carry the
                                                                 # condition -> conditioned RULE
                                                                 # territory (_extract_rules)
            stats["candidate"] += 1
            verdict = gate_edge(subj, pred, parents)
            stats[verdict] += 1
            if verdict != "accept":
                continue
            key = (subj, pred)
            if key in seen:
                continue
            seen.add(key)
            edges.append({
                "subject": subj,
                "object": pred,
                "source_id": str(doc.id),
                "source_original": doc.original,
            })
    return edges, stats


# extract the ACCEPTED low-trust is_a edges from the definitions, gated against the bedrock graph.
# `parents` is the injected BEDROCK is_a reader (sense -> direct hypernyms) — NEVER the union reader,
# so the gate judges candidates against the trusted graph only. Returns (edges, stats):
#   edges = [{subject, object, source_id, source_original}, ...]  (relation is is_a; caller adds trust/method)
#   stats = Counter of {candidate, redundant, placeholder, cycle, disjoint, accept}
def extract_isa_edges(definition_docs, parents) -> tuple[list[dict], Counter]:
    stats: Counter = Counter()
    edges: list[dict] = []
    seen: set = set()
    for subj, genus, doc in _candidate_edges(definition_docs):
        stats["candidate"] += 1
        verdict = gate_edge(subj, genus, parents)
        stats[verdict] += 1
        if verdict != "accept":
            continue
        key = (subj, genus)
        if key in seen:
            continue                                             # dedup identical edges across defs
        seen.add(key)
        edges.append({
            "subject": subj,
            "object": genus,
            "source_id": str(doc.id),
            "source_original": doc.original,
        })
    return edges, stats
