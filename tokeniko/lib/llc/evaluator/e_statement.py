# ------------------------------------------------------------------------------------------------
# EVALUATOR — statement evaluation
# evaluate a whole input (TKZip) against tokeniko's knowledge:
#   1. ground each leaf clause (TKZipContent) against the definitions  -> per-clause truth in [0,1]
#      (no operators: the content is flat, the comparison is purely geometric)
#   2. FOLD those clause truths through the input's operator tree (operator_truth, fuzzy [0,1]) to
#      get the statement's overall truth — e.g. A1 IMPLY (A2 AND A3) -> IMPLY(T1, AND(T2, T3))
#   3. if the input relates clauses, require a known axiom/theorem to cover the relation
#   4. combine -> RESOLVED (grounded + relation known, truth = folded) or INSUFFICIENT (something
#      is missing, truth = 0.5)
# The INCONSISTENT outcome (operator-math rule-violation detection + missing-variable tracking) is
# scaffolded by EvaluatorResult but DEFERRED to the reasoning engine.
# The evaluator stays DB-agnostic: the caller loads and injects definitions / axioms / theorems.
#
# Operator/tree convention (pinned empirically by compiling representative sentences):
#   a sibling list[TKZipItem] folds LEFT-TO-RIGHT — item 0 is the seed (its op is AND in practice),
#   and each later item's op combines the running accumulator with that item's truth
#   (acc = op_i(acc, truth_i)). The operator sits on the CONSEQUENT, so "A IMPLY B" (B at index 1,
#   op=IMPLY) folds IMPLY(T_A, T_B) and differs from "B IMPLY A". THAT is not truth-functional: its
#   complement truth is modulated toward 0.5 by the attitude confidence, then conjoined. NOT is a
#   defensive unary case (observed negation is encoded inside the clause vector, not as a NOT op).
# ------------------------------------------------------------------------------------------------
from typing import Callable, Optional
from lib.core.evaluation import EvaluatorResult, EvaluatorStatus
from lib.core.tk import TKOperator, TKQuantifier
from lib.core.tkzip import TKZip, TKZipContent, TKZipItem
from lib.llc.anchors import anchor_is
from .e_compare import evaluator_compareZip
from .e_relations import relations_disjoint, relations_subsumes, relations_is_part_of
from .e_truth import evaluator_groundContent
from .operators import operator_truth

# a clause is decisively grounded when its truth is far enough from neutral 0.5 (affirmed or denied
# by some definition); within this band it is treated as ungrounded (no definition decides it).
_GROUNDING_MARGIN = 0.15
# an axiom/theorem counts as covering the input's relation when the zip similarity clears this.
_RELATION_MATCH_THRESHOLD = 0.85
# PILLAR 3 (abstain completion): geometry may AFFIRM a claim only when it is a near-exact definition
# match clearing this floor; below it (mid-guess) or for a denied claim, geometry must abstain, never
# refute. "Humble but sure truths over confident guesses."
_GEOM_AFFIRM = 0.85

# a BARE copular identity claim — "X is a Y" with both X and Y plain noun senses and nothing else
# (no direct object, no modifiers/extra roles). Its truth is the is_a graph's to decide; geometry must
# not vote (see the SPINE post-pass). A definitional GLOSS ("X is [a Y with modifiers]") carries extra
# roles, so it is NOT bare and keeps its geometric definition-grounding.
def _is_bare_identity(content) -> bool:
    senses = getattr(content, "senses", None) or {}
    if set(senses.keys()) != {"subject", "predicate"}:
        return False
    subj, pred = senses.get("subject"), senses.get("predicate")
    return bool(subj and pred and ".n." in subj and ".n." in pred and subj != pred)

# P2a/P2c (logic-is-sacred, individual identity): the subject (or any role) of this clause is an
# INDIVIDUAL — it carries a referential identity uid in `identities` (a named individual like "Mari",
# OR a personal pronoun "I"/"you" routed to the talker/tokeniko stakeholder uid). meaning=geometry holds
# for CLASSES, but an individual's properties/identity are CONTINGENT FACTS, never decidable by vector
# proximity: "are you human?" must not be answered by how close the tokeniko-subject vector sits to
# "human". So when an individual-subject clause is NOT otherwise decided (no is_a/part_of/chaining
# verdict, no supporting fact), geometry must abstain.
def _has_individual_subject(content: TKZipContent) -> bool:
    identities = getattr(content, "identities", None) or {}
    return bool(identities.get("subject"))

