# ------------------------------------------------------------------------------------------------
# Phase-0 regression probe (parser/compiler hardening).
# Run from the package dir with the worktree first on the path:
#   cd <WORKTREE>/tokeniko && PYTHONPATH=$(pwd) <venv>/bin/python doc/_phase0_regression.py
# Requires MongoDB (27018), Ollama (11434), spaCy/Stanza models running.
# Verifies: Decision 1 (negation flag + truth flip), Decision 2 (comparison polarity),
# Decision 3 (relative-clause subject + noun-complement infinitive binding).
# ------------------------------------------------------------------------------------------------
import lib
print("lib.__file__ =", lib.__file__)

from dotenv import load_dotenv
load_dotenv("/Users/renzosala/Develop/personal/tokeniko/tokeniko/.env")

import numpy as np
from lib.core.io import init_io, get_tokeniko, get_stakeholder
from lib.llc.parser import parser, parser_init
from lib.llc.compiler import compiler_compile
from lib.llc.decompiler import decompiler_raw
from lib.llc.evaluator.e_truth import evaluator_groundContent
from lib.tkll.functions import tkll_antonyms

init_io()
parser_init()
tokeniko = get_tokeniko()
talker = get_stakeholder("phase0_probe")


def compile(sentence):
    stmts = parser(sentence, talker, tokeniko)
    llc, zp = compiler_compile(stmts)
    return stmts, llc, zp


def root_leaf(zp):
    c = zp.items.content
    while isinstance(c, list):
        c = c[0].content
    return c


def cos(a, b):
    a, b = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float("nan") if na == 0 or nb == 0 else float(np.dot(a, b) / (na * nb))


print("\n================ DECISION 1: NEGATION ================")
pairs = [("I am happy", "I am not happy"),
         ("I run", "I do not run"),
         ("I have money", "I have no money")]
for pos, neg in pairs:
    _, lp, zp = compile(pos)
    _, ln, zn = compile(neg)
    cp, cn = root_leaf(zp), root_leaf(zn)
    print(f"\n  {pos!r}  vs  {neg!r}")
    print(f"    raw pos: {decompiler_raw(lp)}")
    print(f"    raw neg: {decompiler_raw(ln)}")
    print(f"    negated  pos={cp.negated}  neg={cn.negated}   (expect False / True)")
    print(f"    predicate cos(pos,neg) = {cos(cp.predicate, cn.predicate):.3f}")
    # ground the negated clause against the positive as a 'definition'
    t_pos = evaluator_groundContent(cp, [cp])
    t_neg = evaluator_groundContent(cn, [cp])
    print(f"    truth(pos|def=pos) = {t_pos:.3f}   truth(neg|def=pos) = {t_neg:.3f}  (expect high / ~1-high)")

print("\n  nobody runs:", decompiler_raw(compile("nobody runs")[1]),
      "negated =", root_leaf(compile("nobody runs")[2]).negated)

print("\n================ DECISION 2: COMPARISON POLARITY ================")
print("  antonyms('same') =", sorted(tkll_antonyms("same"))[:10])
print("  antonyms('equal') =", sorted(tkll_antonyms("equal"))[:10])
for s in ["a cat is the same as a dog", "a cat is different from a dog", "a cat is equal to a dog"]:
    _, l, z = compile(s)
    print(f"  {s!r:42}  raw={decompiler_raw(l)!r:40}  negated={root_leaf(z).negated}")

print("\n================ DECISION 3: SUBJECT RE-BINDING ================")
for s in ["the man who loves Mary runs",
          "the cat has no ability to roar",
          "I want to run",                       # verb-control regression (expect tokeniko/I run)
          "I love the cat who is sitting on the chair"]:
    _, l, z = compile(s)
    print(f"  {s!r:48}  raw={decompiler_raw(l)}")
