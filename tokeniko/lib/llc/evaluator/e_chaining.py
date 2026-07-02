# ------------------------------------------------------------------------------------------------
# EVALUATOR — multi-hop forward-chaining engine (priority-2 step c, the capstone)
#
# Given an input statement, derive the consequences for the input's subject(s) by firing universal
# rules to a FIXPOINT, then check the input clause against the derived facts -> corroborated (truth~1)
# or KB-refuted (truth~0, with a derivation chain). Per doctrine, a KB-contradiction is RESOLVED with
# truth~0 + a chain, NEVER INCONSISTENT (INCONSISTENT is reserved for logic/math rule violations).
#
# Two rule kinds (classified by the universal rule's PREDICATE part-of-speech in its synset key):
#   MEMBERSHIP rule (predicate is a NOUN, ".n.")  — "all humans are thinkers": subject is_a* S
#                   ⇒ subject is_a [predicate-sense class]. These GROW the class closure C.
#   PROPERTY  rule (predicate is ".a."/".s."/".v.") — "all carnivores eat meat" / "all humans are
#                   mortal": subject is_a* S ⇒ subject has property (predicate, object, negated).
#
# The engine:
#   1. seed a class closure C from the input subject's sense (+ its is_a ancestors) and, for an
#      individual subject, from the membership FACTS about that uid (+ their ancestors);
#   2. fire MEMBERSHIP rules to a fixpoint (each fired rule adds its predicate class + ancestors to C);
#   3. apply PROPERTY rules whose subject sits in C -> derived properties, each with a derivation chain.
#
# Pure / DB-agnostic: the caller injects rules, facts, and the is_a `parents(sense)` reader.
# ------------------------------------------------------------------------------------------------
from typing import Callable, Optional

from lib.core.tk import TKQuantifier
from lib.core.tkzip import TKZipContent
from .e_relations import relations_isa_ancestors

Parents = Callable[[str], list[str]]

# truth pinned to a KB-derived verdict (mirrors e_statement). off the exact rails is not required, but
# kept at 1.0/0.0 so a chained verdict is decisive past the grounding margin.
_TAXO_TRUE = 1.0
_TAXO_FALSE = 0.0


# the lemma prefix of a WSD synset key ("eat.v.02" -> "eat"), or "" if empty/malformed.
def _synset_lemma(sense: Optional[str]) -> str:
    if not sense:
        return ""
    return sense.split(".", 1)[0]


# is this synset key a NOUN sense (membership-rule predicate)? ".n." in "thinker.n.01".
def _is_noun_sense(sense: Optional[str]) -> bool:
    return bool(sense) and ".n." in sense


# the ids of any TIER (definition-derived, low-trust) is_a edges walked along `path` — the consecutive
# (child, parent) pairs. `edge_source(child, parent)` returns the tier edge's id if that edge is NOT
# bedrock, else None. returns a frozenset (empty when no reader / all-bedrock). This is the refinement
# of the integrity invariant: BEDROCK is_a edges are substrate (never a premise); a TIER edge walked in
# a derivation IS a revocable premise, so a theorem resting on it can be audited + retracted (step 4).
def _tier_premises_on_path(path: list[str], edge_source) -> frozenset:
    if edge_source is None:
        return frozenset()
    ids = set()
    for child, parent in zip(path, path[1:]):
        eid = edge_source(child, parent)
        if eid:
            ids.add(eid)
    return frozenset(ids)


# add `sense` and its is_a ancestors to the closure C, recording provenance for each newly-added
# class. `base_chain` is the human-readable provenance of how `sense` itself entered C (e.g. the seed
# fact, or a membership rule); `base_premises` is the SET of KB-doc ids that entry rests on. closure[c]
# holds the chain; closure_premises[c] holds the premise-id set. `edge_source` (optional) makes the walk
# provenance-aware: a BEDROCK is_a edge adds NO premise (WordNet substrate), but a TIER edge walked to
# reach an ancestor is recorded as a premise (revocable). When edge_source is None the behaviour is the
# original bedrock-only invariant (backward compatible).
def _add_with_ancestors(sense: str, base_chain: str, closure: dict[str, str], parents: Parents,
                        base_premises: frozenset, closure_premises: dict[str, frozenset],
                        edge_source=None) -> bool:
    added = False
    if sense not in closure:
        closure[sense] = base_chain
        closure_premises[sense] = base_premises
        added = True
    for anc, path in relations_isa_ancestors(sense, parents).items():
        if anc not in closure:
            closure[anc] = base_chain + " -> " + " —is_a→ ".join(path)
            closure_premises[anc] = base_premises | _tier_premises_on_path(path, edge_source)
            added = True
    return added


# a rule/fact's source axiom id as a 1-element premise set (empty if it carries none — defensive).
def _premise_of(rule_or_fact: dict) -> frozenset:
    sid = rule_or_fact.get("source_id")
    return frozenset({sid}) if sid else frozenset()


