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
from .e_keys import role_key

Parents = Callable[[str], list[str]]


# surface a WordNet synset key as a readable word: "feline.n.01" -> "feline"; "domestic_cat" -> "domestic cat".
def _surface(sense: Optional[str]) -> Optional[str]:
    if not sense:
        return None
    return sense.split(".")[0].replace("_", " ")


# the KB-FACTS BRANCH for an INDIVIDUAL (the identity-blindness cure, failure mode 2 = source-
# blindness): the WordNet is_a graph has no synset for a named individual, so "what/who is
# <individual>?" is answered from a copular is_a FACT keyed by the uid instead. scan axioms then
# theorems for a leaf whose SUBJECT is this uid and whose predicate is a NOMINAL sense (".n." — a
# class membership; an adjective/verb predicate is not a "what is it" answer); skip negated facts
# («I am not a fish» does not answer «what are you»). returns (class_surface, kind) or None.
def _isa_fact_for(subj_id: str, axioms: list, theorems: list):
    for zips, kind in ((axioms, "axiom"), (theorems, "theorem")):
        for z in zips:
            if z is None:
                continue
            for kb_leaf in _leaves(z.items):
                if role_key(kb_leaf, "subject") != subj_id:
                    continue
                if getattr(kb_leaf, "negated", False):
                    continue
                pred = (getattr(kb_leaf, "senses", None) or {}).get("predicate")
                if pred and ".n." in pred:
                    return _surface(pred), kind
    return None


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
    place_parent=None,
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
        # IDENTITY subject («what are you?» — "you"/"I" is a uid, sense-less): the is_a graph is
        # silent on individuals (sense-only-by-design), so answer from the KB-facts branch — a
        # copular fact keyed by the subject's uid («I am a software» -> "software"). the uid is
        # NEVER fed to `parents`. (identity-blindness family: both failure modes at once, the live
        # «what are you?»×4 specimen of 2026-07-18.)
        subj_id = identities.get("subject")
        if subj_id:
            hit = _isa_fact_for(subj_id, axioms, theorems)
            if hit:
                klass, kind = hit
                return AnswerResult(
                    kind=AnswerKind.WH, verdict=AnswerVerdict.VALUE, value=klass, confidence=0.7,
                    reason=f"KB {kind}: {subj_id.split('@')[0]} is a {klass}",
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
        # IDENTITY target («who is Mari?» — the named individual is carried as a uid, sense-less;
        # role_key makes it matchable where the sense-only predicate read missed it). the parser
        # leaves the individual on the SUBJECT role while marking the gap SUBJECT, so read the uid
        # from either role, then DESCRIBE it from KB facts about that uid (the same is_a-fact lookup
        # as the what-branch). (identity-blindness family: the who-branch bounce, notes §.)
        target_id = identities.get("predicate") or identities.get("subject")
        if target_id:
            hit = _isa_fact_for(target_id, axioms, theorems)
            if hit:
                klass, kind = hit
                return AnswerResult(
                    kind=AnswerKind.WH, verdict=AnswerVerdict.VALUE, value=klass, confidence=0.7,
                    reason=f"KB {kind}: {target_id.split('@')[0]} is a {klass}",
                )
        return _idk("no KB fact predicates that of any known subject")

    # "what do you LIKE?" -> the gap is the verb's DIRECT object (the verb-frame refinement of
    # what->predicate): find a KB clause with the SAME subject + predicate and read its direct.
    if role == TKWhRole.DIRECT:
        subj_id = identities.get("subject")
        subj_sense = senses.get("subject")
        pred = senses.get("predicate") or ""
        pred_lemma = pred.split(".")[0]
        if (subj_id or subj_sense) and pred_lemma:
            for zips, kind in ((axioms, "axiom"), (theorems, "theorem")):
                for z in zips:
                    if z is None:
                        continue
                    for kb_leaf in _leaves(z.items):
                        kb_senses = getattr(kb_leaf, "senses", None) or {}
                        kb_ids = getattr(kb_leaf, "identities", None) or {}
                        same_subject = (subj_id and kb_ids.get("subject") == subj_id) or \
                                       (subj_sense and kb_senses.get("subject") == subj_sense)
                        if not same_subject:
                            continue
                        kb_pred = kb_senses.get("predicate") or ""
                        if kb_pred != pred and kb_pred.split(".")[0] != pred_lemma:
                            continue
                        value = (kb_ids.get("direct") or "").split("@")[0] or _surface(kb_senses.get("direct"))
                        if value:
                            return AnswerResult(
                                kind=AnswerKind.WH, verdict=AnswerVerdict.VALUE, value=value,
                                confidence=0.7,
                                reason=f"KB {kind}: the stored fact's object is '{value}'",
                            )
        return _idk("no KB fact fills that object")

    # "why is X Y?" -> the answer is the premise chain that grounds "X is Y" (if any).
    if role == TKWhRole.CAUSE:
        if assertion is not None and assertion.derivation:
            return AnswerResult(
                kind=AnswerKind.WH, verdict=AnswerVerdict.VALUE, value="; ".join(assertion.derivation),
                confidence=0.7, reason="derivation", derivation=list(assertion.derivation),
            )
        return _idk("no derivation available to explain it")

    # "where is/does X …?" -> the gap is a LOCATION. two sources, in order:
    #   (1) the subject is itself a known place ("where is Rome?") -> its immediate container from
    #       the places table (admin preferred: the human answer is "Lazio", not "Eurasia").
    #   (2) a KB fact about the same subject + predicate that carries a place identity in a non-gap
    #       role ("where do you live?" <- the stored «you live in Japan») -> that place's name.
    if role == TKWhRole.LOCATION:
        subj_id = identities.get("subject")
        if subj_id and subj_id.endswith("@place") and place_parent is not None:
            parent = place_parent(subj_id)
            if parent:
                name, chain = parent
                return AnswerResult(
                    kind=AnswerKind.WH, verdict=AnswerVerdict.VALUE, value=name,
                    confidence=0.9, reason=f"places: {subj_id.split('@')[0]} is in {name} ({chain})",
                )
        pred = senses.get("predicate")
        pred_lemma = (pred or "").split(".")[0]
        if subj_id and pred_lemma:
            for zips, kind in ((axioms, "axiom"), (theorems, "theorem")):
                for z in zips:
                    if z is None:
                        continue
                    for kb_leaf in _leaves(z.items):
                        kb_senses = getattr(kb_leaf, "senses", None) or {}
                        kb_ids = getattr(kb_leaf, "identities", None) or {}
                        if kb_ids.get("subject") != subj_id:
                            continue
                        kb_pred = kb_senses.get("predicate") or ""
                        if kb_pred != pred and kb_pred.split(".")[0] != pred_lemma:
                            continue
                        place = next((u for r, u in kb_ids.items()
                                      if r != "subject" and (u or "").endswith("@place")), None)
                        if place:
                            value = place.split("@")[0]
                            return AnswerResult(
                                kind=AnswerKind.WH, verdict=AnswerVerdict.VALUE, value=value,
                                confidence=0.7,
                                reason=f"KB {kind}: the stored fact carries the place '{value}'",
                            )
        return _idk("no spatial knowledge for that subject/predicate")

    # when / how — not yet answerable (no structured temporal/manner KB query). honest.
    return _idk(f"answering a '{role.value if role else '?'}' question is not yet supported")
