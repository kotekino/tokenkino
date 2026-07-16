# ------------------------------------------------------------------------------------------------
# PARSER V2: transform a token list into a list of TKStatements (using spacy for the first ingestion)
# ------------------------------------------------------------------------------------------------

from ollama import Client as OllamaClient
import spacy
from spacy import displacy
from spacy.tokens import Span, Token
import spacy_stanza
import numpy as np
from lib.core.tk import EntityPayload, TKAux, TKClause, TKClauseType, TKFullProperty, TKMarker, TKFullEntity, TKDictionary, TKGeneric, TKMetaEntity, TKName, TKNumber, TKOperator, TKPlace, TKPronoun, TKStatement, TKStatements, TKWhRole
import re
from lib.core.models import TKDictionaryDoc, TKPlaceDoc, TKMemoryStakeholdersDoc
from lib.core.places import place_type_sense
from lib.core.mappers import TKPosMapper
from lib.core.tkllc import TKLLC
from lib.llc.constants import _SPACY_MODEL, _SPACY_MAX_SIMILAR_RESULTS, _WSD_FALLBACK_MIN_SIMILARITY, _OPERATORS_BASE_ANCHORS, _OPERATORS_SIMILARITY_THRESHOLD, _GEO_NER_LABELS, _MODAL_POSSIBILITY, _MODAL_NECESSITY
from lib.core.utilities import util_expandContractions, util_removeSpace
from functools import cmp_to_key
import textacy
from word2number import w2n
from lib.core.memory import MEMContext, MEMStakeholder
from lib.llc.anchors import anchor_resolve, anchor_whType

# --- INIZIO PATCH PYTORCH ---
import torch

_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load
# --- FINE PATCH PYTORCH ---

# load spacy model
nlp_stanza = None
nlp = None

# global variables
_context: MEMContext = None
_ollamaClient: OllamaClient = None
_talker: MEMStakeholder = None
_tokeniko: MEMStakeholder = None

# tokens (and their subtrees) to EXCLUDE while gathering subordinates. used ONLY by the
# universal-relcl re-root (parser_parseSentence): when "everything that thinks exists" is mangled by
# stanza, the real main verb "exists" hangs off the relcl as a ccomp; while we rebuild the bare relcl
# condition ("thinks") on the subject we must keep "exists" out of it (it becomes the main predicate
# instead). scoped tightly: filled right before the subject build and cleared immediately after.
_exclude_subordinates: set[int] = set()

def parser_init():
    global nlp_stanza, nlp
    
    if nlp_stanza is None:
        nlp_stanza = spacy_stanza.load_pipeline(
            "en",
            device="mps",                       # silicon gpu acceleration (if available)
            download_method="reuse_resources"   # skip download if already present
        )
        
        # spacy standard
        nlp = spacy.load(_SPACY_MODEL)

# --------------------------------------------------------------
# utils
# --------------------------------------------------------------
# ------------------------------------------------------------------------------------------------
# the wh-POSITION test (R5, the wh-position bug — live specimens 2026-07-12/13). A wh-word marks the
# utterance interrogative ONLY if it attaches to the ROOT clause: "WHEN do you sleep" (when→sleep,
# the root) is a question; "I am happy WHEN I talk" (when→talk, an advcl under the root) is
# subordination, and «a person is wrong WHEN he says false» is a taught rule — both were swallowed
# as TIME questions before this walk. Walk the head chain to the root; crossing ANY embedded-clause
# dependency (advcl/ccomp/xcomp/acl(:relcl)/csubj/parataxis — UD labels, ":"-subtypes normalized)
# means embedded. Note "?" is judged separately (mood), but the GAP ROLE also uses this test: a
# polar "you are happy when you sleep?" is a question about the conditional, not a TIME-gap wh.
# ------------------------------------------------------------------------------------------------
_WH_EMBEDDED_DEPS = {"advcl", "ccomp", "xcomp", "acl", "relcl", "csubj", "parataxis"}

def _parser_whAttachesToRoot(token: Token) -> bool:
    node = token
    # bounded walk — compare INDICES, never Token objects: spaCy mints a fresh wrapper on every
    # `.head` access, so an identity test at the root never terminates (the 43-minute gremlin)
    for _ in range(len(token.doc)):
        if node.dep_.split(":")[0] in _WH_EMBEDDED_DEPS:
            return False
        if node.head.i == node.i:  # the root heads itself
            return True
        node = node.head
    return True


# get operator corresponding to cc
def parser_ccToOperator(token: Token | str) -> TKOperator:
    lemma = token.lemma_.lower() if isinstance(token, Token) else token

    # unified anchor resolver: exact-hit -> nearest-anchor (polarity-guarded) -> default AND
    return anchor_resolve(lemma, "operators")

# is the cc an ADVERSATIVE join ("but"/"however"/…)? Truth-conditionally it is AND (resolved above);
# the defied-expectation nuance rides the clause `contrast` flag instead of the operator tree
# (M1 2026-07-16 — the old NOTIMPLY mapping folded every true "X but Y" to 0).
def parser_ccIsContrast(token: Token | str) -> bool:
    lemma = token.lemma_.lower() if isinstance(token, Token) else token
    return bool(anchor_resolve(lemma, "contrast"))

# the cc's causal role, if any ("so"/"therefore"/… -> "result"): a conclusive join is FACTIVE
# ("A so B" asserts A, B, and the link), so it folds AND with the link on the clause `cause` flag
# (M2 2026-07-16). The "reason" side (because/since) arrives via the subordinate mark path.
def parser_ccCause(token: Token | str) -> str | None:
    lemma = token.lemma_.lower() if isinstance(token, Token) else token
    return anchor_resolve(lemma, "cause")

# --------------------------------------------------------------
# PARSING
# --------------------------------------------------------------
def parser_getRelatedEntity(token: Token, quotes: list[tuple[list[Token], list[Token], Span]] = [], isPredicate = False) -> TKFullEntity:
    
    entity: TKFullEntity = None

    # search operator, otherwise default
    opToken = next((tt for tt in list(token.subtree) if tt.dep_ == "cc" or tt.dep_ == "punct"), None)
    operator: TKOperator = parser_ccToOperator(opToken) if opToken else TKOperator.AND
    contrast: bool = parser_ccIsContrast(opToken) if opToken else False
    cause: str | None = parser_ccCause(opToken) if opToken else None

    # decide if its a conj single word or a sentence
    if isPredicate:
        subtree = [t for t in token.subtree if t != opToken] # remove operator
        forcedSubject: Token = None
        for q in quotes: 
            if token.text in (c.text for c in list(q.content)): 
                forcedSubject = q.speaker[0] if len(q.speaker) > 0 else None
            continue
        sentence = parser_parseSentence(token, subtree, clause_type=TKClause.COORDINATE, subject=forcedSubject)
        entity = TKFullEntity(entity=sentence, dep=token.dep_, aux=None, marker=None, token=None, properties=[], conjuncts=[], op=operator, contrast=contrast, cause=cause) if sentence else None
    else:
        entity = parser_getFullEntity(token, quotes, operator, contrast=contrast, cause=cause)
    
    # no entity found
    return entity

