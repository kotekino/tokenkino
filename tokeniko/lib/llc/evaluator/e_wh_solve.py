# ------------------------------------------------------------------------------------------------
# WH-QUESTION VALUE-SOLVER (the genuinely-new piece of the questions work).
#
# A polar question reuses the truth machinery (yes/no). A WH-question ("what is a cat?", "who is
# happy?", "why is the sky blue?") names a GAP ROLE — the variable X to SOLVE FOR — via its wh-word
# (carried on the zip leaf as `wh_role`). Solving = a role-gap KB query: read the non-gap roles of the
# question clause, find KB knowledge that fits, and read the value off the gap role.
#
# DB-agnostic, like the rest of the evaluator: the caller injects the active definitions/axioms/
# theorems + the is_a `parents(sense)` reader (and, for "why", the already-computed assertion result
# whose `derivation` chain IS the answer). Staged by tractability — "what" (is_a hypernym) is solid;
# "who/which" scans KB facts; "why" surfaces the derivation; where/when/how are not yet answerable
# (an honest UNKNOWN). Sense -> readable word is the synset lemma ("feline.n.01" -> "feline").
# ------------------------------------------------------------------------------------------------
from typing import Callable, Optional

from lib.core.tk import TKWhRole
from lib.core.tkzip import TKZip, TKZipContent
from lib.core.evaluation import AnswerResult, AnswerKind, AnswerVerdict, EvaluatorResult

Parents = Callable[[str], list[str]]


# surface a WordNet synset key as a readable word: "feline.n.01" -> "feline"; "domestic_cat" -> "domestic cat".
def _surface(sense: Optional[str]) -> Optional[str]:
    if not sense:
        return None
    return sense.split(".")[0].replace("_", " ")


# collect every leaf TKZipContent of a zip-item tree (local copy — keeps the evaluator independent of
# the harness, which imports the evaluator, not the other way around).
def _leaves(item) -> list[TKZipContent]:
    c = item.content
    if isinstance(c, TKZipContent):
        return [c]
    out: list[TKZipContent] = []
    if isinstance(c, list):
        for child in c:
            out += _leaves(child)
    return out


def _idk(reason: str) -> AnswerResult:
    return AnswerResult(kind=AnswerKind.WH, verdict=AnswerVerdict.UNKNOWN, confidence=0.3, reason=reason)


# solve a WH question. `leaf` is the question clause (the one carrying wh_role). `parents` is the
# injected is_a reader; `axioms`/`theorems` are the active TKZips (for the SUBJECT scan); `assertion`
# is the EvaluatorResult of grounding the same clause as a statement (its derivation answers "why").
def evaluator_solveWh(
    leaf: TKZipContent,
    axioms: list[TKZip],
    theorems: list[TKZip],
    parents: Parents,
    assertion: Optional[EvaluatorResult] = None,
) -> AnswerResult:
    role = getattr(leaf, "wh_role", None)
    senses = getattr(leaf, "senses", None) or {}
    identities = getattr(leaf, "identities", None) or {}

    # "what is X?" -> the gap is the predicate (copular complement): answer with X's is_a hypernym.
    if role == TKWhRole.PREDICATE:
        subj = senses.get("subject")
        if subj:
            hypers = parents(subj)
            if hypers:
                hyper = hypers[0]
                return AnswerResult(
                    kind=AnswerKind.WH, verdict=AnswerVerdict.VALUE, value=_surface(hyper),
                    confidence=0.9, reason=f"is_a: a {_surface(subj)} is a {_surface(hyper)}",
                    derivation=[f"{subj} is_a {hyper}"],
                )
        return _idk("no is_a knowledge for the subject")

    # "who/which is P?" -> the gap is the subject: find a KB clause predicating P, return its subject.
    if role == TKWhRole.SUBJECT:
        pred = senses.get("predicate")
        if pred:
            for zips, kind in ((axioms, "axiom"), (theorems, "theorem")):
                for z in zips:
                    if z is None:
                        continue
                    for kb_leaf in _leaves(z.items):
                        kb_senses = getattr(kb_leaf, "senses", None) or {}
                        kb_ids = getattr(kb_leaf, "identities", None) or {}
                        if kb_senses.get("predicate") != pred:
                            continue
                        subj_word = (kb_ids.get("subject") or "").split("@")[0] or _surface(kb_senses.get("subject"))
                        if subj_word:
                            return AnswerResult(
                                kind=AnswerKind.WH, verdict=AnswerVerdict.VALUE, value=subj_word,
                                confidence=0.7, reason=f"KB {kind}: {subj_word} is {_surface(pred)}",
                            )
        return _idk("no KB fact predicates that of any known subject")

    # "why is X Y?" -> the answer is the premise chain that grounds "X is Y" (if any).
    if role == TKWhRole.CAUSE:
        if assertion is not None and assertion.derivation:
            return AnswerResult(
                kind=AnswerKind.WH, verdict=AnswerVerdict.VALUE, value="; ".join(assertion.derivation),
                confidence=0.7, reason="derivation", derivation=list(assertion.derivation),
            )
        return _idk("no derivation available to explain it")

    # where / when / how — not yet answerable (no structured spatial/temporal/manner KB query). honest.
    return _idk(f"answering a '{role.value if role else '?'}' question is not yet supported")
