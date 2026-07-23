# ------------------------------------------------------------------------------------------------
# EVALUATOR — intra-statement consistency (controllo di contraddizione)
# classifica la FORMA logica dell'input sul suo stesso albero ripiegato (la stessa fold di
# e_statement), senza KB: una self-contradiction (X ∧ ¬X) è falsa sotto OGNI assegnazione e va
# segnalata INCONSISTENT a prescindere da come la si grounda.
#
# come funziona:
#   - le foglie (TKZipContent) vengono raggruppate in "atomi": due foglie sono lo stesso atomo se
#     geometricamente uguali (evaluator_compareContent >= soglia); il segno (+1/-1) tiene conto del
#     flag `negated`, così "alive" e "not alive" finiscono nello stesso atomo con segni opposti.
#   - le foglie `unknown` non si fondono con nulla (vocabolario ignoto: non possiamo assumere identità).
#   - si enumerano le assegnazioni crisp {0,1} sugli atomi e si ripiega la formula con _fold_statement;
#     su input crisp operator_truth si riduce alla logica booleana classica.
# bar contraddizione-only: segnaliamo SOLO le forme insoddisfacibili (maxF <= 0). Le forme
# soddisfacibili (es. IMPLY(x, 1-x)) restano consistenti.
# ------------------------------------------------------------------------------------------------
from dataclasses import dataclass
from itertools import product
from typing import Callable, Optional

from lib.core.tk import TKQuantifier
from lib.core.tkzip import TKZip, TKZipContent
from .e_compare import evaluator_compareContent
from .e_keys import role_key
from .e_statement import _collect_contents, _fold_statement

# due foglie sono lo stesso atomo quando la similarità geometrica clear questa soglia.
_ALIAS_THRESHOLD = 0.90
# oltre questo numero di atomi l'enumerazione 2^k è troppo costosa: si salta il check.
_MAX_ATOMS = 16
# tolleranza numerica per "vero/falso sotto ogni assegnazione".
_EPS = 1e-9


@dataclass
class FormClass:
    contradiction: bool
    tautology: bool
    detail: Optional[str] = None


# il lemma-prefisso di una chiave-synset WSD ("alive.a.01" -> "alive"), o "" se vuota/malformata.
# serve per la detail string contrary-predicate.
def _sense_lemma(sense: Optional[str]) -> str:
    if not sense:
        return ""
    return sense.split(".", 1)[0]


# ------------------------------------------------------------------------------------------------
# THE SQUARE OF OPPOSITION (2026-07-14, the Socratic dialogue — an S0 in the hardwired logic).
# Before this, every quantified opposition read as P∧¬P: «some S are P» + «some S are not P»
# (SUBCONTRARIES — can both be true, and usually ARE the truth together) docked a teacher -0.15,
# twice. A leaf's crisp meaning depends on its QUANTIFIER — Aristotle's corners:
#   A (all S are P) · E (no S is P) · I (some S are P) · O (some S are not P)
# On the SAME atom (same subject+predicate geometry): contradictories (A↔O, E↔I) and contraries
# (A↔E, Aristotelian — KB class atoms are kind-level, non-empty) cannot BOTH hold; subcontraries
# (I↔O) and subalterns (A↔I, E↔O) can. Corner mapping is CONSERVATIVE (never punish a consistent
# reading): a negated universal is ambiguous between E («all S are not P») and O («not every S is
# P» — the negation-scope tangle) → read as the WEAKER O, since INCONSISTENT demands certainty
# under every reading. INDEFINITE («a S is P») is generic-ambiguous → read existentially (I/O).
# DEFINITE/GENERIC leaves stay CRISP: the original boolean-atom behavior (an individual, or a
# kind-level claim, opposed by its own negation is still a genuine contradiction).
# A MODAL leaf (◇-claim) has NO corner: it never enters an atom as an assertion at all.
_CORNER_A, _CORNER_E, _CORNER_I, _CORNER_O = "A", "E", "I", "O"
_CORNER_CRISP, _CORNER_MODAL = "CRISP", "MODAL"
# corner pairs that cannot both hold on the same atom
_SQUARE_MUTEX = {(_CORNER_A, _CORNER_O), (_CORNER_O, _CORNER_A),
                 (_CORNER_E, _CORNER_I), (_CORNER_I, _CORNER_E),
                 (_CORNER_A, _CORNER_E), (_CORNER_E, _CORNER_A)}
