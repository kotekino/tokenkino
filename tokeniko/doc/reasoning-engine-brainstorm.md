# Reasoning engine — brainstorm summary (roadmap #1: the INCONSISTENT path)

> **Status: brainstorm, not a committed plan.** This captures the design conversation so we have a
> shared, written context to build on. The strategy is still being formed. See `VISION.md` for the
> north star and `CLAUDE.md` for the tactical roadmap. The terse version lives in Claude memory as
> `reasoning-engine-architecture`.

## The starting question

Roadmap #1 asks tokeniko to detect **logical inconsistency** — e.g. the form `(A eq B) IMPLY (B noteq
A)` should come out false/illegal. How?

## The core hunch (kotekino) — and why it holds

**Inconsistency is a property of the hardwired operator algebra; you compute it, you don't store it.**
Because the operators are fixed truth-functions, the validity of a form is decidable by evaluating it
over its operand variables. You never need an inconsistent axiom sitting in memory to "notice" the
contradiction — it surfaces by itself.

Worked example: `a eq b` grounds intrinsically as `X = compare(a, b)`, and `a noteq b = 1 − X` (the
complement is **algebraic**). So `a eq b IMPLY a noteq b` = `IMPLY(X, 1−X)`. With Gödel implication
that is `1` only when `X ≤ 0.5`, and `1−X (<1)` when `X > 0.5` → **not a tautology** → it cannot be a
valid axiom.

## Key refinements that came out of it

1. **Logical negation ≠ semantic antonymy.** The early worry that "inconsistency needs antonym
   vectors (roadmap #2)" was aimed at the wrong target. `noteq = 1 − eq` and `NOT = 1 − x` are
   **hardwired algebra**, not word-geometry. So *logical* inconsistency does **not** need #2. #2 only
   limits the **matching** layer (see below), specifically **individual** identity.

2. **Validity check, not point-sampling.** An axiom/theorem is valid iff its folded truth is `≡ 1`
   for *all* operand assignments → test `min over assignments == 1`, **not** a single sample at
   `X = 0.5` (which is fragile exactly at the Gödel `≤`/`<` boundary). For `IMPLY(X, 1−X)` the min is
   `0` at `X = 1`, so it fails validity unambiguously. This is what rejects admitting
   `a eq b imply a noteq b` as an axiom.

3. **It only fires among LINKED truths.** Two independent clauses (free variables) are always
   satisfiable — nothing surfaces. A contradiction needs the clause truths *coupled*. eq/noteq couple
   for free (shared operand pair → `X` and `1−X`). The general case couples through a **chain of
   definitions/axioms**.

4. **The linchpin moved — from "detect eq/noteq" to "connect clauses through the KB".** Example:
   `A = "all felines are carnivores"`, `B = "my cat eats only lettuce"`. On their own, A and B are
   independent 0.5's — with empty memory tokeniko *correctly* finds no inconsistency. Add bridging
   knowledge ("carnivores eat animals", "a cat is an animal", "lettuce is a vegetable", "a vegetable
   is not an animal") and a linked path appears: cat → carnivore → eats animals; lettuce → not animal;
   "eats only lettuce" ⟹ "eats no animals" ⊥ "eats animals". *Now* the algebra surfaces it. That
   chaining is **forward inference / resolution**.

## The architecture this reveals

- **geometry = soft unification (matching).** The vectors only decide *what connects to what* (is the
  input's "cat" the KB's "cat"? does "my cat" corefer to an entity in memory?). Approximate, fallible.
- **algebra = inference (truth propagation).** The hardwired operators propagate truth along the
  matched edges and surface contradictions. Sound, exact.
- Geometry never "understands"; it only finds matches. Operators do the reasoning.

**"Equality is tricky" = subject/entity matching**, and it is inherently a **similarity + memory**
problem, not a logic problem. Two flavors at different maturity:
- **concept/type** equality ("cat" ⊂ "animal") → dictionary vectors, works today;
- **individual** equality ("my cat" = a specific entity; Mari ≠ Luca) → leans on memory/coreference
  **+ roadmap #2** (named individuals are geometrically identical today).

**Verdicts are relative to tokeniko's realm.** Output the **minimal premise + identification set**
behind a contradiction, so disagreement is *locatable*: shared premises → genuine logical
inconsistency; rejected premise → just divergent knowledge. Reliability is bounded by the *matching*
layer (its confidence travels with the verdict), never by the logic (always sound).

## The boundary principle (the "first axiom")

- **Hardwired = logic.** The operator truth-functions + the procedure that applies them (ground →
  soft-unify → fold → validity-check). Inviolable — tokeniko's *self*. Logical properties **emerge**
  from the operators (`EQ` symmetric by construction; `X ∧ ¬X` folds false) — never stored.
- **Memory = everything contingent.** Knowledge (facts, domain rules) **and** behavior/policy.
  Editable, learnable, per-stakeholder, disagreeable.

## Behavior as memory (later)

Tokeniko's policy can also be memory rules over reserved **reflective tokens**:
`[eval:inconsistent] IMPLY [tokeniko:speakup]`, `[eval:unknown] IMPLY [tokeniko:ask]`. SOAR/ACT-R
lineage. Likely hooks already present: the `imperative` field on `TKZipContent` (a directive's folded
value = activation, not truth) and the `brain` daemon as the perceive → evaluate → act loop. Mechanism
stays hardwired (action-dispatch table, injecting `[eval:*]` tokens, an action **allowlist**); policy
lives in memory. This is the seam where the future volitional / emotive-intuitive layer plugs in.

## Risks to handle

- **Termination / cascades** in chaining and in action firing (depth bounds, loop control).
- **Conflict resolution** when multiple rules fire (highest activation? trust-weighted? most-specific?).
- **Trust / safety** of editable logic+behavior → lean on the `readonly` / `trusted` tiers, the
  **validity check** (gates what may become an axiom), and an **action allowlist**.
- **Physics constants**: the few semi-arbitrary modeling choices (t-norm / implication: Gödel vs
  Łukasiewicz vs product).

## Staging

1. **Intra-statement kernel** — validity / self-contradiction on the input's own folded form
   (`eq/noteq`, `X ∧ ¬X`, `X → ¬X`). No KB chaining. Tractable now; builds the operator-validity core.
2. **Inter-statement** — soft-unification + forward-chaining over the KB, with the minimal-unsat-core
   output. (1) is the degenerate single-step case of (2).

## Open decisions (still to settle)

- **Representation of comparison relations.** `EQ`/`NOTEQ` exist in the operator enum but the compiler
  never emits them; "equal"/"different" compile as predicate words. To make the eq/noteq algebra fire,
  comparison/identity clauses likely need to become `EQ`/`NOTEQ` **operators** with **intrinsic
  grounding** (`compare(operands)` / `1 − compare`), instead of definition-matched declaratives.
- **Quantifiers** — "*all* felines", "*only* lettuce" are not truth-functional connectives; they need
  binding/scoping. "only" is load-bearing in the cat example.
- **Build order** — prototype the intra-statement kernel first, or whiteboard the full inference
  engine (unification + chaining + unsat-core) before any code.
