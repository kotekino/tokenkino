# ------------------------------------------------------------------------------------------------
# glosses.py — Phase 1b of the knowledge bootstrap (see tokeniko/doc/plan.md).
# Turn WordNet glosses into tokeniko's own statements: for each STANDARD content-word sense, clean
# the gloss, frame it POS-appropriately into a sentence, compile it through the (Phase-0-hardened)
# pipeline, and route by structure — single-clause -> `definitions`, multi-clause -> `axioms`.
# The "flesh" (properties) on the 1a taxonomy skeleton.
#
# Scope (first pass): the base words (the 2925 Oxford-3000 axes). Neighborhood expansion comes later.
# STRICT, academic-first filtering ("tokeniko learns the slang later"):
#   - skip function words (NLTK stopwords + length<=2) and words with no content-POS sense
#   - content POS only: noun / verb / adjective (+ satellite); adverbs skipped
#   - primary sense per POS only (WordNet orders by frequency); drop informal/slang/etc. glosses
#   - clean the gloss: strip parentheticals, cut at the first ';'/':' (alt-phrasings/examples), de-quote
#   - POS-aware framing: noun "a X is ..."; verb "to X is to ..."; adjective "X means ..."
#
# Usage:
#   python scripts/glosses.py sample [N]   # DRY: compile + show routing for N passing senses, NO writes
#   python scripts/glosses.py [LIMIT]      # REAL: store via the services, resumable (skips existing)
# ------------------------------------------------------------------------------------------------
import os
import re
import sys
import copy

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "tokeniko", ".env"))

import nltk
from nltk.corpus import wordnet as wn
from nltk.corpus import stopwords
nltk.download("wordnet", quiet=True)
nltk.download("omw-1.4", quiet=True)
nltk.download("stopwords", quiet=True)

from lib.core.io import init_io, get_tokeniko
from lib.core.models import TKBaseDoc, TKDefinitionDoc, TKAxiomDoc
from lib.core.utilities import util_indefiniteArticle
from lib.core.tkzip import TKZipContent
from lib.llc.parser import parser, parser_init
from lib.llc.compiler import compiler_compile
from lib.llc.decompiler import decompiler_raw
from api.services import DefinitionService, AxiomService, NotASingleClauseError
import ollama

_STOP = set(stopwords.words("english"))
_INFORMAL = ("informal", "slang", "vulgar", "offensive", "colloquial", "derogatory",
             "disparaging", "ethnic slur", "obscene", "taboo")
_CONTENT_POS = {"n", "v", "a", "s"}  # noun / verb / adjective / adjective-satellite (skip 'r' adverbs)
# This pass: nouns (already done) + adjectives (incl. satellite 's'). Adverbs ('r') skipped. VERBS
# deferred — the "X means <gloss>" frame captures the verb but drags in "means" (a spurious predicate
# / THAT attitude), below the clean-core bar; revisit with a cleaner verb frame. Framing uses NOMINAL
# subjects (see `frame`) to avoid the clausal-subject construction the parser can't bind.
_INGEST_POS = {"n", "a", "s"}
_PAREN_RE = re.compile(r"\([^)]*\)")


def is_function_word(word: str) -> bool:
    return word in _STOP or len(word) <= 2


def is_informal(gloss: str) -> bool:
    g = gloss.lower()
    return any(tag in g for tag in _INFORMAL)


# keep just the core genus-differentia: drop parentheticals, cut at the first ';' or ':' (WordNet's
# alternate phrasings / examples), remove quote artifacts, collapse whitespace.
def clean_gloss(gloss: str) -> str:
    g = _PAREN_RE.sub("", gloss or "")
    g = re.split(r"[;:]", g, 1)[0]
    g = g.replace("`", "").replace('"', "").strip()
    g = re.sub(r"\s+", " ", g)
    return g


# POS-aware sentence frame for a sense
def frame(word: str, pos: str, gloss: str):
    if not gloss:
        return None
    if pos == "n":
        return f"{util_indefiniteArticle(word)} {word} is {gloss}"   # "a cat is a feline mammal"
    if pos == "v":
        return f"{word} means {gloss}"                               # "accept means consider or hold..."
    if pos in ("a", "s"):
        return f"something {word} is {gloss}"                        # "something able is having skill..."
    return None


# the STANDARD content senses of a word: primary synset per content POS, skipping informal glosses
def standard_senses(word: str):
    if is_function_word(word):
        return []
    out, seen = [], set()
    for syn in wn.synsets(word):
        pos = syn.pos()
        if pos not in _INGEST_POS or pos in seen:
            continue
        if is_informal(syn.definition()):
            continue
        seen.add(pos)
        out.append(syn)
    return out


def _leaf_count(item) -> int:
    c = item.content
    if isinstance(c, TKZipContent):
        return 1
    return sum(_leaf_count(ch) for ch in c) if isinstance(c, list) else 0


def setup():
    init_io(os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"), os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"))
    parser_init()
    ai = ollama.AsyncClient(host=os.getenv("OLLAMA_HOST") or "http://localhost:11434")
    return get_tokeniko(), ai


def base_words(limit=None):
    words = [d.word for d in TKBaseDoc.find().sort("index").to_list()]
    return words[:limit] if limit else words


def _sentences(word):
    for syn in standard_senses(word):
        sent = frame(word, syn.pos(), clean_gloss(syn.definition()))
        if sent:
            yield syn.pos(), sent


def sample(n=25):
    me, ai = setup()
    print(f"DRY sample: first {n} senses that PASS the filter (no writes):\n")
    defs = axioms = printed = skipped_words = 0
    for w in base_words():
        sents = list(_sentences(w))
        if not sents:
            skipped_words += 1
            continue
        for pos, sent in sents:
            try:
                flat, z = compiler_compile(copy.deepcopy(parser(sent, me, me, ai)))
                kind = "definition" if _leaf_count(z.items) == 1 else "axiom"
                defs += kind == "definition"; axioms += kind == "axiom"
                print(f"  [{kind:10s}|{pos}] {sent}")
                print(f"                 -> {decompiler_raw(flat)}")
            except Exception as e:
                print(f"  [ERROR] {sent!r}: {e!r}")
            printed += 1
        if printed >= n:
            break
    print(f"\nprinted {printed} senses | would store: {defs} definitions, {axioms} axioms"
          f" | {skipped_words} words skipped by the filter so far (DRY — nothing written)")


def exists(original: str) -> bool:
    return bool(TKDefinitionDoc.find_one({"original": original}).run()
                or TKAxiomDoc.find_one({"original": original}).run())


def main(limit=None):
    me, ai = setup()
    defs_svc = DefinitionService(me, ai)
    axiom_svc = AxiomService(me, ai)
    words = base_words(limit)
    print(f"Ingesting glosses for {len(words)} base words -> definitions/axioms ...")
    defs = axioms = skipped = errors = 0
    for i, w in enumerate(words):
        for _pos, sent in _sentences(w):
            if exists(sent):
                skipped += 1
                continue
            try:
                defs_svc.create(sent)
                defs += 1
            except NotASingleClauseError:
                axiom_svc.create(sent)
                axioms += 1
            except Exception as e:
                errors += 1
                print(f"  [ERROR] {sent!r}: {e!r}")
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(words)} words | {defs} defs, {axioms} axioms, {skipped} skipped, {errors} err")
    print(f"\n✅ Done. {defs} definitions, {axioms} axioms, {skipped} skipped, {errors} errors.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "sample":
        sample(int(sys.argv[2]) if len(sys.argv) > 2 else 25)
    else:
        main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