# get properties
def parser_getProperties(tokens: list[Token]) -> list[TKFullProperty]:

    doc_properties: list[TKFullProperty] = []
    property: TKFullProperty

    for t in tokens:
        property = None
        if t.dep_ == "nummod" \
        or t.dep_ == "amod" \
        or t.dep_ == "nmod" \
        or t.dep_ == "advmod" \
        or t.dep_ == "compound" \
        or t.dep_ == "nmod:poss" \
        or t.dep_ == "det":
            property = parser_getFullProperty(t)

        if property: 
            doc_properties.append(property)

            # ----------------------------------------
            # coordinated entities (conjuncts)
            # ----------------------------------------   
            for c in [cc for cc in t.conjuncts if cc.head == t]:
                doc_properties.append(parser_getFullProperty(c))

    return doc_properties

# get full entity as property
def parser_getFullProperty(token: Token) -> TKFullProperty:
    # related tokens to the entity
    conjuncts = list(token.conjuncts)
    children = list(token.children)

    # get wn pos
    pos = TKPosMapper.get_wn_pos(token.pos_)

    # try finding the meaning (in our dictionary)
    doc_properties: list[TKFullProperty] = []

    # get single entity or statement
    tkMeaning = parser_getPropertyMeaning(token, pos)

    # get properties (for each token directly bound to the result)
    doc_properties = parser_getProperties(children)

    # primary entity (from token)
    primaryEntity: TKFullProperty = TKFullProperty(entity=tkMeaning, token=token.text, dep=token.dep_, properties=doc_properties)

    return primaryEntity

# parse a subordinate clause
def parser_parseSubordinate(token: Token, quotes: list[tuple[list[Token], list[Token], Span]] = []) -> TKFullEntity:

    # initialize variables
    childrenTokens = list(token.children)
    tkMarker: TKMarker = None
    result: TKFullEntity = None

    # get indirect marker 
    marker = next((s for s in childrenTokens if s.dep_ == "case" or s.dep_ == "mark"), None)
    if marker is None:
        # stanza parses wh-subordinators ("...WHEN he says false", "...WHERE you live") as advmod,
        # not mark — the storm-sequel flattening: no marker -> dep-label fallback -> ADVCL -> AND.
        # accept an advmod child as the marker ONLY when the anchors recognize it as a subordinate
        # type (semantic catch, no fixed list; content adverbs like "very" resolve OTHER and pass).
        marker = next((s for s in childrenTokens if s.dep_ == "advmod"
                       and anchor_resolve(s.lemma_, "subordinate_types") != TKClauseType.OTHER), None)
    if marker and marker.has_vector: 
        tkMarker = TKMarker(dep=marker.dep_, word=marker.lemma_, vector=marker.vector, parent_dep=token.dep_)

    # update marker
    if marker == None: 
        tkMarker = TKMarker(parent_dep=token.dep_)

    tokenSubtree = [t for t in token.subtree if t != marker]

    forcedSubject: Token = None
    for q in quotes: 
        if token.text in (c.text for c in list(q.content)): 
            forcedSubject = q.speaker[0] if len(q.speaker) > 0 else None
        continue

    tkStatement = parser_parseSentence(token, tokenSubtree, clause_type=TKClause.SUBORDINATE, subject=forcedSubject)
    if tkStatement: result = TKFullEntity(entity=tkStatement, token=None, dep=token.dep_, aux=None, marker=tkMarker, properties=[], conjuncts=[], op=TKOperator.AND)
    
    return result

# search for separate statements in the token list, and parse them recursively
def parser_isStatement(token: Token) -> bool:
    return token.dep_ in ["xcomp", "ccomp", "csubj", "advcl", "acl", "acl:relcl", "parataxis"]

# get from dictionary, names, number, pronouns, generic (fallback) meaning
# resolve a geo-NER proper noun (GPE/LOC/FAC) to a known place with coordinates, else None.
# NB: name lookup is not disambiguated by prominence, so homonyms resolve to whichever the
# places knowledge base returns first (e.g. "Paris" may be Paris, Ontario).
# identity-bridge: a known place is a NAMED INDIVIDUAL — it gets a GLOBAL uid ("japan@place",
# the same individual for every talker) + its `type` column's dictionary centroid as the honest
# SEMANTIC vector (country/city/planet/... — richer than the flat GPE location.n.01, and never
# a noise vector). The uid is the KEY back into the places table, where the dependency map
# (path_admin/path_geo) stays reachable at reasoning time.
def parser_getPlace(token: Token) -> TKPlace | None:
    if token.ent_type_ not in _GEO_NER_LABELS:
        return None
    # place names are stored lowercased in the knowledge base
    doc = TKPlaceDoc.find_one({"name": token.text.lower()}).run()
    if doc is None:
        return None
    place = TKPlace(**doc.model_dump(exclude={"id"}))
    place.uid = f"{place.name}@place"
    place.vector = _parser_placeTypeCentroid(place.type) or []
    return place

# --------------------------------------------------------------
# NAMED-INDIVIDUAL ENTITY-LINKING (Slice 3a)
# a proper noun NER-typed to a known type centroid becomes an entity-linked individual: it gets the
# type centroid as its SEMANTIC vector (meaning=geometry — NEVER a random/noise vector into the
# grounded 2925 space) + a context-scoped IDENTITY uid (identity=symbolic, kept separate). gated by
# NER type + has_vector so OOV gibberish (which spaCy mislabels) never mints an individual.
# --------------------------------------------------------------
# spaCy NER label -> the dictionary type-centroid sense whose 2925 vector becomes the individual's
# semantic vector. unmapped labels are not entity-linked (conservative).
_NER_TYPE_CENTROID = {
    "PERSON": "person.n.01",
    "GPE": "location.n.01",
    "LOC": "location.n.01",
    "FAC": "location.n.01",
    "ORG": "organization.n.01",
    "NORP": "group.n.01",
    "PRODUCT": "artifact.n.01",
    "WORK_OF_ART": "artifact.n.01",
    "EVENT": "event.n.01",
}

# in-memory cache of {sense -> 2925 type centroid}; these lookups repeat across tokens/sentences.
_TYPE_CENTROID_CACHE: dict[str, list[float]] = {}

def _parser_typeCentroid(sense: str) -> list[float] | None:
    if sense in _TYPE_CENTROID_CACHE:
        return _TYPE_CENTROID_CACHE[sense]
    doc = TKDictionaryDoc.find_one({"sense": sense}).run()
    vec = doc.vector if (doc and doc.vector) else None
    if vec is not None:
        _TYPE_CENTROID_CACHE[sense] = vec
    return vec

# a place's `type` column (country/city/planet/... — the places table's closed set) -> its 2925
# semantic centroid. the type->sense selection is the SHARED places-bridge resolver
# (lib/core/places.py — the evaluator's readers use the same one); the vector fetch reuses the
# type-centroid cache above.
def _parser_placeTypeCentroid(place_type: str) -> list[float] | None:
    return _parser_typeCentroid(place_type_sense(place_type))