# run the forward-chainer for one subject (a sense and/or an individual uid). returns
# (derived_props, chains) where derived_props is a list of dicts
#   {predicate, object, negated, chain, premises}
# `premises` is the sorted list of KB-doc ids that conclusion rests on (the seed facts' source axioms +
# the rule axioms fired to reach it + any TIER is_a edges walked — bedrock is_a edges are substrate and
# add no premise). `chains` is the list of all property-derivation chains (same as the per-prop chains).
# `edge_source` (optional): sense-pair -> tier-edge id, makes the is_a walk provenance-aware (definition-
# derived edges become revocable premises); None keeps the original bedrock-only behaviour.
def evaluator_forwardChain(
    subject_sense: Optional[str],
    subject_uid: Optional[str],
    rules: list,
    parents: Parents,
    facts: list,
    max_hops: int = 6,
    edge_source=None,
) -> tuple[list[dict], list[str]]:
    # ---- 1. seed the class closure C (sense -> provenance chain; sense -> premise-id set) ----
    closure: dict[str, str] = {}
    closure_premises: dict[str, frozenset] = {}
    if subject_sense:
        # the subject's OWN sense comes from the INPUT clause, not a KB doc -> no premise.
        _add_with_ancestors(subject_sense, subject_sense, closure, parents, frozenset(), closure_premises,
                            edge_source)
    if subject_uid:
        for fact in facts:
            if fact.get("subject_uid") != subject_uid:
                continue
            klass = fact.get("klass_sense")
            if not klass:
                continue
            base = f"{subject_uid} is_a {klass} (fact)"
            # the membership fact rests on its source axiom.
            _add_with_ancestors(klass, base, closure, parents, _premise_of(fact), closure_premises,
                                edge_source)

    # display name for the subject in the chains. NB: NO early-return on an empty closure — an
    # individual (e.g. tokeniko) may have no class membership yet still satisfy a PROPERTY-CONDITIONED
    # rule via its property facts (the cogito: "tokeniko thinks" -> exists), fired in step 4 below.
    subject_name = subject_uid or subject_sense or "?"

    # ---- 2. fixpoint over MEMBERSHIP rules ----
    membership = [r for r in rules if r.get("kind") == "membership"]
    for _ in range(max_hops):
        changed = False
        for r in membership:
            r_subj = r.get("subject")
            r_pred = r.get("predicate")
            if not r_subj or not r_pred:
                continue
            if r_subj in closure and r_pred not in closure:
                base = (
                    closure[r_subj]
                    + f" -> all {r_subj} are {r_pred}"
                    + f" -> {subject_name} is_a {r_pred}"
                )
                # the new class rests on what put r_subj in C PLUS this rule's axiom.
                base_prem = closure_premises[r_subj] | _premise_of(r)
                if _add_with_ancestors(r_pred, base, closure, parents, base_prem, closure_premises,
                                       edge_source):
                    changed = True
        if not changed:
            break  # fixpoint reached

    # ---- 3. apply PROPERTY rules ----
    derived: list[dict] = []
    for r in rules:
        if r.get("kind") != "property":
            continue
        r_subj = r.get("subject")
        r_pred = r.get("predicate")
        if not r_subj or not r_pred or r_subj not in closure:
            continue
        chain = (
            closure[r_subj]
            + f" -> all {r_subj} {r_pred}"
            + f" -> {subject_name} {r_pred}"
        )
        derived.append({
            "predicate": r_pred,
            "object": r.get("object"),
            "negated": bool(r.get("negated", False)),
            "chain": chain,
            "premises": closure_premises[r_subj] | _premise_of(r),
        })

    # ---- 4. fire PROPERTY-CONDITIONED rules ("everything that thinks exists") ----
    # the subject's KNOWN properties = its property FACTS (uid-keyed) + the properties derived in step 3.
    # a property-conditioned rule whose CONDITION the subject satisfies derives its CONCLUSION; iterate
    # to a fixpoint (a derived property can satisfy another rule's condition — the cogito can cascade).
    pc_rules = [r for r in rules if r.get("kind") == "property_conditioned"]
    if pc_rules:
        # (predicate, object) the subject HAS -> (chain explaining why, premise-id set behind it).
        props: dict[tuple, tuple[str, frozenset]] = {}
        if subject_uid:
            for f in facts:
                if (f.get("subject_uid") == subject_uid and f.get("predicate")
                        and not f.get("klass_sense") and not f.get("negated", False)):
                    props[(f["predicate"], f.get("object"))] = (
                        f"{subject_name} {f['predicate']} (fact)", _premise_of(f))
        for d in derived:
            if not d.get("negated", False):
                props[(d["predicate"], d.get("object"))] = (d["chain"], d["premises"])
        for _ in range(max_hops):
            changed = False
            for r in pc_rules:
                cond_p, cond_o = r.get("cond_pred"), r.get("cond_obj")
                concl_p, concl_o = r.get("concl_pred"), r.get("concl_obj")
                if not cond_p or not concl_p or (concl_p, concl_o) in props:
                    continue
                base = next(((b, prem) for (p, o), (b, prem) in props.items()
                             if p == cond_p and (cond_o is None or o is None or o == cond_o)), None)
                if base is None:
                    continue
                base_chain, base_prem = base
                chain = base_chain + f" -> all that {cond_p} {concl_p} -> {subject_name} {concl_p}"
                # the conclusion rests on the condition-property's premises PLUS this rule's axiom.
                concl_prem = base_prem | _premise_of(r)
                derived.append({"predicate": concl_p, "object": concl_o,
                                "negated": bool(r.get("concl_negated", False)),
                                "chain": chain, "premises": concl_prem})
                props[(concl_p, concl_o)] = (chain, concl_prem)
                changed = True
            if not changed:
                break

    # surface premises as a sorted list per conclusion (frozensets are an internal accumulation detail).
    for d in derived:
        d["premises"] = sorted(d.get("premises", frozenset()))

    return derived, [d["chain"] for d in derived]


