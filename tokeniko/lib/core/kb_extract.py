# --------------------------------------------------------------
# lib/core/kb_extract.py — the UNIVERSAL EXTRACTOR (Brain v1.1 step 4): TKZip → usable logic.
#
# PURE + parser-free. ONE source-agnostic home for every "stored zip → chainable logic" path — is_a
# edges, membership/property/property-conditioned rules, individual facts — with a per-shape GATE
# judged against tokeniko's OWN bedrock is_a graph. The collection an item comes from (definition /
# axiom / theorem) never gates WHETHER logic is extracted — only the TRUST it carries (the Unified-KB
# thesis, doc/ref/brain-v1.1.md). `extract_logic(docs, source, parents)` is the one front door; the
# per-shape extractors below are its organs (still individually importable — the read-only probes and
# the tier writers call the same functions, so ruler and writer can never drift).
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
from typing import Optional

from lib.core.tk import TKOperator, TKQuantifier
from lib.core.tkzip import TKZipContent
from lib.llc.evaluator.e_relations import relations_subsumes, relations_disjoint, relations_isa_ancestors


# collect every leaf TKZipContent of a zip item tree, in order. (Homed here — the extractor layer —
# since step 4; evaluation_harness re-exports it for its many probe/brain callers.)
def _zip_leaves(item) -> list:
    c = item.content
    if isinstance(c, TKZipContent):
        return [c]
    out = []
    if isinstance(c, list):
        for child in c:
            out += _zip_leaves(child)
    return out


# like _zip_leaves, but returns the leaf-level TKZipItem WRAPPERS (which carry the .op) rather than the
# bare contents — needed to read the operator (AND/IMPLY/...) a leaf folds with. used to recognize the
# IMPLY pattern of a property-conditioned rule (see _extract_property_conditioned).
def _zip_leaf_items(item) -> list:
    c = item.content
    if isinstance(c, TKZipContent):
        return [item]
    out = []
    if isinstance(c, list):
        for child in c:
            out += _zip_leaf_items(child)
    return out

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


# ================================================================================================
# AXIOM/THEOREM RULES + FACTS (moved here from evaluation_harness in step 4 — verbatim semantics).
# extract RULES from the active axioms/theorems for the forward-chainer. three quantifier shapes
# qualify (Brain v1.1 step 2 widened this beyond UNIVERSAL — bare-plural generics are how people
# naturally state universals; the step-2 census showed the curated imprint itself phrases rules
# that way):
#   UNIVERSAL — "all carnivores eat meat", "all humans are thinkers" (the original path).
#   GENERIC / INDEFINITE class-subject — "humans create their gods", "truth is relative",
#       "violence generates violence": a CLASS subject (sense, no identity uid — an individual is a
#       FACT) read as a defeasible universal. EXCEPT the bare copular noun-noun shape ("a cat is a
#       mammal") — that is the generic-taxonomy EDGE extractor's territory (extract_generic_isa_edges,
#       unioned into the relations reader), and double-representing it would duplicate derivations.
#   NEGATIVE — "no mind can reach absolute truth": a negated universal (rule negated = NEGATIVE XOR
#       leaf.negated, the evaluator's own net-flip). Only the property shape; a NEGATIVE copular
#       noun-noun ("no machine is a human") is a DISJOINTNESS claim — future work, skipped here.
# the predicate POS classifies the rule: a NOUN predicate (".n.") is a MEMBERSHIP rule (subject
# is_a* S => subject is_a [predicate class]); anything else (".a."/".s."/".v.") is a PROPERTY rule.
# ================================================================================================
_RULE_GENERIC_QUANTIFIERS = (TKQuantifier.GENERIC, TKQuantifier.INDEFINITE)


# collect the ordered "<prefix>0", "<prefix>1", … sense keys from a leaf's senses dict (the
# restrictive-modifier carriers, compiler_contentSenses — finding #5 / Brain v1.1 2c).
def _mod_senses(senses: dict, prefix: str) -> list[str]:
    out, i = [], 0
    while f"{prefix}{i}" in senses:
        out.append(senses[f"{prefix}{i}"])
        i += 1
    return out