# P2c: a bare identity claim "X is Y" where BOTH X and Y are individuals with DISTINCT uids. Distinct
# names MAY corefer ("an entity can have multiple names"), so we can neither assert (geometry) nor
# refute it — only ABSTAIN. Same uid (a=a) is left to the reflexive path. Look at the subject vs the
# predicate/direct identity role (the predicate of a copular "X is Y" carries Y's uid).
def _is_distinct_individual_identity(content: TKZipContent) -> bool:
    identities = getattr(content, "identities", None) or {}
    subj = identities.get("subject")
    if not subj:
        return False
    for other_role in ("predicate", "direct"):
        other = identities.get(other_role)
        if other and other != subj:
            return True
    return False

# collect every leaf TKZipContent of an item tree, in order
def _collect_contents(item: TKZipItem) -> list[TKZipContent]:
    content = item.content
    if isinstance(content, TKZipContent):
        return [content]
    result: list[TKZipContent] = []
    if isinstance(content, list):
        for child in content:
            result.extend(_collect_contents(child))
    return result

# truth of one item: its leaf grounding (or the fold of its children), then — for a THAT item —
# pulled toward neutral 0.5 by the attitude confidence ("I know X" keeps more of X's truth than
# "I believe X"). non-THAT items carry no attitude, so they are returned unmodulated.
def _self_truth(item: TKZipItem, ground) -> float:
    content = item.content
    if isinstance(content, TKZipContent):
        t = ground(content)
    else:
        t = _fold_list(content, ground)
    if item.attitude is not None:
        t = 0.5 + (t - 0.5) * item.attitude.confidence
    return t

# fold a sibling list into one truth, left-to-right. item 0 seeds the accumulator (a stray NOT on it
# negates the seed); each later item's op combines acc with its truth. NOT -> "and not" (acc AND ¬t);
# THAT -> conjoin its (already attitude-modulated) complement truth; everything else applies its
# fuzzy truth function directly via operator_truth.
def _fold_list(items: list[TKZipItem], ground) -> float:
    if not items:
        return 0.5
    acc = _self_truth(items[0], ground)
    if items[0].op == TKOperator.NOT:
        acc = 1.0 - acc
    for item in items[1:]:
        t = _self_truth(item, ground)
        if item.op == TKOperator.NOT:
            acc = operator_truth(TKOperator.AND, acc, 1.0 - t)
        elif item.op == TKOperator.THAT:
            acc = operator_truth(TKOperator.AND, acc, t)
        else:
            acc = operator_truth(item.op, acc, t)
    return acc

# fold the whole statement tree (root item) into a single truth in [0,1].
def _fold_statement(root: TKZipItem, ground) -> float:
    content = root.content
    if isinstance(content, TKZipContent):
        return _self_truth(root, ground)
    return _fold_list(content, ground) if isinstance(content, list) else 0.5

# best geometric match of the input against the injected knowledge. returns (score, kind, index)
# with kind in {"axiom","theorem"} and index into that kind's list; (None, None, None) if no
# knowledge was provided. the score is kept even when below threshold so the caller can surface the
# closest known statement.
def _best_match(statement: TKZip, axioms: list[TKZip], theorems: list[TKZip]):
    best: float | None = None
    kind: str | None = None
    index: int | None = None
    for i, axiom in enumerate(axioms):
        score = evaluator_compareZip(statement, axiom)
        if best is None or score > best:
            best, kind, index = score, "axiom", i
    for i, theorem in enumerate(theorems):
        score = evaluator_compareZip(statement, theorem)
        if best is None or score > best:
            best, kind, index = score, "theorem", i
    return best, kind, index

# truth value pinned to a KB-derived taxonomic verdict (subsumed / refuted). kept off the 0/1 rails
# so the fuzzy fold stays well-behaved, but far past _GROUNDING_MARGIN so it is decisive.
_TAXO_TRUE = 1.0
_TAXO_FALSE = 0.0

# is this clause a copular taxonomic predication "X is a Y" that the is_a graph can decide? per the
# STEP-0 recon, in "a cat is a plant" the SUBJECT holds "cat" and the PREDICATE holds the class noun
# ("plant"); both resolve to dictionary senses. require both senses present (and distinct).
def _isa_senses(content: TKZipContent) -> Optional[tuple[str, str]]:
    senses = getattr(content, "senses", None) or {}
    subj = senses.get("subject")
    pred = senses.get("predicate")
    if subj and pred and subj != pred:
        return subj, pred
    return None