# the grounding hook (mirrors _ground_relationally in e_statement): decide the input clause via the
# chaining engine. returns (truth, chain, premises) when chaining decides it, else None (fall through).
# `premises` = the KB-doc ids the derivation rests on (provenance). a KB-refutation is a RESOLVED
# truth~0 with a chain — NOT inconsistent.
def evaluator_chainGround(
    content: TKZipContent,
    rules: list,
    parents: Parents,
    facts: list,
    edge_source=None,
) -> Optional[tuple[float, str, list]]:
    senses = getattr(content, "senses", None) or {}
    identities = getattr(content, "identities", None) or {}

    subject_uid = identities.get("subject")
    subject_sense = senses.get("subject")
    if not subject_uid and not subject_sense:
        return None

    pred = senses.get("predicate")
    if not pred:
        return None
    obj = senses.get("direct")
    negated = bool(getattr(content, "negated", False))

    derived, _ = evaluator_forwardChain(subject_sense, subject_uid, rules, parents, facts,
                                        edge_source=edge_source)

    # find a derived property matching the input predicate (object must match, or the rule had none)
    match: Optional[dict] = None
    for d in derived:
        if d["predicate"] != pred:
            continue
        if d["object"] is None or d["object"] == obj:
            match = d
            break

    if match is None:
        return None  # chaining doesn't decide -> fall through

    premises = match.get("premises", [])
    if match["negated"] == negated:
        base = _TAXO_TRUE
        chain = "chain: " + match["chain"]
    else:
        base = _TAXO_FALSE
        chain = "KB-refuted: " + match["chain"] + " | input negates the derived property"

    # quantifier net_flip — mirrors the shared convention so a NEGATIVE quantifier ("no cat eats
    # meat") flips the base verdict. NB: unlike _ground_relationally (whose base verdict is the
    # affirmative graph fact, with `negated` applied as the flip), here `negated` is ALREADY consumed
    # in the corroborate/refute decision above (input.negated vs the derived property's negation), so
    # only the quantifier dimension remains to flip — otherwise the predicate negation double-counts.
    quantifier = getattr(content, "quantifier", TKQuantifier.GENERIC)
    net_flip = (quantifier == TKQuantifier.NEGATIVE)
    truth = (1.0 - base) if net_flip else base
    chain += f" | quantifier={quantifier.value} negated={negated}"
    if net_flip:
        chain += f" -> flipped -> {'true' if truth >= 0.5 else 'false'}"
    return truth, chain, premises


# ground an INDIVIDUAL-subject clause directly against the stored individual PROPERTY facts (no
# rules, no closure). "tokeniko thinks" is a stored property fact; a question "do you think?" resolves
# you -> tokeniko (same uid) and grounds here, deciding it BEFORE the Pillar-2 individual-abstain.
# returns (truth, chain, premises) on a matching property fact, else None (fall through). `premises` =
# the fact's source-axiom id. matching: same subject uid + same predicate sense, and (the fact has no
# object OR the input has no object OR the objects match). corroborate/refute by negation parity
# (mirrors evaluator_chainGround's tail). NB: quantifier net_flip is NOT applied — these are individual
# facts, not universals.
def evaluator_groundIndividualFact(
    content: TKZipContent,
    facts: list,
) -> Optional[tuple[float, str, list]]:
    identities = getattr(content, "identities", None) or {}
    senses = getattr(content, "senses", None) or {}

    subject_uid = identities.get("subject")
    pred = senses.get("predicate")
    if not subject_uid or not pred:
        return None
    obj = senses.get("direct")
    negated = bool(getattr(content, "negated", False))

    match: Optional[dict] = None
    for fact in facts:
        # property facts only: skip membership facts (no "predicate" key / a "klass_sense")
        if "predicate" not in fact or fact.get("klass_sense"):
            continue
        if fact.get("subject_uid") != subject_uid or fact.get("predicate") != pred:
            continue
        f_obj = fact.get("object")
        if f_obj is None or obj is None or f_obj == obj:
            match = fact
            break

    if match is None:
        return None

    fact_negated = bool(match.get("negated", False))
    original = match.get("original", "")
    premises = [match["source_id"]] if match.get("source_id") else []
    if fact_negated == negated:
        return _TAXO_TRUE, "fact: " + original, premises
    return _TAXO_FALSE, "KB-refuted: " + original + " | input negates the fact", premises