def extract_rules(docs) -> list:
    rules: list = []
    for doc in docs:
        if doc.zip is None:
            continue
        for leaf in _zip_leaves(doc.zip.items):
            quantifier = getattr(leaf, "quantifier", None)
            senses = getattr(leaf, "senses", None) or {}
            subject = senses.get("subject")
            predicate = senses.get("predicate")
            if not subject or not predicate:
                continue
            negated = bool(getattr(leaf, "negated", False))
            # the subject's RESTRICTIVE modifiers (finding #5 / 2c): "all THINKING machines …" must
            # fire only on subjects that HAVE the modifier property — carried as rule conditions.
            cond_props = _mod_senses(senses, "subject_mod")
            if quantifier == TKQuantifier.UNIVERSAL:
                pass  # the original path — always a rule
            elif quantifier in _RULE_GENERIC_QUANTIFIERS or quantifier == TKQuantifier.NEGATIVE:
                if (getattr(leaf, "identities", None) or {}).get("subject"):
                    continue  # an individual subject is a FACT (extract_facts), never a rule
                if getattr(leaf, "dubitative", 0.5) >= 0.75 or getattr(leaf, "wh_role", None) is not None:
                    continue  # a question is answered, not believed
                if ".n." in predicate and not senses.get("direct") and not cond_props:
                    continue  # bare copular noun-noun: EDGE (generic-taxonomy) or disjointness (future)
                    # (a MODIFIED one — "a thinking machine is a mind" — stays here as a conditioned
                    # membership rule: a graph edge cannot carry a condition)
                if quantifier == TKQuantifier.NEGATIVE:
                    negated = not negated  # the net-flip: "no X <pred>" == "all X NOT <pred>"
            else:
                continue  # EXISTENTIAL/DEFINITE never generalize to a rule
            kind = "membership" if ".n." in predicate else "property"
            rules.append({
                "subject": subject,
                "predicate": predicate,
                "object": senses.get("direct"),
                "negated": negated,
                "kind": kind,
                "cond_props": cond_props,
                # 2d: a generic rule is defeasible, a universal is law. NEGATIVE ("no X …") is a
                # negative UNIVERSAL. Consumed by the chain renderer ("most" vs "all") and the
                # trust map (_GENERIC_RULE_TRUST) in _load_active_kb.
                "strength": "generic" if quantifier in _RULE_GENERIC_QUANTIFIERS else "universal",
                "original": doc.original,
                "source_id": str(doc.id),  # provenance: the KB doc this rule comes from
            })
        # PROPERTY-CONDITIONED rule: a universal IMPLY over two sense-less-subject predications
        # ("everything that thinks exists" => think ⟹ exist). Recognized from the compiled IMPLY form
        # rather than per-leaf (the leaves carry no subject sense), so it is NL-seedable as a real KB
        # axiom — no hardcoded foundational rule.
        pc = _extract_property_conditioned(doc.zip)
        if pc is not None:
            rules.append({**pc, "original": doc.original, "source_id": str(doc.id)})
    return rules


# detect a property-conditioned rule in a compiled zip: a universal IMPLY(antecedent, consequent) whose
# operands are both SENSE-LESS-subject predications (an indefinite universal "everything/everyone that
# <cond> <concl>"). returns {kind, cond_pred, cond_obj, concl_pred, concl_obj, concl_negated} or None.
# the antecedent leaf folds with op=AND (seeds), the consequent leaf carries op=IMPLY (see the compiler's
# property-restricted-universal transform). mirrors the shape the old _FOUNDATIONAL_RULES hand-wrote.
def _extract_property_conditioned(statement) -> Optional[dict]:
    items = _zip_leaf_items(statement.items)
    concl_item = next((it for it in items if it.op == TKOperator.IMPLY), None)
    if concl_item is None:
        return None
    idx = items.index(concl_item)
    if idx == 0:
        return None
    consequent = concl_item.content
    antecedent = items[idx - 1].content
    # both operands must be UNIVERSAL and SENSE-LESS-subject (bound variable, no class noun) — that is
    # what distinguishes "everything that thinks exists" from an intersective class universal.
    for leaf in (antecedent, consequent):
        if getattr(leaf, "quantifier", None) != TKQuantifier.UNIVERSAL:
            return None
        if (getattr(leaf, "senses", None) or {}).get("subject"):
            return None
    cond_pred = (getattr(antecedent, "senses", None) or {}).get("predicate")
    concl_pred = (getattr(consequent, "senses", None) or {}).get("predicate")
    if not cond_pred or not concl_pred:
        return None
    return {
        "kind": "property_conditioned",
        "cond_pred": cond_pred,
        "cond_obj": (getattr(antecedent, "senses", None) or {}).get("direct"),
        "concl_pred": concl_pred,
        "concl_obj": (getattr(consequent, "senses", None) or {}).get("direct"),
        "concl_negated": bool(getattr(consequent, "negated", False)),
    }


