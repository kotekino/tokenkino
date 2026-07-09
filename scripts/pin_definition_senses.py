# ------------------------------------------------------------------------------------------------
# pin_definition_senses.py — STEP 5.1 WRITER: pin every definition's SUBJECT sense to the TRUE
# WordNet synset it was generated from (gloss-inversion ground truth), patching the stored zip
# IN PLACE — `senses["subject"]` + the subject tensor's 2925-dim semantic segment — so label and
# geometry stay in sync (the same in-place style as the genus untangle, c_untangle.py).
#
# WHY: definitions were framed by glosses.py as "a {word} is {clean_gloss(synset.definition())}"
# from a KNOWN synset, but compile-time WSD re-guessed the subject and got it wrong 9.3% of the
# time (probe_subject_wsd.py) in three ways: POS mis-typing (behind.r.01 in a noun frame), lemma
# drift (dvd -> cadmium.n.01), true sense-number errors (church.n.02). Plus 120 adjective-frame
# definitions ("something bottom is ...") carrying a NOUN subject sense — the source of false
# noun is_a edges (bottom.n.01 is_a rank.n.01). Ground truth recovers ALL of them.
#
# RE-RUNNABLE + IDEMPOTENT (a no-op once pinned). Definitions are recompiled from `original` by
# recompile.py and new batches are stored unpinned by glosses.py — RUN THIS AFTER EITHER, then
# rebuild the derived tiers (extract_definitions / extract_sufficiency / extract_differentia).
#
# DRY-RUN by default — prints the full ledger, writes nothing.
#   python scripts/pin_definition_senses.py            # dry-run (ledger only)
#   python scripts/pin_definition_senses.py --apply     # patch the zips (operator-gated)
#   VERBOSE=1 ...                                       # list every patched definition
# ------------------------------------------------------------------------------------------------
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko", ".env"))

from nltk.corpus import wordnet as wn

from lib.core.io import init_io
from lib.core.models import TKDefinitionDoc, TKDictionaryDoc
from lib.core.kb_extract import _zip_leaves

VERBOSE = os.getenv("VERBOSE") == "1"
BAR = "=" * 100

# the subject role tensor layout (tkzip.py): 300 markers + 2925 semantic + 12 spacetime
_SEM_LO, _SEM_HI = 300, 300 + 2925

# ---- gloss-inversion (mirror glosses.py EXACTLY; probe_subject_wsd.py imports these) ----
_PAREN_RE = re.compile(r"\([^)]*\)")

def clean_gloss(gloss: str) -> str:
    g = _PAREN_RE.sub("", gloss or "")
    g = re.split(r"[;:]", g, 1)[0]
    g = g.replace("`", "").replace('"', "").strip()
    g = re.sub(r"\s+", " ", g)
    return g

_NOUN_FRAME = re.compile(r"^an? (\S+) is (.+)$")
_ADJ_FRAME = re.compile(r"^something (\S+) is (.+)$")

def recover_truth(original: str):
    """(word, true_sense|None, frame) — invert the gloss framing back to the source synset."""
    m = _NOUN_FRAME.match(original or "")
    if m:
        word, tail = m.group(1), m.group(2).strip()
        for syn in wn.synsets(word):
            if syn.pos() == "n" and clean_gloss(syn.definition()) == tail:
                return word, syn.name(), "noun"
        return word, None, "noun"
    m = _ADJ_FRAME.match(original or "")
    if m:
        word, tail = m.group(1), m.group(2).strip()
        for syn in wn.synsets(word):
            if syn.pos() in ("a", "s") and clean_gloss(syn.definition()) == tail:
                return word, syn.name(), "adj"
        return word, None, "adj"
    return None, None, "other"


_vector_cache: dict[str, object] = {}

def _vector_of(sense: str):
    if sense not in _vector_cache:
        doc = TKDictionaryDoc.find_one({"sense": sense}).run()
        _vector_cache[sense] = doc.vector if (doc and doc.vector) else None
    return _vector_cache[sense]