# corners strong enough for the antonym contrary-predicate mutex (an existential pair of antonym
# predicates — "some cats are dead and some are alive" — is NOT a contradiction)
_STRONG_CORNERS = {_CORNER_A, _CORNER_E, _CORNER_CRISP}


def _corner(c: TKZipContent) -> str:
    if getattr(c, "modal", None):
        return _CORNER_MODAL
    q = getattr(c, "quantifier", TKQuantifier.GENERIC)
    neg = bool(getattr(c, "negated", False))
    if q == TKQuantifier.UNIVERSAL:
        return _CORNER_O if neg else _CORNER_A     # negated universal -> the weaker O reading
    if q == TKQuantifier.NEGATED_UNIVERSAL:
        # ¬∀ first-class (M6): «not all S are P» = O; «not all S are not-P» = ¬(∀¬) = ∃ = I
        return _CORNER_I if neg else _CORNER_O
    if q == TKQuantifier.NEGATIVE:
        return _CORNER_I if neg else _CORNER_E     # ¬(no S is P) = some S is P
    if q in (TKQuantifier.EXISTENTIAL, TKQuantifier.INDEFINITE):
        return _CORNER_O if neg else _CORNER_I
    return _CORNER_CRISP                           # DEFINITE / GENERIC: the original behavior


# coppie di atomi CONTRARI: due atomi (non-unknown) che predicano l'uno l'antonimo dell'altro sullo
# STESSO soggetto ("X è vivo" / "X è morto"). i contrari non possono valere insieme (1,1) ma possono
# essere entrambi falsi (0,0) — quindi è un vincolo di mutua esclusione, NON P/¬P. guardie conservative:
# stesso senso-soggetto, sensi-predicato distinti, entrambi NON negati (così l'atomo significa pulito
# la predicazione positiva "X è <pred>"), e i due predicati legati da antonimia. senza un reader -> [].
def _contrary_pairs(
    reps: list[TKZipContent],
    reps_unknown: list[bool],
    antonyms: Optional[Callable[[str], list[str]]],
    reps_corner: Optional[list[str]] = None,
) -> list[tuple[int, int]]:
    if antonyms is None:
        return []
    pairs: list[tuple[int, int]] = []
    n = len(reps)
    for i in range(n):
        if reps_unknown[i]:
            continue
        # square-gate: antonym contrariety needs a STRONG claim on both sides — an existential
        # pair of antonym predicates ("some cats are dead and some are alive") is consistent.
        if reps_corner is not None and reps_corner[i] not in _STRONG_CORNERS:
            continue
        for j in range(i + 1, n):
            if reps_unknown[j]:
                continue
            if reps_corner is not None and reps_corner[j] not in _STRONG_CORNERS:
                continue
            rep_i, rep_j = reps[i], reps[j]
            # SUBJECT keyed identity-first (role_key): two individual-subject leaves («I am alive» /
            # «I am dead») compare by uid, not by two None senses that fell through the truthiness
            # guard below and left the contrary pair silently undetected (identity-blindness family).
            # PREDICATE stays a SENSE read — the antonym reader is keyed by synset; an identity
            # predicate has no antonym, so it never forms a contrary pair.
            si = role_key(rep_i, "subject")
            pi = (getattr(rep_i, "senses", None) or {}).get("predicate")
            sj = role_key(rep_j, "subject")
            pj = (getattr(rep_j, "senses", None) or {}).get("predicate")
            # stesso soggetto, predicati distinti
            if not (si and sj and si == sj):
                continue
            if not (pi and pj and pi != pj):
                continue
            # entrambi non negati: evita di mis-modellare predicazioni negate
            if getattr(rep_i, "negated", False) or getattr(rep_j, "negated", False):
                continue
            # legame di antonimia (in una delle due direzioni)
            if pj in antonyms(pi) or pi in antonyms(pj):
                pairs.append((i, j))
    return pairs