# extract individual FACTS from the active axioms/theorems for the forward-chainer + the individual-
# fact grounder. an individual leaf has an entity-linked subject (identities['subject']) and is NOT
# universal (universals are RULES, not facts). two fact kinds, both returned in ONE list:
#   MEMBERSHIP fact — NOUN predicate ("Mari is a human" => mari@... is_a homo.n.02). carries
#                     `klass_sense` (the chainer keys on this; property facts are ignored by it).
#   PROPERTY  fact  — non-noun predicate (verb/adj) OR a noun predicate WITH an object ("tokeniko
#                     thinks", "I value logic"). grounds an individual-subject clause directly via
#                     evaluator_groundIndividualFact, so a stored self-fact decides its matching
#                     question instead of abstaining.
def extract_facts(docs) -> list:
    facts: list = []
    for doc in docs:
        if doc.zip is None:
            continue
        for leaf in _zip_leaves(doc.zip.items):
            if getattr(leaf, "quantifier", None) == TKQuantifier.UNIVERSAL:
                continue
            identities = getattr(leaf, "identities", None) or {}
            senses = getattr(leaf, "senses", None) or {}
            subject_uid = identities.get("subject")
            predicate = senses.get("predicate")
            if not subject_uid or not predicate:
                continue
            obj = senses.get("direct")
            if ".n." in predicate and obj is None:
                # bare NOUN predication "X is a Y" -> a MEMBERSHIP fact (class membership).
                # klass_mods: the class's restrictive modifiers ("I am a THINKING machine" ->
                # [thinking.n.01]) — the chainer tests a conditioned rule's condition against these
                # (finding #5 / 2c: the fact side compiles the same senses as the rule side).
                # negated carried ("I am NOT a man"): a negated membership must never seed the
                # closure (the chainer skips it) — it instead REFUTES the matching question/claim
                # (evaluator_groundIndividualFact's membership branch).
                facts.append({
                    "subject_uid": subject_uid,
                    "klass_sense": predicate,
                    "klass_mods": _mod_senses(senses, "predicate_mod"),
                    "negated": bool(getattr(leaf, "negated", False)),
                    "original": doc.original,
                    "kind": "membership",
                    "source_id": str(doc.id),  # provenance: the KB doc this fact comes from
                })
            else:
                # verb/adj predicate, OR noun-with-object -> a PROPERTY fact
                facts.append({
                    "subject_uid": subject_uid,
                    "predicate": predicate,
                    "object": obj,
                    "negated": bool(getattr(leaf, "negated", False)),
                    "original": doc.original,
                    "kind": "property",
                    "source_id": str(doc.id),  # provenance: the KB doc this fact comes from
                })
    return facts


