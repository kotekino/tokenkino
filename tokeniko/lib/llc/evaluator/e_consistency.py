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
from typing import Optional

from lib.core.tkzip import TKZip, TKZipContent
from .e_compare import evaluator_compareContent
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


# classifica la forma logica di uno statement: è una contraddizione (mai vera) e/o una tautologia
# (sempre vera)? Il controllo è puramente strutturale sul fold dell'input, senza alcuna conoscenza.
def evaluator_classifyForm(statement: TKZip) -> FormClass:
    contents = _collect_contents(statement.items)
    if not contents:
        return FormClass(False, False, None)

    # 1. clustering delle foglie in atomi (greedy, primo match). mapping: id(content) -> (atom, sign).
    mapping: dict[int, tuple[int, int]] = {}
    # foglie PINNATE: identità riflessive (a=a -> 1, a≠a -> 0). costanti hardwired, non atomi liberi.
    constants: dict[int, float] = {}
    reps: list[TKZipContent] = []
    reps_unknown: list[bool] = []
    # per ogni atomo, le foglie (indice, segno) che vi mappano — serve per la detail string.
    atom_leaves: list[list[tuple[int, int]]] = []

    for leaf_index, c in enumerate(contents):
        if getattr(c, "reflexive", False):
            # a=a -> 1, a≠a -> 0 (negated flips it). a PINNED constant, not a free atom.
            # reflexive takes precedence over unknown: logical identity holds regardless of vocabulary.
            constants[id(c)] = 0.0 if getattr(c, "negated", False) else 1.0
            continue

        if getattr(c, "unknown", False):
            # vocabolario ignoto: atomo proprio, segno +1, non fonde con nulla (skippato nel match).
            atom_index = len(reps)
            reps.append(c)
            reps_unknown.append(True)
            atom_leaves.append([(leaf_index, 1)])
            mapping[id(c)] = (atom_index, 1)
            continue

        matched = False
        for atom_index, rep in enumerate(reps):
            if reps_unknown[atom_index]:
                continue
            if evaluator_compareContent(c, rep) >= _ALIAS_THRESHOLD:
                sign = 1 if c.negated == rep.negated else -1
                mapping[id(c)] = (atom_index, sign)
                atom_leaves[atom_index].append((leaf_index, sign))
                matched = True
                break

        if not matched:
            atom_index = len(reps)
            reps.append(c)
            reps_unknown.append(False)
            atom_leaves.append([(leaf_index, 1)])
            mapping[id(c)] = (atom_index, 1)

    k = len(reps)
    # k==0 free atoms (solo costanti pinnate) deve comunque ripiegare una volta: product(..., repeat=0)
    # rende una sola assegnazione vuota, così uno statement di sole identità riflessive viene classificato.
    if k > _MAX_ATOMS:
        return FormClass(False, False, None)

    # 2. enumerazione crisp {0,1} su tutti gli atomi: traccia il massimo e il minimo della formula.
    maxF = float("-inf")
    minF = float("inf")
    for assignment in product((0.0, 1.0), repeat=k):
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
        elif constants:
            detail = (
                "self-contradiction: reflexive identity violated — a thing cannot differ from itself"
            )
        else:
            detail = (
                "self-contradiction: the statement is false under every assignment to its 0/1 clauses"
            )

    return FormClass(contradiction, tautology, detail)