# is the surface form a REAL word (known to the spaCy lg vectors), not OOV gibberish? the parser
# tokens come from the stanza pipeline, which carries NO word vectors (token.has_vector is always
# False there), so the has_vector gate is checked against the lg `nlp` vocab — where real names
# ("Mari", "Rome") have vectors and gibberish ("Kjadhfhfjdk") does not.
def _parser_hasLgVector(text: str) -> bool:
    lex = nlp.vocab[text]
    return bool(lex.has_vector) and float(lex.vector_norm) > 0.0

# mint an entity-linked individual TKName, or None when the token is not a linkable individual
# (caller falls back to a bare TKName). deterministic + READ-ONLY (no DB writes -> /evaluate stays pure).
def parser_getIndividual(token: Token, talker: MEMStakeholder) -> TKName | None:
    # gate: a known NER type AND a real vector (rejects OOV gibberish spaCy mislabels as GPE/...)
    mapped_sense = _NER_TYPE_CENTROID.get(token.ent_type_)
    if mapped_sense is None or not _parser_hasLgVector(token.text):
        return None

    # the type centroid is the individual's SEMANTIC vector (never fabricate one)
    centroid = _parser_typeCentroid(mapped_sense)
    if centroid is None:
        return None

    # context-scoped identity uid: name@channel:talker_uid
    name_norm = token.lemma_.lower()
    context = f"{talker.channel.value}:{talker.uid}"
    uid = f"{name_norm}@{context}"

    return TKName(name=token.lemma_, ner=token.ent_type_, uid=uid, vector=centroid)

# --------------------------------------------------------------
# KNOWN-INDIVIDUAL RECOGNITION (Brain v1.1 2b, finding #6)
# before asking "is this a NER-blessed NEW individual?" (minting, above), ask "have I already MET
# this one?": a case-insensitive name match against the stakeholders tokeniko knows (participants he
# talks WITH + individuals he was told ABOUT). Fixes the lowercase-known-name no-op ("kotekino is my
# creator" — stanza tags it PROPN but gives no NER type, so the minting gate rightly refuses; yet
# kotekino is not unknown). RECOGNITION ONLY: it can never create an identity (the NER gate still
# guards minting), so OOV gibberish stays unlinkable. On a name known under several identities the
# preference is (1) the individual scoped to THIS talker's context (their own referent), (2) a
# participant (a real interlocutor — global identity), (3) a unique individual from another context;
# genuinely ambiguous -> None (never guess an identity). READ-ONLY (/evaluate stays pure).
# --------------------------------------------------------------
def parser_getKnownIndividual(token: Token, talker: MEMStakeholder) -> TKName | None:
    return _parser_knownIndividualByName((token.lemma_ or token.text or "").strip(), talker)

