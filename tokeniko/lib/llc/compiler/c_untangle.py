# ------------------------------------------------------------------------------------------------
# c_untangle.py — the graph-constrained GENUS untangle (the definitions-as-rules INGESTION gate).
#
# For every copular "X is a ⟨genus⟩" clause, re-resolve the genus to the sense that is consistent with
# the SUBJECT's own place in the is_a graph — killing homophony (organ-the-fish, state-the-country,
# officer-the-cop) at the source, using tokeniko's OWN taxonomy rather than the token shape. Runs at
# COMPILE time (so all ingestion — definitions, axioms, /evaluate — inherits it), mutating the genus
# entity IN PLACE before the zip is built.
#
# CONSERVATIVE by construction: it OVERRIDES only when the current genus sense is NOT an is_a ancestor
# of the subject AND a sense of the same genus WORD is — so it fixes a demonstrable mis-sense yet leaves
# genuine new edges (air→mixture, no consistent candidate) and already-correct genera untouched. An
# override can never land on a worse edge (the target IS, by test, an ancestor of the subject). When it
# swaps the sense it swaps the matching 2925-dim vector too, so the zip's label and geometry stay in sync.
# ------------------------------------------------------------------------------------------------
from lib.core.models import TKRelationDoc, TKDictionaryDoc
from lib.core.tkllc import TKLLCContent
from lib.llc.evaluator.e_relations import relations_subsumes

from .c_state import _entities

# static-graph caches (the is_a graph + dictionary word→senses never change within a process run).
_parents_cache: dict[str, list[str]] = {}
_senses_cache: dict[str, list[str]] = {}
_vector_cache: dict[str, list[float]] = {}


def _parents(sense: str) -> list[str]:
    hit = _parents_cache.get(sense)
    if hit is None:
        hit = [e.object for e in TKRelationDoc.find({"subject": sense, "relation": "is_a"}).to_list()]
        _parents_cache[sense] = hit
    return hit


def _senses_of(word: str) -> list[str]:
    w = (word or "").lower()
    hit = _senses_cache.get(w)
    if hit is None:
        hit = [d.sense for d in TKDictionaryDoc.find({"word": w}).to_list()]
        _senses_cache[w] = hit
    return hit


def _vector_of(sense: str):
    if sense not in _vector_cache:
        doc = TKDictionaryDoc.find_one({"sense": sense}).run()
        _vector_cache[sense] = doc.vector if (doc and doc.vector) else None
    return _vector_cache[sense]


def _sense_num(s: str) -> int:
    try:
        return int(s.rsplit(".", 1)[1])
    except Exception:
        return 99


def _entity_by_ref(ref):
    if ref is None:
        return None
    m = next((e for e in _entities if e.entity.id == ref.id), None)
    return m.entity if m else None


# the untangle decision (pure over the injected graph/dictionary): the graph-consistent genus, or the
# current sense unchanged. noun→noun genus only (the taxonomic spine).
def _resolve_genus(subject_sense: str, genus_token: str, genus_sense: str) -> str:
    if not subject_sense or not genus_sense:
        return genus_sense
    if ".n." not in subject_sense or ".n." not in genus_sense:
        return genus_sense
    cands = list(_senses_of(genus_token))
    if genus_sense not in cands:
        cands.append(genus_sense)
    consistent = [c for c in cands if c != subject_sense and relations_subsumes(c, subject_sense, _parents)]
    if not consistent or genus_sense in consistent:
        return genus_sense              # genuine new edge / off-graph / already-consistent -> keep
    return min(consistent, key=_sense_num)  # override -> the most-frequent graph-consistent sense


def _leaves(items):
    out = []
    for it in items:
        c = it.content
        if isinstance(c, list):
            out += _leaves(c)
        elif c is not None:
            out.append(c)
    return out


# the SUBJECT-side untangle decision (step 5, the chat-zombie antidote for runtime axioms — the
# definitions get exact gloss-pinning instead, scripts/pin_definition_senses.py). Mirror of
# _resolve_genus: override the subject sense ONLY when it is NOT a bedrock descendant of the genus
# AND another sense of the same subject WORD is — so a demonstrable mis-sense snaps to the sense the
# graph already vouches for, while a genuine NEW edge ("a human is a person": no sense of "human"
# descends from person.n.01 in bedrock) is left untouched. Runs AFTER the genus untangle, so it only
# fires on pairs the genus pass could not reconcile. noun→noun only (the taxonomic spine).
def _resolve_subject(subject_token: str, subject_sense: str, genus_sense: str) -> str:
    if not subject_sense or not genus_sense:
        return subject_sense
    if ".n." not in subject_sense or ".n." not in genus_sense:
        return subject_sense
    cands = list(_senses_of(subject_token))
    if subject_sense not in cands:
        cands.append(subject_sense)
    consistent = [c for c in cands
                  if ".n." in c and c != genus_sense and relations_subsumes(genus_sense, c, _parents)]
    if not consistent or subject_sense in consistent:
        return subject_sense            # genuine new edge / off-graph / already-consistent -> keep
    return min(consistent, key=_sense_num)  # override -> the most-frequent graph-consistent sense


# walk the LLC clauses and untangle each copular genus IN PLACE. Returns the number of genera corrected.
def compiler_untangleGenus(items) -> int:
    fixed = 0
    for content in _leaves(items):
        if not isinstance(content, TKLLCContent):
            continue
        subj = _entity_by_ref(content.subject)
        pred = _entity_by_ref(content.predicate)
        if not subj or not pred or not subj.sense or not pred.sense:
            continue
        new = _resolve_genus(subj.sense, pred.token, pred.sense)
        if new == pred.sense:
            continue
        vec = _vector_of(new)
        if not vec:
            continue  # no vector for the target sense -> cannot safely swap; leave it
        pred.sense = new
        pred.semantic_vector = vec  # keep label + geometry in sync (else the zip lies)
        fixed += 1
    return fixed


# walk the LLC clauses and untangle each copular SUBJECT IN PLACE (after the genus pass). A named
# individual's subject is NEVER touched: its sense is the NER type centroid (identity-bridge), not a
# WSD guess — swapping it would corrupt the identity representation. Returns the number corrected.
def compiler_untangleSubject(items) -> int:
    fixed = 0
    for content in _leaves(items):
        if not isinstance(content, TKLLCContent):
            continue
        subj = _entity_by_ref(content.subject)
        pred = _entity_by_ref(content.predicate)
        if not subj or not pred or not subj.sense or not pred.sense:
            continue
        if getattr(subj, "uid", None):
            continue  # entity-linked individual: type-centroid sense, not a WSD pick
        new = _resolve_subject(subj.token, subj.sense, pred.sense)
        if new == subj.sense:
            continue
        vec = _vector_of(new)
        if not vec:
            continue  # no vector for the target sense -> cannot safely swap; leave it
        subj.sense = new
        subj.semantic_vector = vec  # keep label + geometry in sync (else the zip lies)
        fixed += 1
    return fixed
