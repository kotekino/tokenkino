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
from typing import Optional

from lib.core.constants import _ME_UID
from lib.core.models import TKAxiomDoc, TKDefinitionDoc, TKDictionaryDoc, TKRelationDoc, TKDerivedRelationDoc, TKTheoremDoc
from lib.core.tk import TKOperator, TKQuantifier
from lib.core.tkzip import TKZip, TKZipContent, TKZipItem
from lib.core.evaluation import AnswerKind, AnswerResult, AnswerVerdict, EvaluatorResult, EvaluatorStatus
from lib.llc.evaluator import evaluator_classifyForm, evaluator_evaluateStatement, evaluator_solveWh, evaluator_forwardChain


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
# is_a edges, definitions-as-rules step 3), so definitions finally fuel grounding + chaining — without
# ever polluting bedrock (the tier is a physically separate, revocable collection). Only `_load_active_kb`
# wires this into the evaluator/chainer; the gate + untangle deliberately keep the bedrock-only reader.
def _make_relations_reader_union():
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
        cache[sense] = objs
        return objs

    return parents


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


# collect every leaf TKZipContent of a zip item tree, in order.
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
def _class_word(sense: str) -> str:
    if not sense:
        return ""
    docs = TKDictionaryDoc.find({"sense": sense}).to_list()
    words = [d.word for d in docs if getattr(d, "word", None)]
    if not words:
        return _sense_surface(sense)
    word_set = set(words)
    # drop a plural "-s" form when its singular sibling is also a candidate
    singulars = [w for w in words if not (w.endswith("s") and w[:-1] in word_set)]
    candidates = singulars or words
    # prefer the longest -> "human" over "homo"
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
        leaves.append((subject, senses.get("predicate"), senses.get("direct"),
                       bool(getattr(leaf, "negated", False))))
    return tuple(sorted(leaves, key=lambda t: tuple(x or "" for x in t)))


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


# extract universal RULES from the active axioms for the forward-chainer. a rule leaf is a
# UNIVERSAL-quantified clause with a subject sense and a predicate sense ("all carnivores eat
# meat", "all humans are thinkers"). the predicate POS classifies the rule: a NOUN predicate
# (".n.") is a MEMBERSHIP rule (subject is_a* S => subject is_a [predicate class]); anything else
# (".a."/".s."/".v.") is a PROPERTY rule (subject is_a* S => subject has the predicate property).
def _extract_rules(axiom_docs) -> list:
    rules: list = []
    for doc in axiom_docs:
        if doc.zip is None:
            continue
        for leaf in _zip_leaves(doc.zip.items):
            if getattr(leaf, "quantifier", None) != TKQuantifier.UNIVERSAL:
                continue
            senses = getattr(leaf, "senses", None) or {}
            subject = senses.get("subject")
            predicate = senses.get("predicate")
            if not subject or not predicate:
                continue
            kind = "membership" if ".n." in predicate else "property"
            rules.append({
                "subject": subject,
                "predicate": predicate,
                "object": senses.get("direct"),
                "negated": bool(getattr(leaf, "negated", False)),
                "kind": kind,
                "original": doc.original,
                "source_id": str(doc.id),  # provenance: the KB axiom this rule comes from
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


# extract individual FACTS from the active axioms for the forward-chainer + the individual-fact
# grounder. an individual leaf has an entity-linked subject (identities['subject']) and is NOT
# universal (universals are RULES, not facts). two fact kinds, both returned in ONE list:
#   MEMBERSHIP fact — NOUN predicate ("Mari is a human" => mari@... is_a homo.n.02). carries
#                     `klass_sense` (the chainer keys on this; property facts are ignored by it).
#   PROPERTY  fact  — non-noun predicate (verb/adj) OR a noun predicate WITH an object ("tokeniko
#                     thinks", "I value logic"). grounds an individual-subject clause directly via
#                     evaluator_groundIndividualFact, so a stored self-fact decides its matching
#                     question instead of abstaining.
def _extract_facts(axiom_docs) -> list:
    facts: list = []
    for doc in axiom_docs:
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
                # bare NOUN predication "X is a Y" -> a MEMBERSHIP fact (class membership)
                facts.append({
                    "subject_uid": subject_uid,
                    "klass_sense": predicate,
                    "original": doc.original,
                    "kind": "membership",
                    "source_id": str(doc.id),  # provenance: the KB axiom this fact comes from
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
                    "source_id": str(doc.id),  # provenance: the KB axiom this fact comes from
                })
    return facts


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
    kb = {
        "definition_docs": definition_docs,
        "axiom_docs": axiom_docs,
        "theorem_docs": theorem_docs,
        "definitions": definitions,
        "axiom_zips": [a.zip for a in axiom_docs],
        "theorem_zips": [t.zip for t in theorem_docs],
        "relations": _make_relations_reader_union(),  # evaluator/chainer see bedrock ∪ derived tier
        "part_of": _make_partof_reader(),
        "antonyms": _make_antonym_reader(),
        "senses_of": _make_senses_reader(),
        "rules": _extract_rules(axiom_docs),
        "facts": _extract_facts(axiom_docs),
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

def kb_wonder(kb: Optional[dict] = None) -> list[dict]:
    kb = kb or _load_active_kb()
    rules, facts, parents = kb["rules"], kb["facts"], kb["relations"]

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

    out: list[dict] = []
    seen_conclusions: set = set()
    for subject, uid, sense, kind in seeds:
        derived, _ = evaluator_forwardChain(sense, uid, rules, parents, facts)
        for d in derived:
            premises = d.get("premises", [])
            if len(premises) < _NOVELTY_MIN_PREMISES:
                continue  # novelty gate: a single-rule restatement is not a new theorem
            sig = (subject, d["predicate"], d.get("object"), bool(d.get("negated", False)))
            if sig in seen_conclusions:
                continue  # semantic dedup across seeds
            seen_conclusions.add(sig)
            out.append({
                "subject": subject,
                "subject_kind": kind,
                "predicate": d["predicate"],
                "object": d.get("object"),
                "negated": bool(d.get("negated", False)),
                "chain": d["chain"],
                "premises": premises,
            })
    return out


def evaluate_zip(statement: TKZip) -> dict:
    kb = _load_active_kb()
    axiom_docs, theorem_docs = kb["axiom_docs"], kb["theorem_docs"]
    result = evaluator_evaluateStatement(
        statement, kb["definitions"], kb["axiom_zips"], kb["theorem_zips"],
        relations=kb["relations"], part_of=kb["part_of"], antonyms=kb["antonyms"],
        senses_of=kb["senses_of"],
        rules=kb["rules"], facts=kb["facts"],
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
        rules=kb["rules"], facts=kb["facts"],
    )

    if wh_leaf is None:
        answer = _polar_answer(result)
    else:
        answer = evaluator_solveWh(wh_leaf, kb["axiom_zips"], kb["theorem_zips"], kb["relations"], assertion=result)

    return {"answer": answer, "result": result}