# the name-string core of the known-individual recognition (shared by the token path above and the
# COMPOUND-NAME assembly in parser_getMeaning — "test-probe-hellen" is looked up as the whole
# assembled string).
def _parser_knownIndividualByName(name: str, talker: MEMStakeholder) -> TKName | None:
    if not name:
        return None
    matches = TKMemoryStakeholdersDoc.find(
        {"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}}).to_list()
    if not matches:
        return None
    context = f"{talker.channel.value}:{talker.uid}"
    doc = next((m for m in matches if m.kind == "individual" and m.contextKey == context), None)
    if doc is None:
        doc = next((m for m in matches if m.kind == "participant"), None)
    if doc is None:
        individuals = [m for m in matches if m.kind == "individual"]
        if len({m.uid for m in individuals}) == 1:
            doc = individuals[0]
    if doc is None:
        return None  # several distinct identities, no way to pick — never guess
    # semantic vector: the stored type centroid, else the NER-type centroid, else PERSON (a
    # participant is a conversation partner). identity: the stakeholder's OWN stable uid.
    centroid = doc.vector or _parser_typeCentroid(
        _NER_TYPE_CENTROID.get(doc.ner_type or "PERSON", "person.n.01"))
    if centroid is None:
        return None
    return TKName(name=doc.name, ner=doc.ner_type or "PERSON", uid=doc.uid, vector=centroid)

# --------------------------------------------------------------
# WORD-SENSE DISAMBIGUATION (Phase 2)
# pick the dictionary sense that best fits the sentence: POS prunes the candidates (done by the
# caller's query), then the sense whose vector is closest to the sentence's context centroid wins;
# near-ties are broken by gloss/Lesk overlap; with no usable context (or a genuine tie) we fall back
# to the most-frequent sense (the first candidate). single-pass: the context centroid is built from
# the OTHER content words' most-frequent senses (no iterative refinement yet).
# --------------------------------------------------------------
_WSD_CONTENT_POS = {"NOUN", "VERB", "ADJ", "ADV", "PROPN"}  # spaCy POS that carry context

# the centroid may override the frequency prior ONLY when it is confident: its top cosine must clear
# this absolute floor AND beat the runner-up of a different sense by this margin. otherwise a weak /
# ambiguous centroid (the "cat is a plant" failure: the sparse explicit vectors confidently mis-rank
# a person-sense over the animal-sense) can never override the most-frequent sense.
_WSD_CENTROID_FLOOR = 0.5      # absolute cosine the centroid winner must clear to be trusted
_WSD_CENTROID_MARGIN = 0.1     # how far it must beat the next-best sense to be trusted

def _wsd_cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    return float(np.dot(a, b) / (na * nb)) if na and nb else 0.0

# WordNet orders a word's senses by frequency, so the most-frequent sense is the one with the
# smallest sense number NN in its synset name ("word.pos.NN"). NB: the stored `sense` is the synset's
# PRIMARY-lemma name, which for a non-dominant lemma is a DIFFERENT word (e.g. "cat" -> the woman
# sense is stored as "guy.n.01"), so NN alone ties guy.n.01 with cat.n.01. We therefore (1) prefer
# candidates whose synset lemma matches the query word, then (2) take the smallest NN. Mongo
# find().to_list() has NO guaranteed order, so we never rely on candidates[0] being the most frequent.
def _wsd_senseNumber(sense: str) -> int:
    # "word.pos.NN" -> NN (large fallback so an unparseable sense never wins the min)
    try:
        return int(sense.rsplit(".", 1)[-1])
    except (ValueError, AttributeError):
        return 1_000_000

def _wsd_mostFrequent(token: Token, candidates: list[TKDictionaryDoc]) -> TKDictionaryDoc:
    lemma = token.lemma_.lower()
    # prefer senses whose synset lemma IS the query word; fall back to all if none match
    own = [c for c in candidates if (c.sense or "").rsplit(".", 2)[0].lower() == lemma]
    pool = own or candidates
    return min(pool, key=lambda c: _wsd_senseNumber(c.sense or ""))

# the MOST-FREQUENT dictionary sense vector for a token, or None. The selection must follow the
# same discipline as _wsd_mostFrequent (own-lemma preferred, smallest sense number): a bare
# find_one has NO order guarantee, and the arbitrary row it returned poisoned every centroid the
# word appeared in (M3 2026-07-16: find_one("whale") returned giant.n.04 — the PERSON vector — so
# in «a whale … a whale …» the other whale token pushed the centroid onto the person senses,
# 0.807 for giant.n.04, and even "fish" then resolved to pisces.n.02, the astrology PERSON).
def _wsd_mostFrequentVector(token: Token) -> np.ndarray | None:
    for p in TKPosMapper.get_wn_pos(token.pos_):
        cands = TKDictionaryDoc.find({"word": token.lemma_, "pos": p}).to_list()
        cands = [c for c in cands if c.vector]
        if cands:
            # a curated preferred row is the word's plain reading — context vectors use it too
            best = next((c for c in cands if getattr(c, "preferred", False)), None) \
                or _wsd_mostFrequent(token, cands)
            return np.asarray(best.vector, dtype=np.float32)
    return None

# per-Doc cache (computed once) of {token.i: most-frequent sense vector} for content tokens
def _wsd_contextVectors(doc) -> dict[int, np.ndarray]:
    cache = doc.user_data.get("_wsd_vecs")
    if cache is None:
        cache = {}
        for t in doc:
            if t.pos_ in _WSD_CONTENT_POS and not t.is_stop and not t.is_punct:
                v = _wsd_mostFrequentVector(t)
                if v is not None:
                    cache[t.i] = v
        doc.user_data["_wsd_vecs"] = cache
    return cache

# the token's COPULAR PARTNER indices — excluded from its WSD context (the circularity guard,
# 2026-07-11 B-item: in «a dog is a reptile» the subject's only context word IS the predicate the
# claim asserts; disambiguating dog by its affinity to reptile ASSUMES the claim true, and the
# sparse vectors ranked dog.n.03 "a fellow" at 0.83 vs the canine's 0.72 — manufacturing agreement
# with the speaker). Excluded BOTH ways (the predicate must not be voted on by the subject either);
# the partner's own modifiers stay — they are independent description, not the claimed identity.
# Covers the UD shape (predicate noun heads a `cop` child; subject is its nsubj) and the spaCy
# shape (both hang off the copula verb as nsubj/attr).
def _wsd_copularPartners(token: Token) -> set[int]:
    out: set[int] = set()
    head = token.head
    # UD: token is the nsubj of a noun that carries a cop child -> the partner is that head noun
    if token.dep_ in ("nsubj", "nsubj:pass") and any(ch.dep_ == "cop" for ch in head.children):
        out.add(head.i)
    # UD: token IS the copular predicate (has a cop child) -> its nsubj children are partners
    if any(ch.dep_ == "cop" for ch in token.children):
        out.update(ch.i for ch in token.children if ch.dep_ in ("nsubj", "nsubj:pass"))
    # spaCy: subject and predicate are siblings under the copula verb (nsubj / attr)
    if token.dep_ in ("nsubj", "attr") and head.pos_ in ("AUX", "VERB"):
        other = "attr" if token.dep_ == "nsubj" else "nsubj"
        out.update(ch.i for ch in head.children if ch.dep_ == other)
    return out


# context centroid = mean of the OTHER content tokens' most-frequent vectors (None if no context);
# the token's copular partner is NOT context (the circularity guard above), and neither is another
# token of the SAME LEMMA (M3: a repeated word is self-evidence, not independent context — it can
# only vote the word toward its own most-frequent sense, drowning the real context).
def _wsd_centroid(token: Token) -> np.ndarray | None:
    vecs = _wsd_contextVectors(token.doc)
    lemma = token.lemma_.lower()
    excluded = _wsd_copularPartners(token) | {token.i}
    excluded |= {t.i for t in token.doc if t.lemma_.lower() == lemma}
    others = [v for i, v in vecs.items() if i not in excluded]
    return np.mean(others, axis=0) if others else None

# Lesk overlap: how many of a gloss's content words appear among the sentence's content lemmas.
# the QUERY TOKEN ITSELF is excluded from the sentence side (2026-07-14, the shiny incident):
# a gloss that merely MENTIONS the query word ("glazed: having a SHINY surface" vs «gold is
# shiny») is self-reference, not context fit — it let the mentioning sense beat the synset that
# IS the word. overlap must measure how the gloss fits the REST of the sentence.
def _wsd_lesk(definition: str, doc, query: Token | None = None) -> int:
    if not definition:
        return 0
    glossWords = {w for w in (t.strip(".,;:()'\"`") for t in definition.lower().split()) if len(w) > 2 and w.isalpha()}
    exclude = {query.lemma_.lower(), query.text.lower()} if query is not None else set()
    ctx = {t.lemma_.lower() for t in doc
           if t.pos_ in _WSD_CONTENT_POS and not t.is_stop} - exclude
    return len(glossWords & ctx)

# choose the best sense among candidates (the dictionary docs for token's lemma+POS, >=1)
def parser_disambiguateSense(token: Token, candidates: list[TKDictionaryDoc]) -> TKDictionaryDoc:
    if len(candidates) == 1:
        return candidates[0]

    # LESK FIRST: overlap of the sense's gloss with the sentence's content words is the most reliable
    # signal on the sparse explicit vectors — a raw centroid cosine can confidently mis-rank (it scores
    # the "gossip" sense of cat ABOVE the animal sense next to "mammal", while the animal gloss is the
    # only one that contains "mammal"). pick the UNIQUE top-overlap sense.
    leskScored = [(_wsd_lesk(c.definition or "", token.doc, query=token), c) for c in candidates]
    maxLesk = max(s for s, _ in leskScored)
    leaders = [c for s, c in leskScored if s == maxLesk]
    if maxLesk > 0 and len(leaders) == 1:
        return leaders[0]

    # CURATED PREFERRED (M3): the crew's ruling on the word's plain reading, consulted AFTER Lesk
    # (real textual evidence still wins) and BEFORE the centroid (curated human data outranks the
    # sparse-vector co-occurrence guess — geometry proposes, curation disposes; the centroid ranked
    # pisces.n.02 the FISH SIGN above the actual fish at 0.755). At most one row per (word,pos).
    curated = next((c for c in candidates if getattr(c, "preferred", False)), None)
    if curated is not None:
        return curated

    # CONFIDENT CENTROID: lean on the context centroid only when it is decisive (rich contexts the
    # gloss overlap misses). Restrict to the tied Lesk leaders when there IS a positive overlap signal,
    # else consider all candidates. A centroid pick overrides the frequency prior ONLY if its cosine
    # clears the absolute floor AND beats the best DIFFERENT-sense runner-up by the margin — so a weak
    # / ambiguous centroid can never override the most-frequent sense.
    centroid = _wsd_centroid(token)
    if centroid is not None:
        pool = leaders if maxLesk > 0 else candidates
        scored = sorted(
            ((_wsd_cosine(np.asarray(c.vector, dtype=np.float32), centroid) if c.vector else -1.0, c) for c in pool),
            key=lambda sc: sc[0], reverse=True,
        )
        topScore, topCand = scored[0]
        runnerUp = next((s for s, c in scored[1:] if (c.sense or "") != (topCand.sense or "")), None)
        if topScore >= _WSD_CENTROID_FLOOR and (runnerUp is None or topScore - runnerUp >= _WSD_CENTROID_MARGIN):
            return topCand

    # FREQUENCY PRIOR (default): no clear Lesk winner and no confident centroid -> the most-frequent
    # sense (smallest sense number, query-word lemma preferred), NOT an arbitrary candidates[0] nor a
    # low-confidence centroid guess. TODO Phase-5: [eval:ambiguous] -> [tokeniko:ask]
    return _wsd_mostFrequent(token, candidates)

def parser_getPropertyMeaning(token: Token, pos: list[str]) -> EntityPayload:

    tkMeaning = None

    # should be in the dictionary (exclude auxiliaries, pronouns)
    doc_result: TKDictionary = None
    if len(pos) > 0 and token.pos_ != "NUM" and token.pos_ != 'PROPN' and token.pos_ != 'PRON':
        # search in dictionary
        for p in pos:           
            doc_result = TKDictionaryDoc.find_one({"word": token.lemma_, "pos": p}).run()
            if doc_result: break
                
        # semantic fallback — only for tokens that actually carry a vector, and only accepting a
        # candidate whose cosine similarity clears _WSD_FALLBACK_MIN_SIMILARITY. an OOV/gibberish
        # token has no real vector (its query vector is all-zeros / unrelated), so force-matching it
        # to the nearest dictionary lemma is a hallucination -> leave doc_result None -> TKGeneric.
        for p in pos:
            if not doc_result:
                newDoc = nlp.tokenizer(token.lemma_)
                if newDoc and len(list(newDoc)) > 0 and newDoc[0].has_vector:
                    query_vector = np.asarray([newDoc[0].vector])
                    most_similar = nlp.vocab.vectors.most_similar(query_vector, n=_SPACY_MAX_SIMILAR_RESULTS)
                    similar_keys = most_similar[0][0]
                    similar_scores = most_similar[2][0]
                    for key, score in zip(similar_keys, similar_scores):
                        if score < _WSD_FALLBACK_MIN_SIMILARITY:
                            continue
                        fallback_lemma = nlp.vocab.strings[key].lower()
                        doc_result = TKDictionaryDoc.find_one({"word": fallback_lemma, "pos": p}).run()
                        if doc_result:
                            break

        # assign result
        if doc_result: tkMeaning = TKDictionary(**doc_result.model_dump(exclude={"id"}))
    else:
        # not in the dictionary [avrns] -> (cconj, pron, propn, intj, num, particle, punctuation, sconj, sym, x)
        if token.pos_ == "PROPN":
            # a geo-NER proper noun (GPE/LOC/FAC) may be a real place: resolve to TKPlace (with
            # its coordinates) from the places knowledge base; otherwise it is a plain name
            tkMeaning = parser_getPlace(token) or parser_getKnownIndividual(token, _talker) or parser_getIndividual(token, _talker) or TKName(name=token.lemma_)
        if token.pos_ == "NUM":
            clean_text = token.text.replace(',', '').strip()
            numValue = 0
            try:
                numValue = float(clean_text)
            except ValueError:
                numValue = float(w2n.word_to_num(clean_text))

            tkMeaning = TKNumber(value=numValue, num_type=token.ent_type_, text=token.lemma_)
        elif token.pos_ == "PRON":
            vector: list[int] = token.vector if token.has_vector else []
            tkMeaning = TKPronoun(lemma=token.lemma_, vector=vector)

    # if still no result, generic (it is used to manage unknown semantics)
    knownPos = pos[0] if len(pos) > 0 else ""
    if not tkMeaning and not doc_result:
        tkMeaning = TKGeneric(token=token.lemma_, pos=knownPos, upos=token.pos_)

    return tkMeaning

# get from dictionary, names, number, pronouns, generic (fallback) meaning
def parser_getMeaning(token: Token, pos: list[str]) -> EntityPayload:

    tkMeaning = None

    # COMPOUND-NAME assembly (cluster D, 2026-07-14): a hyphenated/multi-token name
    # ("test-probe-hellen", "Jean-Pierre") tokenizes into pieces — the head alone misses the
    # known-individual lookup (^hellen$ never matches "test-probe-hellen") and the OOV mint-gate
    # rightly refuses it, so the role compiled mute. try the ASSEMBLED span (leftmost compound
    # descendant -> token, original text) against the known stakeholders FIRST. RECOGNITION ONLY —
    # an exact full-name match against an already-known identity; it can never mint.
    compound_kids = [c for c in token.children if c.dep_ == "compound"]
    if compound_kids:
        start = min([token.i] + [d.i for k in compound_kids for d in k.subtree])
        span_name = token.doc[start: token.i + 1].text.strip()
        known = _parser_knownIndividualByName(span_name, _talker)
        if known:
            return known

    # STATIVE PARTICIPLE (cluster C, 2026-07-14): a copular participle predicate («I am well
    # RESTED») is a STATE, but stanza lemmatizes it to the dynamic verb ("rest" + VERB), so the
    # adjective sense (rested.a.01 "not tired; refreshed") is never even a candidate. When the
    # participle sits under a copula, try the SURFACE form's adjective senses first —
    # existence-gated: no adjective entry in the dictionary, no behavior change.
    if token.pos_ == "VERB" and "Part" in token.morph.get("VerbForm") \
            and any(ch.dep_ == "cop" or (ch.dep_ in ("aux", "aux:pass") and ch.lemma_ == "be")
                    for ch in token.children):
        adjCandidates = TKDictionaryDoc.find(
            {"word": token.text.lower(), "pos": {"$in": ["a", "s"]}}).to_list()
        if adjCandidates:
            chosen = parser_disambiguateSense(token, adjCandidates)
            return TKDictionary(**chosen.model_dump(exclude={"id"}))

    # should be in the dictionary (exclude auxiliaries, pronouns)
    doc_result: TKDictionary = None
    if len(pos) > 0 and token.pos_ != "NUM" and token.pos_ != 'PROPN' and token.pos_ != 'PRON':
        # search in dictionary — gather the candidate senses across ALL the mapped POS buckets and
        # pick by context (WSD), falling back to the most-frequent sense when context can't decide.
        # UNION, not first-bucket-wins (cluster C, 2026-07-14): ADJ maps to BOTH 'a' and 's'
        # (satellites ARE adjectives — the a/s split is a WordNet artifact), and breaking on the
        # first non-empty bucket hid every satellite sense ("shiny": only glazed.a.03 was ever a
        # candidate; glistening.s.01 — the synset whose lemma IS shiny — never entered the pool).
        candidates = []
        for p in pos:
            candidates.extend(TKDictionaryDoc.find({"word": token.lemma_, "pos": p}).to_list())
        if candidates:
            doc_result = parser_disambiguateSense(token, candidates)


        # semantic fallback — only for tokens that actually carry a vector, and only accepting a
        # candidate whose cosine similarity clears _WSD_FALLBACK_MIN_SIMILARITY. an OOV/gibberish
        # token has no real vector (its query vector is all-zeros / unrelated), so force-matching it
        # to the nearest dictionary lemma is a hallucination -> leave doc_result None -> TKGeneric.
        for p in pos:
            if not doc_result:
                newDoc = nlp.tokenizer(token.lemma_)
                if newDoc and len(list(newDoc)) > 0 and newDoc[0].has_vector:
                    query_vector = np.asarray([newDoc[0].vector])
                    most_similar = nlp.vocab.vectors.most_similar(query_vector, n=_SPACY_MAX_SIMILAR_RESULTS)
                    similar_keys = most_similar[0][0]
                    similar_scores = most_similar[2][0]
                    for key, score in zip(similar_keys, similar_scores):
                        if score < _WSD_FALLBACK_MIN_SIMILARITY:
                            continue
                        fallback_lemma = nlp.vocab.strings[key].lower()
                        doc_result = TKDictionaryDoc.find_one({"word": fallback_lemma, "pos": p}).run()
                        if doc_result:
                            break

        # assign result
        if doc_result: tkMeaning = TKDictionary(**doc_result.model_dump(exclude={"id"}))
    else:
        # not in the dictionary [avrns] -> (cconj, pron, propn, intj, num, particle, punctuation, sconj, sym, x)
        if token.pos_ == "PROPN":
            # a geo-NER proper noun (GPE/LOC/FAC) may be a real place: resolve to TKPlace (with
            # its coordinates) from the places knowledge base; otherwise it is a plain name
            tkMeaning = parser_getPlace(token) or parser_getKnownIndividual(token, _talker) or parser_getIndividual(token, _talker) or TKName(name=token.lemma_)
        if token.pos_ == "NUM":
            clean_text = token.text.replace(',', '').strip()
            numValue = 0
            try:
                numValue = float(clean_text)
            except ValueError:
                numValue = float(w2n.word_to_num(clean_text))

            tkMeaning = TKNumber(value=numValue, num_type=token.ent_type_, text=token.lemma_)
        elif token.pos_ == "PRON":
            vector: list[int] = token.vector if token.has_vector else []
            tkMeaning = TKPronoun(lemma=token.lemma_, vector=vector)

    # if still no result, generic (it is used to manage unknown semantics)
    knownPos = pos[0] if len(pos) > 0 else ""
    if not tkMeaning and not doc_result:
        tkMeaning = TKGeneric(token=token.lemma_, pos=knownPos, upos=token.pos_)

    return tkMeaning

# get marker
def parser_getMarker(token: Token) -> TKMarker:
    tkMarker: TKMarker = None
    marker = next((s for s in token.children if s.dep_ == "case" or s.dep_ == "mark"), None)
    if marker and marker.has_vector: 
        tkMarker = TKMarker(dep=marker.dep_, word=marker.lemma_, vector=marker.vector, parent_dep=token.dep_)
    
    # not found, but it is an indirect object, assign "to" as marker
    if tkMarker == None and token.dep_ == "iobj":
        newMarker = nlp.tokenizer("to")
        tkMarker = TKMarker(word="to", dep="mark", vector=newMarker.vector if newMarker.has_vector else [], parent_dep=token.dep_)

    return tkMarker

# clause tense from the finite element: modal will/shall -> future; else the Tense morph of the
# auxiliary if present, else the predicate verb itself. returns "past" | "pres" | "fut" | None.
def parser_getTense(predicateToken: Token, auxToken: Token | None) -> str | None:
    if auxToken is not None and auxToken.lemma_.lower() in ("will", "shall"):
        return "fut"
    source = auxToken if auxToken is not None else predicateToken
    tense = source.morph.get("Tense")
    return tense[0].lower() if tense else None

# get seamntic value from dictionary + properties
def parser_getFullEntity(token: Token, quotes: list[tuple[list[Token], list[Token], Span]] = [], op: TKOperator = TKOperator.AND, isPredicate = False, contrast: bool = False, cause: str | None = None) -> TKFullEntity:

    # related tokens to the entity
    conjuncts = list(token.conjuncts)
    children = list(token.children)

    # get wn pos
    pos = TKPosMapper.get_wn_pos(token.pos_)

    # try finding the meaning (in our dictionary)
    doc_properties: list[TKFullEntity] = []
    tkMarker = None
    tkAux = None

    # get single entity or statement
    tkMarker = parser_getMarker(token)
    tkMeaning = parser_getMeaning(token, pos)

    # an ASSEMBLED multi-token name consumed its compound children — they are pieces of the NAME
    # ("test"/"probe" in "test-probe-hellen"), not restrictive modifiers; keep them out of the
    # properties (and out of the 2925 blend / the subject_mod{i} senses).
    if isinstance(tkMeaning, TKName) and tkMeaning.uid and tkMeaning.name.lower() != (token.lemma_ or "").lower():
        children = [c for c in children if c.dep_ != "compound"]

    # get properties (for each token directly bound to the result)
    doc_properties = parser_getProperties(children)

    # get auxiliary
    aux = next((s for s in children if s.dep_ in ["cop","aux"]), None)
    tense = parser_getTense(token, aux) if isPredicate else None
    # MODALITY (the Socratic-dialogue fix; □ added M4 2026-07-16): a modal among the aux children
    # scopes the whole clause — ◇ ("a software CAN be a mind" asserts possibility, not membership)
    # or □ ("humans MUST be minds" asserts necessity, not bare membership; unflagged it minted
    # is_a fuel as if asserted fact). Closed grammatical class -> EXACT is correct (like the
    # quantifier determiners). Checked over ALL aux children (the modal and the copula coexist:
    # "can be" -> aux "can" + cop "be"; "must not be" -> □ + the negation, i.e. □¬).
    modal_lemma = next((s.lemma_.lower() for s in children
                        if s.dep_ in ("aux", "aux:pass")
                        and s.lemma_.lower() in (_MODAL_POSSIBILITY | _MODAL_NECESSITY)), None)
    modal = (None if modal_lemma is None
             else "possibility" if modal_lemma in _MODAL_POSSIBILITY else "necessity")
    if aux:
        posAux = TKPosMapper.get_wn_pos(aux.pos_)
        dictAux = parser_getMeaning(aux, posAux)
        # parser_getMeaning may return a TKGeneric (the aux lemma isn't in the dictionary and no
        # vector fallback cleared the threshold — e.g. an aux in a malformed embedded clause like
        # "...know how are you"); TKGeneric carries no .vector, so fall back to an empty vector
        # (a valid TKAux, same as the no-aux branch below).
        auxVector = getattr(dictAux, "vector", None) or []
        tkAux = TKAux(lemma=aux.lemma_, vector=auxVector, tense=tense,
                      modal=modal)
    elif tense:
        # no auxiliary, but stash the predicate verb's own tense for the spacetime time axis
        tkAux = TKAux(tense=tense)

    # ----------------------------------------
    # subordinates entities (search)
    # ----------------------------------------
    subordinates: list[TKFullEntity] = []
    for t in children:
        # skip a subordinate the universal-relcl re-root has carved out (the demoted main verb)
        if t.i in _exclude_subordinates: continue
        if parser_isStatement(t):
            subordinate = parser_parseSubordinate(t, quotes)
            if subordinate:
                subordinates.append(subordinate)

    # primary entity (from token)
    primaryEntity: TKFullEntity = TKFullEntity(entity=tkMeaning, dep=token.dep_, op=op, contrast=contrast, cause=cause, token=token.text, aux=tkAux, marker=tkMarker, properties=doc_properties, subordinates=subordinates)

    # ----------------------------------------
    # coordinated entities (conjuncts)
    # ----------------------------------------   
    for c in [cc for cc in conjuncts if cc.head == token]:
        relatedEntity = parser_getRelatedEntity(c, quotes, isPredicate)
        if relatedEntity: primaryEntity.conjuncts.append(relatedEntity)

    return primaryEntity

# indirects complements
def parser_getIndirects(tokens: list[Token], quotes: list[tuple[list[Token], list[Token], Span]] = []) -> list[TKFullEntity]: 

    # initialize result
    indirectFullEntities: list[TKFullEntity] = list()
    usedTokens: list[Token] = list()

    for t in tokens:
        if t in usedTokens: continue

        # reset indirect entity
        indirectEntity = None

        # indirect objects
        if t.dep_ in ["obl", "obl:tmod", "iobj", "obl:agent"]:
            indirectEntity = parser_getFullEntity(t, quotes)

        # if found 
        if indirectEntity: 
            # mark already used
            usedTokens.extend(t.children)
            usedTokens.extend(t.subtree)
            
            # append indirect
            indirectFullEntities.append(indirectEntity)

    return indirectFullEntities

# closed-class universal determiners that make a NOUN root a universally-quantified subject
_REROOT_UNIVERSAL_DETS = {"all", "every", "each"}

# detect the mangled property-restricted universal ("everything that thinks exists") and return
# (concl, relcl) when the EXACT signature holds, else None. tight by design — it must fire ONLY on the
# mangled pattern, never on legit ccomp ("I think that he exists"), non-universal relcl ("the cat that
# sleeps purrs"), or a universal with no relcl ("everything exists").
def parser_rerootUniversalRelcl(root: Token, children: list[Token]) -> tuple[Token, Token] | None:
    # 1) root is a UNIVERSAL subject: an indefinite TOTAL pronoun (everything/everyone/everybody),
    #    OR a noun carrying an all/every/each determiner.
    isTotalPron = "Tot" in root.morph.get("PronType")
    hasUnivDet = any(c.dep_ == "det" and c.lemma_.lower() in _REROOT_UNIVERSAL_DETS for c in children)
    if not (isTotalPron or hasUnivDet):
        return None

    # 2) root has an acl:relcl child (the property restriction, e.g. "thinks")
    relcl = next((c for c in children if c.dep_ == "acl:relcl"), None)
    if relcl is None:
        return None

    # 3) that relcl has a ccomp child (the demoted real main verb, e.g. "exists")
    concl = next((c for c in relcl.children if c.dep_ == "ccomp"), None)
    if concl is None:
        return None

    return concl, relcl

# parse sentence (recurively called))
def parser_parseSentence(root: Token, tokens: list[Token], clause_type: TKClause = TKClause.MAIN, subject: Token = None) -> TKStatement:
    global _talker, _tokeniko

    # rebuild doc for quotations
    subStatement = " ".join([t.text for t in tokens])
    doc = nlp_stanza(subStatement)
    quotes: list[tuple[list[Token], list[Token], Span]] = list(textacy.extract.triples.direct_quotations(doc))

    # all necessary trees
    tokens = list(root.subtree)
    children = list(root.children)

    # ------------------------------------------------------------------------------------------------
    # UNIVERSAL-RELCL RE-ROOT (mangled property-restricted universal)
    # ------------------------------------------------------------------------------------------------
    # stanza MIS-PARSES "everything that thinks exists": it roots on the universal pronoun "everything",
    # makes "thinks" an acl:relcl child of it, and DEMOTES the real main verb "exists" to a ccomp of
    # "thinks". the normal path (root == predicate) would then build a bogus "everything"-predicate leaf
    # + a spurious THAT/ccomp leaf for "exists". we detect that exact (tight) signature and rebuild the
    # CLEAN shape the well-parsed sibling "everyone who lies is dishonest" already gets: the ccomp verb
    # ("exists") becomes the MAIN predicate over the universal subject ("everything"), and the relcl
    # ("thinks") attaches as the subject's acl:relcl condition — WITHOUT dragging in its ccomp child.
    reroot = parser_rerootUniversalRelcl(root, children)
    if reroot is not None:
        # only the ccomp verb is needed here; the relcl is re-gathered as a subject subordinate below
        rerootConcl, _ = reroot

        # main predicate <- the demoted ccomp verb ("exists"), built exactly like a normal root predicate
        tkPredicate = parser_getFullEntity(rerootConcl, quotes, TKOperator.AND, True)

        # subject <- the universal pronoun ("everything"); it auto-gathers the relcl ("thinks") as an
        # acl:relcl subordinate (same as "everyone who lies"), but we exclude the ccomp ("exists") and
        # its subtree so the condition stays the bare relcl verb, not "thinks -> exists".
        global _exclude_subordinates
        _exclude_subordinates = {t.i for t in rerootConcl.subtree}
        try:
            tkSubject = parser_getFullEntity(root, quotes)
        finally:
            _exclude_subordinates = set()

        tkMain = TKStatement()
        tkMain.create_entity(payload=TKMetaEntity(who=_talker, isListening=False, isTalking=True))
        tkMain.create_entity(payload=TKMetaEntity(who=_tokeniko, isListening=True, isTalking=False))
        tkMain.clause_type = clause_type
        # ROOT-mark capture (the storm-sequel fix): a fragment utterance that IS a subordinate
        # («because you think») carries its subordinating "mark" on the root — stash it on the
        # statement so the compiler folds it with the subordinate operator instead of bare AND.
        rootMark = next((t for t in children if t.dep_ == "mark"), None) if clause_type == TKClause.MAIN else None
        if rootMark is not None:
            tkMain.marker = TKMarker(dep=rootMark.dep_, word=rootMark.lemma_,
                                     vector=rootMark.vector if rootMark.has_vector else [],
                                     parent_dep=root.dep_)
        if tkPredicate: tkMain.create_predicate(fullEntity=tkPredicate)
        if tkSubject: tkMain.create_subject(fullEntity=tkSubject)

        # carry interrogative mood the same way the normal path does
        whToken = next((t for t in tokens if "Int" in t.morph.get("PronType")
                    and _parser_whAttachesToRoot(t)), None)
        if whToken is not None or any("?" in t.text for t in tokens):
            tkMain.dubitative = 1.0
            if whToken is not None:
                tkMain.wh_role = anchor_whType(whToken.lemma_)

        return tkMain

    # ------------------------------
    # root is predicate
    # ------------------------------
    # the root is a verb or an adjective, assign (auxiliaries are properties)
    tkPredicate = parser_getFullEntity(root, quotes, TKOperator.AND, True)
    
    # ------------------------------
    # search subject (first csubj, then nsubj)
    # ------------------------------
    tkSubject = None
    subjectToken = next((s for s in children if (s.dep_ == "nsubj" or s.dep_ == "nsubj:pass")), None)
    if subjectToken: tkSubject = parser_getFullEntity(subjectToken, quotes)
    else: 
        subjectToken = next((s for s in children if (s.dep_ == "csubj")), None)
        if subjectToken: tkSubject = parser_parseSubordinate(subjectToken, quotes)

    # ------------------------------
    # search direct
    # ------------------------------
    tkDirect = None
    directToken = next((s for s in children if s.dep_ == "obj"), None)
    if directToken: tkDirect = parser_getFullEntity(directToken, quotes)

    # ------------------------------
    # search indirect (only on root's children)
    # ------------------------------
    indirectEntities = parser_getIndirects(children, quotes)

    # main statement
    tkMain = TKStatement()
 
    # ----------------------------------------
    # always create source and target entities
    # ----------------------------------------
    # manage quotes
    if (subject):
        forceSubjectEntity = parser_getFullEntity(subject, quotes)
        tkMain.create_entity(payload=forceSubjectEntity.entity)
        tkMain.create_entity(payload=TKMetaEntity(who=_talker, isListening=True, isTalking=False))
    else:
        tkMain.create_entity(payload=TKMetaEntity(who=_talker, isListening=False, isTalking=True))
        tkMain.create_entity(payload=TKMetaEntity(who=_tokeniko, isListening=True, isTalking=False))
        
    tkMain.clause_type = clause_type
    # ROOT-mark capture (the storm-sequel fix): a fragment utterance that IS a subordinate
    # («because you think») carries its subordinating "mark" on the root — stash it on the
    # statement so the compiler folds it with the subordinate operator instead of bare AND.
    rootMark = next((t for t in children if t.dep_ == "mark"), None) if clause_type == TKClause.MAIN else None
    if rootMark is not None:
        tkMain.marker = TKMarker(dep=rootMark.dep_, word=rootMark.lemma_,
                                 vector=rootMark.vector if rootMark.has_vector else [],
                                 parent_dep=root.dep_)
    if tkPredicate: tkMain.create_predicate(fullEntity=tkPredicate)
    if subjectToken: tkMain.create_subject(fullEntity=tkSubject)
    if directToken: tkMain.create_direct(fullEntity=tkDirect)
    for it in indirectEntities: tkMain.add_indirect(fullEntity=it)

    # ----------------------------------------
    # interrogative mood (a question is ANSWERED, not asserted). detection is empirically robust:
    # "?" survives as a PUNCT token, and every wh-word carries PronType=Int in its morph (regardless of
    # POS — PRON who/what, ADV how/where/why, DET which). polar = "?" with no wh-word; wh = a wh-word
    # whose lemma maps to the gap role (anchor_whType). carried on the statement -> dubitative + wh_role.
    # NB the "?" test is a SUBSTRING (not ==): stanza glues "??"/"?!"/"!?" into one PUNCT token, so an
    # exact match would miss them (R4a) — a "?" anywhere in a token's text marks the interrogative.
    # ----------------------------------------
    whToken = next((t for t in tokens if "Int" in t.morph.get("PronType")
                    and _parser_whAttachesToRoot(t)), None)
    if whToken is not None or any("?" in t.text for t in tokens):
        tkMain.dubitative = 1.0
        if whToken is not None:
            # VERB-FRAME refinement (2026-07-14, the B-nugget): anchor_whType's what->PREDICATE is
            # the COPULAR frame ("what is a cat?" — the gap is the copular complement). On this
            # path the root is a CONTENT verb (the copular path returns earlier), so "what do you
            # LIKE?" gaps the verb's missing DIRECT object — the KB query must fill like's object,
            # not replace like itself. who/where/when/why/how are frame-independent (unchanged).
            role = anchor_whType(whToken.lemma_)
            if role == TKWhRole.PREDICATE and root.pos_ == "VERB" \
                    and not any(ch.dep_ == "cop" for ch in children):
                role = TKWhRole.DIRECT
            tkMain.wh_role = role

    #return statement
    return tkMain

# core internal recursive function to parse a list of token into a TKStatements
def parser_core(tokens: list[Token]) -> TKStatements: 

    # init statement
    statements = TKStatements()

    # search separate predicates
    roots = [s for s in tokens if s.dep_ == "root"] # number of separate sentences
    
    # check for recursion
    if len(roots) > 1:
        # recurse condition with > 1 sentences (multiple roots)
        # recursive iteration for each predicate 
        for p in roots:
            statements += parser_core(list(p.subtree))

    elif len(roots) == 1:              
        sentence = parser_parseSentence(roots[0], list(roots[0].subtree), clause_type=TKClause.MAIN)
        statements.append(sentence)

    return statements

# --------------------------------------------------------------
# DEGENERATE-PARSE RETRY (2026-07-14, the store→shop single): stanza (AND spaCy-lg) read
# «a coin stores bits of information» as ONE noun phrase — "stores" tagged NOUN-compound, no verb
# anywhere, the whole sentence a single mute NP. The recovery is DO-SUPPORT, a meaning-preserving
# English transform: when a multi-token input parses with NO verb at all, find a plural-surface
# NOUN whose lemma has a dictionary VERB sense, sitting between a nominal and its object (the
# S-V-O signature), rewrite it "does <lemma>" («a coin DOES STORE bits...») and reparse — emphatic
# do forces the verb reading, tense stays present, semantics untouched. Accepted ONLY if the
# retry yields a VERB root; else the original parse stands (honest fragment).
# --------------------------------------------------------------
def _parser_degenerateRetry(doc, text: str):
    if len(doc) < 3 or any(t.pos_ in ("VERB", "AUX") for t in doc):
        return doc
    for t in doc:
        if t.pos_ != "NOUN" or not t.text.lower().endswith("s"):
            continue
        lemma = t.lemma_.lower()
        if lemma == t.text.lower():
            continue  # not an -s inflection of a distinct lemma
        # the S-V-O signature: a nominal BEFORE it and at least one token AFTER it
        if t.i >= len(doc) - 1 or not any(p.pos_ in ("NOUN", "PROPN", "PRON") for p in doc[:t.i]):
            continue
        if TKDictionaryDoc.find_one({"word": lemma, "pos": "v"}).run() is None:
            continue  # the lemma is not a verb tokeniko knows
        rewritten = text[:t.idx] + "does " + lemma + text[t.idx + len(t.text):]
        retry = nlp_stanza(rewritten)
        root = next((r for r in retry if r.dep_ == "root"), None)
        if root is not None and root.pos_ == "VERB":
            return retry
    return doc

# --------------------------------------------------------------
# MAIN entry point to parse an input text
# --------------------------------------------------------------
def parser(tokens: str, talker: MEMStakeholder, tokeniko: MEMStakeholder, context: MEMContext = None, ollamaClient: OllamaClient = None) -> TKStatements:
    global _context, _ollamaClient, _talker, _tokeniko

    # prepare input
    tokens = util_removeSpace(tokens)
    tokens = util_expandContractions(tokens) # stanza tokenizer mis-merges some contractions (e.g. "I'm")

    # assign variables
    _context = context
    _ollamaClient = ollamaClient

    # determine stakeholders
    _talker =talker
    _tokeniko = tokeniko

    # spacy parse (+ the verbless-NP do-support retry, above)
    doc = _parser_degenerateRetry(nlp_stanza(tokens), tokens)

    # get all tokens
    tkStatements: TKStatements = parser_core(list(doc))

    # return statement
    return tkStatements

# --------------------------------------------------------------
# DISPLAY
# --------------------------------------------------------------

# wrap the displacy dep diagram
def parser_diagram(tokens: str) -> str:
    
    # spacy parse
    doc = nlp_stanza(tokens)
    diagram = displacy.render(doc, style = "dep")

    html = '<html><body>' + diagram + '</body></html>'

    return html