# ================================================================================================
# THE FRONT DOOR — extract_logic(docs, source, parents): ONE source-agnostic TKZip → usable-logic
# call (Brain v1.1 step 4). The SOURCE never gates extraction — every source yields every shape it
# structurally contains — it only decides how the caller TIERS the trust:
#   "axiom" / "theorem" — the runtime-mutable sets: consumed IN-MEMORY per KB load
#       (evaluation_harness._load_active_kb), so archiving the source doc retracts its logic on the
#       next load (revocation by construction). edges = generic-taxonomy copulars; rules = universal/
#       generic/negative + property-conditioned; facts = individual membership/property.
#   "definition" — the large design-time set: consumed via the PERSISTED tiers (derived_relations /
#       derived_rules), rebuilt by the operator-gated writer scripts which call THIS function (ruler
#       and writer share one gate). edges = genus spine; rules = differentia (the necessary
#       direction); facts = none (definitions describe classes, not individuals).
# Returns {"edges", "rules", "facts", "stats"} — stats is a Counter merging the per-shape gates'.
# ================================================================================================
def extract_logic(docs, source: str, parents) -> dict:
    stats: Counter = Counter()
    if source in ("axiom", "theorem"):
        edges, edge_stats = extract_generic_isa_edges(docs, parents)
        rules = extract_rules(docs)
        facts = extract_facts(docs)
    elif source == "definition":
        edges, edge_stats = extract_isa_edges(docs, parents)
        rules, rule_stats = extract_differentia_rules(docs, parents)
        for r in rules:
            r.setdefault("kind", "property")  # differentia = the necessary direction
        stats.update({f"differentia_{k}": v for k, v in rule_stats.items()})
        # the SUFFICIENT direction (recognition) rides along: kind="sufficient" rules beside the
        # kind="property" differentia — one biconditional, two directions, one front door.
        suff, suff_stats = extract_sufficient_rules(docs, parents)
        for r in suff:
            rules.append({**r, "kind": "sufficient"})
        stats.update({f"sufficient_{k}": v for k, v in suff_stats.items()})
        facts = []
    else:
        raise ValueError(f"unknown extraction source {source!r}")
    stats.update({f"edge_{k}": v for k, v in edge_stats.items()})
    stats.update({"rules": len(rules), "facts": len(facts)})
    return {"edges": edges, "rules": rules, "facts": facts, "stats": stats}


# ================================================================================================
# DEFINITIONAL SUFFICIENCY (Brain v1.1 step 4 — the recognition direction). A definition is a
# biconditional (X ⟺ genus ∧ definiens); the extractors above mine the NECESSARY direction. This
# mines the SUFFICIENT one: whatever satisfies the WHOLE definiens IS an X —
#     (is_a genus ∧ cond₁ ∧ … ∧ condₙ) → is_a X
# The soundness rule that shapes everything here (asymmetric to the differentia gate):
#   NECESSARY  direction may DROP CONJUNCTS (each conjunct is independently necessary);
#   SUFFICIENT direction may DROP DISJUNCTS (each disjunct is independently sufficient)
#              but NEVER a conjunct — a rule missing one conjunct is WEAKER than the definiens and
#              over-fires ("anything added to something is an addition").
# So the definiens' operator tree is left-folded into DNF branches (leaf op=OR splits, op=AND
# distributes — the compiler's fold semantics); each branch is one candidate rule, and a branch
# containing ANY unrepresentable conjunct (IMPLY purpose clause, pred-less leaf, foreign subject,
# negated cond, noun appositive, object-less verb, circularity) is REJECTED whole. The genus rides
# EVERY branch as a class-condition — it is what defuses the nested-disjunction trap ("transports
# goods → vehicle" is false; "conveyance ∧ transports goods → vehicle" is what the gloss says).
# Gate policy + 0.3 trust settled with the author on the step-4 dry-run (scripts/probe_sufficiency.py,
# which calls THIS extractor — ruler and writer share one gate).
# ================================================================================================
_SUFF_TAINT = "?TAINT?"


# left-fold a TKZipItem tree into DNF branches: a branch is a list of leaf TKZipContent (a
# conjunction); the returned list of branches is their disjunction. Mirrors the evaluator's fold
# semantics (e_statement: truths fold left through each item's op). A non-AND/OR op (IMPLY purpose
# clause) taints every branch it lands in — it is an unrepresentable CONJUNCT, judged by the gate.
def _dnf_branches(item):
    c = item.content
    if isinstance(c, TKZipContent):
        return [[c]]
    acc = None
    for ch in c:
        ch_br = _dnf_branches(ch)
        op = getattr(ch, "op", TKOperator.AND)
        if op not in (TKOperator.AND, TKOperator.OR):
            ch_br = [br + [_SUFF_TAINT] for br in ch_br]
            op = TKOperator.AND
        if acc is None:
            acc = ch_br
        elif op == TKOperator.OR:
            acc = acc + ch_br
        else:  # AND: distribute
            acc = [a + b for a in acc for b in ch_br]
    return acc or []


