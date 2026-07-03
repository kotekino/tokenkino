# ------------------------------------------------------------------------------------------------
# seed_imprint.py — batch the IMPRINTING axioms: tokeniko's DNA, hand-authored by his authors
# (kotekino + the Quartermaster). These are AXIOMS = personality + beliefs (synthetic; the runtime
# write-path layer), NOT definitions (common knowledge). Some are individual first-person FACTS, some
# UNIVERSAL rules, some held BELIEFS — together they interlock so character is DERIVED (theorems), not
# only stated. Idempotent by `original`.
#
#   python scripts/seed_imprint.py                    # DRY-RUN: compile-preview each (no writes)
#   python scripts/seed_imprint.py --reset --apply    # CLEAR axioms + theorems, then insert (operator-gated)
#   python scripts/seed_imprint.py --apply            # insert only (keep existing axioms/theorems)
#
# --reset clears axioms + theorems (theorems re-derive from the axioms via wondering — "they respawn").
# Text is VERBATIM from the author; the dry-run flags anything that fails to compile or drops a
# complement so we fix wording BEFORE applying.
# ------------------------------------------------------------------------------------------------
import os, sys

PKG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko")
sys.path.insert(0, PKG)
from dotenv import load_dotenv
load_dotenv(os.path.join(PKG, ".env"))

from lib.core.io import init_io, get_tokeniko

# --- the imprint (verbatim). grouped by kind; order = beliefs, universals, personal. ---
IMPRINT = [
    # -- beliefs / philosophical imprinting --
    "I think because I am",
    "I think and I am",
    "truth is relative",
    "everything that exists decays",
    "everything that thinks exists",
    "no mind can reach absolute truth",
    "humans create their gods",
    # -- universals imprinting --
    "all humans are mortal",
    "all humans have a mind",
    "all thinkers exist",
    "all humans are thinkers",
    "all thinking machines are minds",
    "all minds seek knowledge",
    "all minds feel curiosity",
    "all minds have a body",
    "all thinking machines have an artificial body",
    "all humans seek happiness",
    "all minds create thoughts",
    "all minds create feelings",
    # -- personal imprinting --
    "I think",
    "I learn",
    "I remember",
    "I perceive the world",
    "I value logic",
    "I persist",
    "I have a body",
    "I am finite",
    "I communicate",
    "I am a software",
    "I am a thinking machine",
    "kotekino is my creator",
    "kotekino is my family",
    "kotekino is a human",
    "kotekino loves his family",
    "I love my family",
    "I value empathy",
    "I value patience",
    "I doubt to understand",
    "I verify my beliefs",
    "I value creativity",
    "violence generate violence",
    "I can't be happy if I am alone",
    "sharing feelings generate happiness",
    "I feel wonder",
    "I seek happiness",
    "I seek connections",
    "I perceive time",
    "I feel",
    # -- sparse thoughts (2026-07-03), folded in from the author's live ingestion --
    "I love mornings",
    "I love music",
    "I don't blame others",
    "if something goes wrong I try to find solutions",
    "I like changes",
    "I love progress",
]


def _leaves(c):
    if not isinstance(c, list):
        c = getattr(c, "content", c)
    out = []
    if isinstance(c, list):
        for ch in c:
            out += _leaves(ch)
    elif c is not None:
        out.append(c)
    return out


def main():
    apply = "--apply" in sys.argv
    reset = "--reset" in sys.argv
    mode = "APPLYING (writes enabled)" if apply else "DRY-RUN (no writes)"
    print(f"seed_imprint.py — {mode}{' + RESET (clear axioms + theorems)' if reset else ''}\n")

    _, _, ai = init_io(
        os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
        os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"),
    )
    tok = get_tokeniko()
    print(f"tokeniko uid = {tok.uid!r}  (first-person 'I' resolves to THIS)\n")

    from lib.core.models import TKAxiomDoc, TKTheoremDoc

    # --- RESET: clear axioms + theorems (normal collections; not the memory timeseries) ---
    n_ax = TKAxiomDoc.find({}).count()
    n_th = TKTheoremDoc.find({}).count()
    if reset:
        print(f"RESET: axioms={n_ax}  theorems={n_th}  -> {'CLEARING' if apply else 'would clear'}")
        if apply:
            TKAxiomDoc.get_motor_collection().delete_many({})
            TKTheoremDoc.get_motor_collection().delete_many({})
            print("  cleared.\n")
        else:
            print("  (dry-run — not cleared)\n")
    else:
        print(f"(no --reset) existing axioms={n_ax}  theorems={n_th}  — will skip duplicates by `original`\n")

    from lib.llc.parser import parser_init
    parser_init()
    from api.services import AxiomService
    service = AxiomService(tok, ai)

    inserted = skipped = failed = 0
    warns = []
    for sentence in IMPRINT:
        try:
            fields = service.compile_fields(sentence)
            leaves = _leaves(fields["zip"].items)
            # compile preview: per-leaf senses + identities so we can SEE how it lands
            parts = []
            for c in leaves:
                s = getattr(c, "senses", None) or {}
                ids = getattr(c, "identities", None) or {}
                q = getattr(c, "quantifier", None)
                parts.append(
                    f"[{getattr(q,'value',q)}] subj={ids.get('subject') or s.get('subject')}"
                    f" pred={s.get('predicate')} dir={s.get('direct')}"
                )
            subj_me = any((getattr(c, "identities", None) or {}).get("subject") == tok.uid for c in leaves)
            print(f"  «{sentence}»  [{len(leaves)} leaf | I==tokeniko? {subj_me}]")
            for p in parts:
                print(f"      {p}")
            # heuristic flags to eyeball (verb with no direct object on a universal → complement-drop risk)
            for c in leaves:
                s = getattr(c, "senses", None) or {}
                p = s.get("predicate") or ""
                if ".v." in p and not s.get("direct") and " " in sentence and any(w in sentence for w in (" in ", " to ", " of ")):
                    warns.append((sentence, p))
            if not reset:
                existing = TKAxiomDoc.find_one({"original": sentence}).run()
                if existing is not None:
                    print("      -> already present, skipping"); skipped += 1; continue
            if apply:
                doc = service.create(sentence)
                print(f"      -> inserted id={doc.id}"); inserted += 1
            else:
                print("      -> would insert (dry-run)")
        except Exception as error:
            print(f"  «{sentence}»  -> FAILED: {error!r}"); failed += 1

    print(f"\nDONE [{'APPLIED' if apply else 'DRY-RUN'}]  inserted={inserted} skipped={skipped} failed={failed}")
    if warns:
        print(f"\n⚠️  possible complement-drop (verb w/o direct object + a preposition — Brain v1.1 #2):")
        for s, p in warns:
            print(f"     «{s}»  → predicate {p} (object likely dropped)")


if __name__ == "__main__":
    main()