def pin_doc(doc, truth: str):
    """Patch every leaf whose subject sense is the (single) compiled main-subject sense.
    Returns (leaves_patched, vector_swapped) — (0, False) when already pinned/no subject."""
    if doc.zip is None:
        return 0, False
    leaves = [lf for lf in _zip_leaves(doc.zip.items) if (lf.senses or {}).get("subject")]
    if not leaves:
        return 0, False
    compiled = leaves[0].senses["subject"]
    if compiled == truth:
        return 0, False
    vec = _vector_of(truth)
    patched = 0
    for lf in leaves:
        if lf.senses.get("subject") != compiled:
            continue  # a sub-clause with a different subject — not the definiendum
        lf.senses["subject"] = truth
        if vec and lf.subject and len(lf.subject) == 3237:
            lf.subject[_SEM_LO:_SEM_HI] = vec
        patched += 1
    return patched, bool(vec)


def main():
    apply = "--apply" in sys.argv
    init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
            os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))

    docs = TKDefinitionDoc.find({"archived": False}).to_list()
    mode = "APPLY" if apply else "DRY-RUN"
    print(f"\n{BAR}\nDEFINITION SUBJECT-SENSE PIN  [{mode}]  ({len(docs)} active definitions)\n{BAR}")

    stats = Counter()
    ledger = []   # (frame, word, old, new, vector_swapped, n_leaves, original)
    to_save = []
    for doc in docs:
        word, truth, fr = recover_truth(doc.original)
        if fr == "other":
            stats["skip: unrecognized frame"] += 1
            continue
        if truth is None:
            stats["skip: truth unrecovered"] += 1
            continue
        leaves = [lf for lf in _zip_leaves(doc.zip.items) if (lf.senses or {}).get("subject")] if doc.zip else []
        if not leaves:
            stats["skip: no subject sense in zip"] += 1
            continue
        old = leaves[0].senses["subject"]
        if old == truth:
            stats["already pinned / correct"] += 1
            continue
        n, vec_ok = pin_doc(doc, truth)
        if n == 0:
            stats["skip: no patchable leaf"] += 1
            continue
        stats[f"PIN ({fr} frame)"] += 1
        stats["  + vector swapped" if vec_ok else "  + sense only (no dictionary vector)"] += 1
        ledger.append((fr, word, old, truth, vec_ok, n, doc.original))
        to_save.append(doc)

    print("\nLEDGER — what changes (and what does not):")
    for k in sorted(stats):
        print(f"  {k:38} {stats[k]}")
    n_pin = len(to_save)
    print(f"\n  TOTAL definitions to patch: {n_pin}   (of {len(docs)}; every other doc untouched)")
    print("  fields touched: zip leaves' senses['subject'] + subject tensor semantic segment ONLY")
    print("  NOT touched: original, raw, trusted, archived, readonly, createdAt, sourceId, channel")

    shown = ledger if VERBOSE else ledger[:25]
    for fr, word, old, new, vec_ok, n, original in shown:
        print(f"    [{fr:4}] {word:16} {old:24} -> {new:26} vec={'Y' if vec_ok else '-'} leaves={n}  «{original[:44]}»")
    if not VERBOSE and n_pin > 25:
        print(f"    ... {n_pin - 25} more (VERBOSE=1 to list all)")

    if not apply:
        print(f"\n  DRY-RUN — nothing written. Re-run with --apply to patch.\n{BAR}")
        return

    saved = 0
    for doc in to_save:
        doc.save()
        saved += 1
    print(f"\n  patched + saved {saved} definitions.")
    print(f"  NEXT: rebuild the derived tiers (extract_definitions --apply, extract_sufficiency --apply,")
    print(f"        extract_differentia --apply when green-lit) so the fuel picks up the pinned senses.\n{BAR}")


if __name__ == "__main__":
    main()