# the per-branch gate. verdicts (first failure wins, cheapest first): "taint" | "no_pred" |
# "foreign_subj" (leaf about neither X, the genus, nor a bound variable) | "negated_cond" |
# "noun_cond" (appositive / genus-alt) | "verb_noobj" (transitivity unconfirmed) | "circular" |
# "bare" (genus-only: sufficiency would collapse to the FALSE "is_a genus -> is_a X") | "accept".
# On accept returns the deduped, order-preserving cond list [(predicate, object), ...].
def _gate_sufficient_branch(X, genus_sense, genus_leaf, branch):
    if any(lf is _SUFF_TAINT for lf in branch):
        return "taint", None  # judged FIRST: an IMPLY conjunct dooms the branch whatever else it holds
    conds: list = []
    for lf in branch:
        if lf is genus_leaf:
            continue  # the genus conjunct is carried structurally by the rule
        s = getattr(lf, "senses", None) or {}
        subj, pred, obj = s.get("subject"), s.get("predicate"), s.get("direct")
        if not pred:
            return "no_pred", None
        if subj not in (X, genus_sense, None):
            return "foreign_subj", None
        if bool(getattr(lf, "negated", False)):
            return "negated_cond", None
        if pred == genus_sense:
            continue  # a re-statement of the genus, not a new conjunct
        pos = _pos(pred)
        if pos == "n":
            return "noun_cond", None
        if pos == "v" and not obj:
            return "verb_noobj", None
        if _genus_lemma(pred)[:4] and _genus_lemma(pred)[:4] == _genus_lemma(X)[:4]:
            return "circular", None
        if (pred, obj) not in conds:
            conds.append((pred, obj))
    if not conds:
        return "bare", None
    return "accept", conds


# extract the ACCEPTED sufficient rules from the definitions, gated against the bedrock is_a graph.
# Returns (rules, stats):
#   rules = [{klass, genus, conds: [{"predicate","object"}...], source_id, source_original}, ...]
#           (kind=sufficient; caller adds trust/method)
#   stats = Counter {no_genus, genus_only, abstract_genus, candidate_def, candidate_branch,
#                    br_<verdict>..., accept}
def extract_sufficient_rules(definition_docs, parents) -> tuple[list[dict], Counter]:
    is_abstract = _make_is_abstract(parents)
    stats: Counter = Counter()
    rules: list[dict] = []
    seen: set = set()
    for d in definition_docs:
        leaves = _zip_leaves(d.zip.items) if getattr(d, "zip", None) else []
        X = genus_sense = genus_leaf = None
        for lf in leaves:
            s = getattr(lf, "senses", None) or {}
            subj, pred = s.get("subject"), s.get("predicate")
            if subj and pred and ".n." in subj and ".n." in pred and subj != pred:
                X, genus_sense, genus_leaf = subj, pred, lf
                break
        if genus_sense is None:
            stats["no_genus"] += 1
            continue
        if len(leaves) == 1:
            stats["genus_only"] += 1        # "an X is a Y" alone: Y -> X is false
            continue
        if is_abstract(genus_sense):
            stats["abstract_genus"] += 1    # differentia describes the BEARER, not X
            continue
        stats["candidate_def"] += 1
        for br in _dnf_branches(d.zip.items):
            stats["candidate_branch"] += 1
            verdict, conds = _gate_sufficient_branch(X, genus_sense, genus_leaf, br)
            stats[f"br_{verdict}"] += 1
            if verdict != "accept":
                continue
            key = (X, genus_sense, tuple(conds))
            if key in seen:
                continue
            seen.add(key)
            stats["accept"] += 1
            rules.append({
                "klass": X,
                "genus": genus_sense,
                "conds": [{"predicate": p, "object": o} for p, o in conds],
                "source_id": str(d.id),
                "source_original": d.original,
            })
    return rules, stats
