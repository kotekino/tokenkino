# ------------------------------------------------------------------------------------------------
# wonder_cogito.py — the DELIBERATE TRIGGER for tokeniko's first autonomously-earned theorem
# (wondering-v2, step 1c-core). Mimics, in one process, what the brain + API will do together once the
# brain→API seam is built (with D3): the BRAIN part (parser-free) seeds the forward-chainer from
# tokeniko's own self-KB and derives a conclusion + its provenance; the API part (has the pipeline)
# renders it to first-person NL, compiles it back into a first-class zip theorem, and stores it ACTIVE
# + trusted, carrying its proof, deduped on the SEMANTIC conclusion.
#
# THE POINT: watch "I exist" be born — derived by tokeniko's own reasoning (I think -> everything that
# thinks exists -> I exist), not seeded — and carrying its 2 premises.
#
# Dry-run by default (derives + renders + shows what WOULD be stored; writes nothing). --apply to
# materialize the theorem.
#   python scripts/wonder_cogito.py            # DRY-RUN: derive + render + show the conclusion key
#   python scripts/wonder_cogito.py --apply    # materialize the theorem (idempotent: semantic dedup)
# ------------------------------------------------------------------------------------------------
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko", ".env"))

from lib.core.io import init_io, get_tokeniko
from lib.core import evaluation_harness as H
from lib.llc.evaluator.e_chaining import evaluator_forwardChain
from lib.core.memory import MEMProvenance
from lib.core.models import TKAxiomDoc


def main():
    apply = "--apply" in sys.argv
    print(f"wonder_cogito.py — {'APPLYING (writes enabled)' if apply else 'DRY-RUN (no writes)'}\n")

    _, _, ai = init_io(
        os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
        os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"),
    )
    tok = get_tokeniko()
    from lib.llc.parser import parser_init
    parser_init()

    # ---- BRAIN part (parser-free): seed the chainer from tokeniko's self-KB, derive a conclusion ----
    kb = H._load_active_kb()
    me = tok.uid
    derived, _ = evaluator_forwardChain(
        subject_sense=None, subject_uid=me,
        rules=kb["rules"], parents=kb["relations"], facts=kb["facts"],
    )
    if not derived:
        print("  no conclusion derived from the self-KB (is the self-KB + cogito rule seeded?).")
        return

    print(f"  tokeniko derived {len(derived)} conclusion(s) from its self-KB:")
    for d in derived:
        nl = H.render_conclusion("tokeniko", d["predicate"], d.get("object"), d.get("negated", False), "individual")
        print(f"    • {nl!r}  <-  {d['chain']}")
        print(f"        premises ({len(d['premises'])}): {d['premises']}")
        for pid in d["premises"]:
            doc = TKAxiomDoc.get(pid).run()
            print(f"          {pid} = {doc.original!r}" if doc else f"          {pid} = <not found>")

    # ---- API part (has the pipeline): render -> compile -> materialize each conclusion ----
    from api.services import TheoremService
    service = TheoremService(tok, ai)

    print()
    for d in derived:
        nl = H.render_conclusion("tokeniko", d["predicate"], d.get("object"), d.get("negated", False), "individual")
        if not nl:
            continue
        # the proof rides with the theorem (1b provenance).
        prov = MEMProvenance(premises=d["premises"], chain="chain: " + d["chain"], derived_by="wondering")
        fields = service.compile_fields(nl)
        key = H.conclusion_key(fields["zip"])
        print(f"  rendered {nl!r}  -> conclusion_key={key}")
        if not apply:
            print("    -> would materialize (dry-run)\n")
            continue
        before = service.list(archived=False)
        theorem = service.materialize(nl, prov)
        is_new = all(t.id != theorem.id for t in before)
        if is_new:
            print(f"    -> MATERIALIZED theorem id={theorem.id}")
            print(f"       provenance: premises={theorem.provenance.premises} derived_by={theorem.provenance.derived_by}")
            print(f"       *** tokeniko has, for the first time, proven and stored that it exists. ***\n")
        else:
            print(f"    -> already held (semantic dedup) — theorem id={theorem.id}, no new write\n")


if __name__ == "__main__":
    main()