# classifica la forma logica di uno statement: è una contraddizione (mai vera) e/o una tautologia
# (sempre vera)? Il controllo è puramente strutturale sul fold dell'input, senza alcuna conoscenza.
# quando `antonyms` è iniettato, aggiunge il check contrary-predicate (sensi-predicato antonimi dello
# stesso soggetto): modellato come vincolo di mutua esclusione (no (1,1)) nell'enumerazione crisp.
# con antonyms=None il comportamento è identico byte-per-byte a prima (additivo).
def evaluator_classifyForm(statement: TKZip, antonyms: Optional[Callable[[str], list[str]]] = None) -> FormClass:
    contents = _collect_contents(statement.items)
    if not contents:
        return FormClass(False, False, None)

    # 1. clustering delle foglie in atomi (greedy, primo match). mapping: id(content) -> (atom, sign).
    mapping: dict[int, tuple[int, int]] = {}
    # foglie PINNATE: identità riflessive (a=a -> 1, a≠a -> 0). costanti hardwired, non atomi liberi.
    constants: dict[int, float] = {}
    reps: list[TKZipContent] = []
    reps_unknown: list[bool] = []
    reps_corner: list[str] = []
    # per ogni atomo, le foglie (indice, segno) che vi mappano — serve per la detail string.
    atom_leaves: list[list[tuple[int, int]]] = []

    for leaf_index, c in enumerate(contents):
        if getattr(c, "reflexive", False):
            # a=a -> 1, a≠a -> 0 (negated flips it). a PINNED constant, not a free atom.
            # reflexive takes precedence over unknown: logical identity holds regardless of vocabulary.
            constants[id(c)] = 0.0 if getattr(c, "negated", False) else 1.0
            continue

        corner = _corner(c)

        if getattr(c, "unknown", False) or corner == _CORNER_MODAL:
            # vocabolario ignoto O ◇-claim: atomo proprio, segno +1, non fonde con nulla.
            # (un modale non è un'asserzione crisp: ◇P non contraddice né ◇¬P né ¬P)
            atom_index = len(reps)
            reps.append(c)
            reps_unknown.append(True)
            reps_corner.append(corner)
            atom_leaves.append([(leaf_index, 1)])
            mapping[id(c)] = (atom_index, 1)
            continue

        matched = False
        for atom_index, rep in enumerate(reps):
            if reps_unknown[atom_index]:
                continue
            # square-of-opposition: una foglia si fonde solo con un atomo dello STESSO corner.
            # CRISP+CRISP mantiene il sign-fold originale (P/¬P); i corner quantificati (A/E/I/O)
            # portano la polarità NEL corner (segno sempre +1) e i conflitti vivono nelle mutex.
            if reps_corner[atom_index] != corner:
                continue
            if evaluator_compareContent(c, rep) >= _ALIAS_THRESHOLD:
                if corner == _CORNER_CRISP:
                    sign = 1 if c.negated == rep.negated else -1
                else:
                    sign = 1
                mapping[id(c)] = (atom_index, sign)
                atom_leaves[atom_index].append((leaf_index, sign))
                matched = True
                break

        if not matched:
            atom_index = len(reps)
            reps.append(c)
            reps_unknown.append(False)
            reps_corner.append(corner)
            atom_leaves.append([(leaf_index, 1)])
            mapping[id(c)] = (atom_index, 1)

    k = len(reps)
    # k==0 free atoms (solo costanti pinnate) deve comunque ripiegare una volta: product(..., repeat=0)
    # rende una sola assegnazione vuota, così uno statement di sole identità riflessive viene classificato.
    if k > _MAX_ATOMS:
        return FormClass(False, False, None)

    # 1c. coppie di atomi CONTRARI (predicati antonimi sullo stesso soggetto): vincolo di mutua
    # esclusione sull'enumerazione — i due atomi non possono valere entrambi 1. square-gated:
    # solo corner FORTI (A/E/CRISP) su entrambi i lati.
    contrary_pairs = _contrary_pairs(reps, reps_unknown, antonyms, reps_corner)

    # 1d. mutex del QUADRATO: atomi quantificati con la stessa geometria (stessa claim affermativa
    # — la negazione è un flag, mai piegata nei vettori) e corner incompatibili (contraddittorî
    # A↔O, E↔I; contrarî A↔E) non possono valere entrambi 1. I subcontrarî (I↔O) e i subalterni
    # restano liberi — la correzione del 2026-07-14.
    square_pairs: list[tuple[int, int]] = []
    for i in range(k):
        if reps_unknown[i] or reps_corner[i] == _CORNER_CRISP:
            continue
        for j in range(i + 1, k):
            if reps_unknown[j] or reps_corner[j] == _CORNER_CRISP:
                continue
            if (reps_corner[i], reps_corner[j]) not in _SQUARE_MUTEX:
                continue
            if evaluator_compareContent(reps[i], reps[j]) >= _ALIAS_THRESHOLD:
                square_pairs.append((i, j))
    mutex_pairs = contrary_pairs + square_pairs

    # 2. enumerazione crisp {0,1} su tutti gli atomi: traccia il massimo e il minimo della formula.
    maxF = float("-inf")
    minF = float("inf")
    for assignment in product((0.0, 1.0), repeat=k):
        # le mutex non possono valere insieme: scarta l'angolo (1,1) di ogni coppia.
        # (0,0) resta ammessa -> una disgiunzione di contrari resta soddisfacibile e NON tautologica.
        if any(assignment[i] >= 1.0 - _EPS and assignment[j] >= 1.0 - _EPS for (i, j) in mutex_pairs):
            continue
        def ground(c, _a=assignment):
            if id(c) in constants:
                return constants[id(c)]
            idx, sign = mapping[id(c)]
            v = _a[idx]
            return v if sign > 0 else 1.0 - v

        t = _fold_statement(statement.items, ground)
        if t > maxF:
            maxF = t
        if t < minF:
            minF = t

    contradiction = maxF <= _EPS
    tautology = minF >= 1.0 - _EPS

    detail: Optional[str] = None
    if contradiction:
        # atomi con polarità mista (sia una foglia +1 che una -1): la coppia P / ¬P che contraddice.
        mixed: list[int] = []
        for atom_index, leaves in enumerate(atom_leaves):
            signs = {sign for _, sign in leaves}
            if 1 in signs and -1 in signs:
                mixed.append(atom_index)
        if mixed:
            idxs = sorted(li for atom_index in mixed for li, _ in atom_leaves[atom_index])
            shown = ", ".join(str(i) for i in idxs)
            detail = (
                f"self-contradiction: clauses {{{shown}}} assert P and ¬P and cannot hold together"
            )
        elif square_pairs:
            i, j = square_pairs[0]
            li = atom_leaves[i][0][0]
            lj = atom_leaves[j][0][0]
            kind = "contraries" if (reps_corner[i], reps_corner[j]) in ((_CORNER_A, _CORNER_E), (_CORNER_E, _CORNER_A)) else "contradictories"
            detail = (
                f"quantifier contradiction (square of opposition): clauses {{{li},{lj}}} are "
                f"{kind} ({reps_corner[i]} vs {reps_corner[j]}) of the same claim and cannot both hold"
            )
        elif contrary_pairs:
            # nessuna polarità mista, ma esistono predicati antonimi dello stesso soggetto: contrarietà.
            i, j = contrary_pairs[0]
            li = atom_leaves[i][0][0]
            lj = atom_leaves[j][0][0]
            lemma_i = _sense_lemma((getattr(reps[i], "senses", None) or {}).get("predicate"))
            lemma_j = _sense_lemma((getattr(reps[j], "senses", None) or {}).get("predicate"))
            detail = (
                f"contrary-predicate contradiction: clauses {{{li},{lj}}} predicate antonyms "
                f"({lemma_i} / {lemma_j}) of the same subject and cannot both hold"
            )
        elif constants:
            detail = (
                "self-contradiction: reflexive identity violated — a thing cannot differ from itself"
            )
        else:
            detail = (
                "self-contradiction: the statement is false under every assignment to its 0/1 clauses"
            )

    return FormClass(contradiction, tautology, detail)
