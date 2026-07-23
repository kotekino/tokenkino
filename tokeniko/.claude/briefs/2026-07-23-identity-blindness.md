# BRIEF: the identity-blindness family — the `role_key` cure

> Work order for the 1st Officier. Design author-endorsed 2026-07-19; the reference map is
> `doc/ref/notes.md` § "The identity-blindness family" — READ IT FIRST, it is the brief's other
> half (disease, failure modes, blind sites, healthy organs, sense-only-by-design list).
> `CLAUDE.md` is law. DO NOT commit.

## The disease (one line)

Two referent kinds with disjoint keys — CLASS by WSD sense (`TKZipContent.senses`), INDIVIDUAL by
identity uid (`TKZipContent.identities`) — and any site reading only `senses.get(role)` is
silently blind to half the world (honest-looking IDK, never an error).

## The build (four pieces, ordered)

1. **The `role_key` primitive** — ONE shared reader, homed in `lib/llc/evaluator/` (e.g. a small
   `e_keys.py` or beside the existing compare helpers):
   `role_key(leaf, role) -> sense | identity uid | None` (sense first or identity first — match
   `evaluation_harness.conclusion_key`'s identity-FIRST discipline where dedup/matching needs it;
   study `brain/thinking._leaf_net_key`, the family's first cure, as the template). Then route
   the EXISTING consumers through it: `_leaf_net_key` (brain/thinking.py) and
   `evaluation_harness.conclusion_key` become thin wrappers or direct callers — one mechanism,
   no scattered `senses.get(...)`.
2. **`e_wh_solve` what-branch** (PREDICATE gap; live specimen «what are you?» → IDK despite the
   stored «I am a software»): identity-subject questions get the **KB-facts branch** — look up
   the injected axioms/theorems for copular/is_a facts keyed by the subject's uid (the leaf's
   identity), answer with the fact's predicate/object. The sense path (is_a hypernym walk) stays
   for class subjects; the uid is NEVER fed to the WordNet graph (sense-only-by-design list).
3. **`e_wh_solve` who-branch** (SUBJECT gap; «who is kotekino?» — the next bounce waiting):
   match the question's predicate by `role_key` (sense OR uid), so identity predicates become
   matchable; solve from KB facts about the named individual.
4. **`e_consistency._contrary_pairs` hygiene**: the same-subject check compares subject senses
   only — two individual-subject leaves read `None == None` and pass BY ACCIDENT. Route the
   subject comparison through `role_key` so individual subjects compare by uid (one-line-ish).

## Scope fence

- IN: the four pieces above + tests.
- OUT: everything on the notes' "sense-only BY DESIGN" list (graph entry points, `e_label`, the
  P2a abstention) — do NOT touch; the polar-question direct-theorem miss («is gold beautiful?» →
  IDK) is a SEPARATE §2 lead, not this brief; no API/service changes; no parser/compiler changes.
- The evaluator package stays DB-agnostic: `e_wh_solve` reads only what the harness INJECTS
  (extend the injected readers if a uid-keyed facts view is needed — the harness builds it,
  `evaluation_harness.py` is the wiring site; the brain stays parser-free).

## Acceptance

- New tests (`tests/test_identity_blindness.py` or extend the existing wh-solve test file —
  match the sibling style): «what are you?» answered from a stored «I am a software» ·
  «who is <name>?» answered from a stored fact about that uid · a class-subject what-question
  still walks is_a (regression) · `_contrary_pairs` catches an individual-subject
  antonym-contrary pair (and the sense path still works) · `role_key` unit table
  (sense-only / identity-only / both / neither).
- Full gate green (`PYTHONPATH=. ../.venv/bin/python -m pytest tests/ -q`, FOREGROUND, ~13 min,
  `pgrep -f pytest` first): all passed, 1 xfailed is the norm.
- Working tree left dirty (NO commit); daemons untouched (they are OFF today — do not start).
- Standing report: outcome / files+whys / gate verbatim / deviations / findings.