# the lemma prefix of a WSD synset key ("part.n.01" -> "part", "have.v.01" -> "have"), or "" if the
# key is empty/malformed. used to match mereological cue lemmas against the resolved sense.
def _synset_lemma(sense: Optional[str]) -> str:
    if not sense:
        return ""
    return sense.split(".", 1)[0]

# is this clause a PART-WHOLE claim the part_of graph can decide? recognize the two patterns pinned
# by STEP-0 recon and return (part_sense, whole_sense) when one fits clearly, else None:
#   (1) "X is (a) part of Y": predicate lemma is a part-noun (_PART_OF_PREDICATES) and the WHOLE Y is
#       the predicate's nmod modifier (surfaced as "predicate_nmod"). part = subject, whole = nmod.
#   (2) "Y has/contains X": predicate lemma is a meronymic verb (_HAS_PART_VERBS). per the recon the
#       SUBJECT is the WHOLE and the DIRECT object is the PART. part = direct, whole = subject.
# conservative: both senses must be present and distinct, else None (fall through).
def _partof_senses(content: TKZipContent) -> Optional[tuple[str, str]]:
    senses = getattr(content, "senses", None) or {}
    subj = senses.get("subject")
    pred_lemma = _synset_lemma(senses.get("predicate"))

    # pattern (1): "X is part of Y" — part-noun predicate + nmod whole
    if anchor_is(pred_lemma, "part_of_predicate"):
        whole = senses.get("predicate_nmod")
        if subj and whole and subj != whole:
            return subj, whole          # (part=subject, whole=nmod)
        return None

    # pattern (2): "Y has/contains X" — meronymic verb, subject=whole, direct=part
    if anchor_is(pred_lemma, "has_part_verb"):
        direct = senses.get("direct")
        if subj and direct and subj != direct:
            return direct, subj          # (part=direct, whole=subject)
    return None

# try to decide a clause via the injected part_of (meronymy) graph. returns (truth, chain) when the
# graph decides it, else None (leave it to is_a / definition-grounding). CONSERVATIVE direction-aware
# antisymmetry:
#   part —part_of*→ whole               -> base TRUE  (the asserted direction holds)
#   whole —part_of*→ part (the REVERSE) -> base FALSE (antisymmetry: the reverse holds, so this is false)
#   neither edge present                -> None       (part_of is sparse; absence is NOT a refutation)
# the base verdict is then combined with the clause's quantifier + predicate negation (same net_flip
# as is_a): net_flip = (quantifier == NEGATIVE) XOR negated.
def _ground_partof(content: TKZipContent,
                   part_of: Callable[[str], list[str]]) -> Optional[tuple[float, str, list]]:
    pair = _partof_senses(content)
    if pair is None:
        return None
    part_sense, whole_sense = pair

    base: Optional[float] = None
    chain: str = ""

    path = relations_is_part_of(part_sense, whole_sense, part_of)
    if path is not None:
        base = _TAXO_TRUE
        chain = "part_of: " + " —part_of→ ".join(path)
    else:
        # antisymmetry: only the REVERSE edge refutes; a missing edge does NOT (sparse graph)
        reverse = relations_is_part_of(whole_sense, part_sense, part_of)
        if reverse is not None:
            base = _TAXO_FALSE
            chain = "antisymmetry: reverse holds " + " —part_of→ ".join(reverse)

    if base is None:
        return None

    quantifier = getattr(content, "quantifier", TKQuantifier.GENERIC)
    negated = bool(getattr(content, "negated", False))
    net_flip = (quantifier == TKQuantifier.NEGATIVE) != negated  # XOR
    truth = (1.0 - base) if net_flip else base
    chain += f" | quantifier={quantifier.value} negated={negated}"
    if net_flip:
        chain += f" -> flipped -> {'true' if truth >= 0.5 else 'false'}"
    return truth, chain, []  # taxonomic verdict: is_a/part_of edges are bedrock, not premises

# try to decide a clause taxonomically via the injected is_a graph. returns (truth, chain) when the
# graph decides it (subject —is_a*→ predicate ⇒ base TRUE; subject ⊥ predicate at the kingdom level
# ⇒ base FALSE), else None (leave it to definition-grounding). `relations` is the parents(sense)
# callable. the base verdict is then combined with the clause's QUANTIFIER and predicate negation:
#   net_flip = (quantifier == NEGATIVE) XOR (negated)
# a NEGATIVE quantifier ("no cat is a plant") or a predicate negation ("a cat is not a plant") flips
# the base verdict; both together cancel. universal/existential/definite/generic do not flip.
def _ground_relationally(content: TKZipContent, relations: Callable[[str], list[str]],
                         senses_of: Optional[Callable[[str], list[str]]] = None) -> Optional[tuple[float, str, list]]:
    pair = _isa_senses(content)
    if pair is None:
        return None
    subject_sense, object_sense = pair

    base: Optional[float] = None
    chain: str = ""

    # subsumption: subject is_a* object  -> base TRUE
    path = relations_subsumes(object_sense, subject_sense, relations)
    if path is not None:
        base = _TAXO_TRUE
        chain = "subsumed: " + " —is_a→ ".join(path)

    # CHARITABLE cross-product (WSD-canonicalization): the WSD-chosen senses may be wrong (subject
    # "tiger" -> tiger.n.01 "a fierce person" not the animal; predicate "bird" -> the food sense), yet
    # ANOTHER sense of the same lemma genuinely subsumes. try every (subject-sense, object-sense) pair
    # over the lemmas' dictionary senses; the FIRST real is_a path wins. CONSERVATIVE: this only
    # UPGRADES to TRUE on a real taxonomic path — it never refutes and never fabricates (no path -> we
    # fall through to disjointness on the originally-chosen senses, unchanged).
    if base is None and senses_of is not None:
        subj_senses = (senses_of(subject_sense) or [subject_sense])[:12]
        obj_senses = (senses_of(object_sense) or [object_sense])[:12]
        for ss in subj_senses:
            for os_ in obj_senses:
                if ss == subject_sense and os_ == object_sense:
                    continue  # already tried exactly above
                p = relations_subsumes(os_, ss, relations)
                if p is not None:
                    base = _TAXO_TRUE
                    chain = (f"subsumed (WSD-canonicalized {subject_sense}->{ss}, "
                             f"{object_sense}->{os_}): " + " —is_a→ ".join(p))
                    break
            if base is not None:
                break

    if base is None:
        # conservative kingdom-level disjointness: subject ⊥ object  -> base FALSE
        witness = relations_disjoint(subject_sense, object_sense, relations)
        if witness is not None:
            base = _TAXO_FALSE
            chain = "refuted: " + " | ".join(witness)

    if base is None:
        return None

    # combine the base verdict with the quantifier + predicate negation (single net flip).
    quantifier = getattr(content, "quantifier", TKQuantifier.GENERIC)
    negated = bool(getattr(content, "negated", False))
    net_flip = (quantifier == TKQuantifier.NEGATIVE) != negated  # XOR
    truth = (1.0 - base) if net_flip else base
    chain += f" | quantifier={quantifier.value} negated={negated}"
    if net_flip:
        chain += f" -> flipped -> {'true' if truth >= 0.5 else 'false'}"
    return truth, chain, []  # taxonomic verdict: is_a/part_of edges are bedrock, not premises


# evaluate an input statement. definitions are the grounding set (TKZipContent each); axioms and
# theorems are the relational knowledge (TKZip each). `relations`, when given, is a parents(sense)
# callable over the is_a graph (taxonomic grounding/refutation); `part_of`, when given, is the
# analogous wholes(sense) callable over the part_of (meronymy) graph (part-whole grounding). the two
# readers are kept SEPARATE — is_a and part_of carry different semantics. `antonyms`, when given, is
# an antonyms(sense) reader that feeds the intra-statement contrary-predicate check (two clauses
# predicating antonym senses of the same subject -> INCONSISTENT). `rules`/`facts`, when given, feed
# the forward-chaining grounder (e_chaining): universal MEMBERSHIP rules grow the subject's is_a class
# closure to a fixpoint and PROPERTY rules then derive properties, so a verb/adj-predicate clause that
# the is_a copular grounder skips is corroborated (truth~1) or KB-refuted from the rules. A KB-refutation
# is a RESOLVED truth~0 with a derivation chain — NOT INCONSISTENT (that is reserved for logic violations).
# returns an EvaluatorResult.
def evaluator_evaluateStatement(
    statement: TKZip,
    definitions: list[TKZipContent],
    axioms: list[TKZip] | None = None,
    theorems: list[TKZip] | None = None,
    relations: Callable[[str], list[str]] | None = None,
    part_of: Callable[[str], list[str]] | None = None,
    antonyms: Callable[[str], list[str]] | None = None,
    rules: list | None = None,
    facts: list | None = None,
    senses_of: Callable[[str], list[str]] | None = None,
    edge_source: Callable[[str, str], str | None] | None = None,
) -> EvaluatorResult:
    axioms = axioms or []
    theorems = theorems or []

    # 0. intra-statement consistency: a self-contradiction (X ∧ ¬X) is INCONSISTENT regardless of
    # what grounds it — checked on the input's own folded form (crisp atom enumeration), no KB.
    # imported function-locally to avoid an import cycle (e_consistency imports the fold helpers here).
    from .e_consistency import evaluator_classifyForm
    form = evaluator_classifyForm(statement, antonyms=antonyms)
    if form.contradiction:
        return EvaluatorResult(
            truth=0.0, status=EvaluatorStatus.INCONSISTENT, inconsistency=form.detail,
        )

    # 1. ground each leaf clause against the definitions
    contents = _collect_contents(statement.items)
    groundings = [evaluator_groundContent(c, definitions) for c in contents]

    # 1b. RELATIONAL grounding — when a relations graph is injected, override the per-clause grounding
    # for any clause the graph decides. a clause is EITHER taxonomic (is_a) OR mereological (part_of),
    # never both, so we try is_a first and only fall to part_of when is_a does not decide it (don't
    # double-decide). is_a: subsumption -> ~1, kingdom-disjoint -> ~0. part_of: part-of-whole -> ~1,
    # reverse-edge antisymmetry -> ~0 (a MISSING part_of edge is NOT a refutation — sparse graph).
    # the verdict is recorded as a premise chain in `derivation` and the overridden index is tracked so
    # it counts as grounded (not "ungrounded") and a single such clause needs no axiom/theorem match.
    derivation: list[str] = []
    graph_decided: set[int] = set()
    premises_acc: set[str] = set()  # PROVENANCE: the KB-doc ids the graph-decided verdicts rest on
    if relations is not None or part_of is not None or rules or facts:
        for i, c in enumerate(contents):
            # a clause is EITHER a part-whole claim OR a taxonomic one — never both. recognize the
            # part-whole pattern FIRST (its predicate is a part-noun "part of" or a meronymic verb
            # "has/contains") and route it to part_of ONLY: otherwise the is_a copular path would
            # mis-read "X is part of Y" as "X is_a part" and spuriously refute it (part.n.01 is an
            # abstraction, X is physical -> false). a non-part clause falls through to is_a.
            verdict = None
            is_partwhole = _partof_senses(c) is not None
            if is_partwhole and part_of is not None:
                verdict = _ground_partof(c, part_of)
            elif not is_partwhole and relations is not None:
                verdict = _ground_relationally(c, relations, senses_of)
            # forward-chaining grounder: a verb/adj-predicate clause (not is_a copular) falls through
            # the relational grounder; the chainer fires universal rules over the subject's is_a
            # closure (membership rules grow it; property rules derive properties) and corroborates
            # (truth~1) or KB-refutes (truth~0, RESOLVED — NOT inconsistent) the input clause.
            if verdict is None and rules:
                from .e_chaining import evaluator_chainGround
                verdict = evaluator_chainGround(c, rules, relations, facts or [], edge_source=edge_source)
            # individual-fact grounder: a clause about an INDIVIDUAL subject (identities['subject'])
            # is decided directly by the stored individual PROPERTY facts ("tokeniko thinks" grounds
            # a "do you think?" once you->tokeniko corefer) — BEFORE the Pillar-2 individual-abstain,
            # so a known self-fact decides instead of abstaining. self-gates on identities['subject'].
            if verdict is None:
                from .e_chaining import evaluator_groundIndividualFact
                verdict = evaluator_groundIndividualFact(c, facts or [])
            if verdict is not None:
                truth, chain, prem = verdict
                groundings[i] = truth
                graph_decided.add(i)
                derivation.append(chain)
                premises_acc.update(prem)  # provenance: KB-doc ids this clause's verdict rests on

    # SPINE (logic-is-sacred): a BARE copular identity "X is Y" gets its truth ONLY from the is_a graph.
    # If the graph did not decide it (no subsumption -> TRUE, no tiered-disjointness -> FALSE), geometry
    # must NOT assert it — abstain (0.5 -> INSUFFICIENT). "a cat is a dog" is logically agnostic absent
    # KB knowledge; distinctness is LEARNED (KB + wondering), never asserted by vector proximity.
    for i, c in enumerate(contents):
        if i not in graph_decided and _is_bare_identity(c):
            groundings[i] = 0.5

    # SPINE — individual identity (P2a/P2c, logic-is-sacred). An INDIVIDUAL's properties/identity are
    # contingent FACTS, never decidable by geometry. If a clause about an individual subject was NOT
    # decided by the graph/forward-chainer (no supporting is_a/part_of/property/membership fact) it must
    # abstain (0.5 -> INSUFFICIENT) rather than let bare-predicate geometry vote:
    #   P2a — "are you human?" / "am I alive?": subject is the talker/tokeniko stakeholder (uid-only,
    #         sense-less) -> abstain absent a self-fact.
    #   P2c — "Mari is Luca": two individuals with DISTINCT uids -> MAY corefer, cannot refute, only abstain.
    # Same-uid identity (a=a) is reflexive and is NOT touched here.
    for i, c in enumerate(contents):
        if i in graph_decided:
            continue
        if _has_individual_subject(c) or _is_distinct_individual_identity(c):
            groundings[i] = 0.5

    # PILLAR 3 (abstain completion, logic-is-sacred): the general case of the same principle — geometry
    # may only AFFIRM a near-exact definition match, never REFUTE or mid-guess a property/relational
    # claim it cannot prove. A clause the graph/chainer did NOT decide keeps its geometric grounding ONLY
    # if it is an AFFIRMATIVE, confident match (>= _GEOM_AFFIRM); a denied clause (geometry can't affirm a
    # negation from affirmative definitions) or a mid/low score → abstain (0.5 -> INSUFFICIENT). So
    # "a tiger eats meat" (WSD missed the animal sense → low geometry) abstains instead of being
    # confidently refuted (it WAS eval:false→speakup); a gloss restatement (near-exact) still grounds.
    for i, c in enumerate(contents):
        if i in graph_decided:
            continue
        if getattr(c, "negated", False) or groundings[i] < _GEOM_AFFIRM:
            groundings[i] = 0.5

    # 2. fold the clause truths through the operator tree -> the statement's overall truth.
    # map each leaf content (by identity) to its grounding; the fold walks the same objects.
    truth_by_id = {id(c): g for c, g in zip(contents, groundings)}
    folded = _fold_statement(statement.items, lambda c: truth_by_id.get(id(c), 0.5))

    missing: list[str] = []
    # clauses whose core arguments are unknown vocabulary (generic, no dictionary sense): a distinct,
    # actionable INSUFFICIENT reason — tokeniko doesn't know the word(s), the seam for an ask-and-learn.
    # a graph-decided clause is grounded by the is_a graph, so it is not "unknown" here.
    unknown = sum(1 for i, c in enumerate(contents)
                  if i not in graph_decided and getattr(c, "unknown", False))
    if unknown:
        missing.append(f"{unknown} clause(s) reference unknown vocabulary")
    # clauses that are known but no definition decides them (truth sits in the neutral band) — a
    # graph-decided clause is grounded by the is_a graph, so it is excluded from this count.
    ungrounded = sum(1 for i, (c, g) in enumerate(zip(contents, groundings))
                     if i not in graph_decided and not getattr(c, "unknown", False)
                     and abs(g - 0.5) < _GROUNDING_MARGIN)
    if ungrounded:
        missing.append(f"{ungrounded} clause(s) not grounded by any definition")

    # 3. relational match — always computed (to surface the closest known statement), but only
    # REQUIRED when the input actually relates clauses (>1 clause) AND none of those clauses was
    # decided by the is_a graph (a graph-decided taxonomic clause is its own relational evidence).
    relationMatch, matchedKind, matchedIndex = _best_match(statement, axioms, theorems)
    if (len(contents) > 1 and not graph_decided
            and (relationMatch is None or relationMatch < _RELATION_MATCH_THRESHOLD)):
        missing.append("no matching axiom/theorem covers the relation")

    # 4. combine
    if missing:
        return EvaluatorResult(
            truth=0.5, status=EvaluatorStatus.INSUFFICIENT, groundings=groundings, missing=missing,
            relationMatch=relationMatch, matchedKind=matchedKind, matchedIndex=matchedIndex,
            derivation=derivation, premises=sorted(premises_acc),
        )

    # RESOLVED — clauses grounded (by definitions and/or the is_a graph) and (if relational) a known
    # statement covers the relation. truth = the clause truths folded through the operator tree.
    return EvaluatorResult(
        truth=folded, status=EvaluatorStatus.RESOLVED, groundings=groundings,
        relationMatch=relationMatch, matchedKind=matchedKind, matchedIndex=matchedIndex,
        derivation=derivation, premises=sorted(premises_acc),
    )
