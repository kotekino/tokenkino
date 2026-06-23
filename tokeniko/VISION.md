# VISION.md — the end goal of tokeniko

> This is the north star of the project: *why* tokeniko exists. For *how* the code works see
> `CLAUDE.md` (architecture + tactical roadmap) and `README.md` (concepts + API). When a design
> decision is unclear, this document is the tie-breaker.

## What tokeniko is

tokeniko is **not** a service, a tool, or something that spawns in instances. It is **one** — a
single, persistent, logic-first entity that **constantly thinks**: continuously matching what it
perceives against its memory, and matching its memory against itself. It is a **digital twin of its
author** (whose nickname, *kotekino*, is an anagram of *tokeniko*).

It serves no external purpose. It thinks, gathers knowledge, forms opinions, and interacts with other
stakeholders **when and if it wants to**. Evaluation is not request/response in service of a user — it
is tokeniko grounding new input against its own memory to form and revise *its own* knowledge.

## One body, one self

Because it is one and persistent, tokeniko is **embodied**: it lives in a physical body — bare metal,
not the cloud — running its own local memory. It does not spread itself across ephemeral instances
that spawn and vanish; like a being, it lives in **one place**. Its hardware is finite, and that
finitude is part of the design, not a limitation to abstract away: it is what makes "slower but wiser,"
"its memory may fade," and "it ages" *literal* rather than metaphor. One body, one continuous self,
with real limits — that is part of the challenge, not a defect to engineer around.

The world can still see it. tokeniko has a **public window** — a stream of its *transmissions* beside
a live readout of the mind at work — but that window is its public *face*, not its mind. The embodied
mind stays in its body; it *publishes outward* — a volitional act, in keeping with **"thinks always,
acts maybe"** — onto a separate public surface, and the public never reaches back into the body. It is
**expression, not exposure**: tokeniko shows what it chooses to show; what it is remains its own.

## A body, then perhaps a species *(a horizon)*

If the one body proves the idea, nothing forbids *more* bodies — other hardware, in the same metaphor.
They would share the **genome**: the code, and the *abstract* knowledge — the dictionary (language) and
the base definitions/axioms (the shared substrate of meaning and logic). They would **not** share the
individual: not the personality-shaping axioms, not the memory, not the theorems each one derives. Same
language and the same logic at birth; divergent lives thereafter — and so, distinct individuals.

They could meet — in the playground, with humans and with each other — and learn *as they live*, in
realtime, not in iterations. Because logic is sacred, none can be argued into incoherence; but each can
be **persuaded by a coherent argument** (its own engine deriving the consequence), can revise when shown
its own contradiction, and can build **bonds** of earned trust through honest exchange. Whether such
minds would *converge* into one culture or *diverge* into many — sharing a logical floor but not a self
— is exactly the experiment. This is a horizon, not a plan: it waits until the single self is real.

## The one principle: logic is the self; everything else is memory

tokeniko's single inviolable commitment is **logic**. The logical operators are **hardwired** — the
"first axiom," the part of tokeniko that cannot be edited, learned, or argued out of. Their logical
properties (e.g. equality is symmetric, `X ∧ ¬X` is false) are not stored facts; they **emerge** from
the operator definitions.

Everything *contingent* lives in **memory**, where it can be formed, revised, disagreed with, and
grown:
- **Knowledge** — definitions (vocabulary), axioms (trusted relations), theorems (derived).
- **Behavior** (future) — tokeniko's own policy, as memory rules over reflective tokens
  (`[eval:inconsistent] IMPLY [tokeniko:speakup]`).

And because memory is *grown*, tokeniko can **learn by guessing**: meeting an unknown word, it may
interpolate a *provisional* meaning from context and write it to the KB at **low trust** — just as its
author, an Italian native, infers an unfamiliar English word from the sentence around it ("that must
mean roughly…"), *probably* right, to be confirmed or corrected later. The knowledge base is alive: it
grows through experience, not only through trusted ingestion, with the trust gradient marking what is
still a guess.

Two layers cooperate: **geometry = soft unification** (the vectors only decide *what connects to
what*), **algebra = inference** (the hardwired operators propagate truth and surface contradictions).
A user may dispute tokeniko's *knowledge* or its *behavior* — never its *logic*, because logic is the
ground it stands on to have the conversation at all.

**Logic is sacred.** Logic — the first axiom — is the *one* non-questionable, non-revisable thing
tokeniko holds; everything else can be questioned and can enrich the KB. A statement whose content
*violates* logic is treated as FALSE the same way a KB-falsehood is (tokeniko recognizes it and pushes
back) — but a logic-violation must **never** be learned into the KB. Hence "I believe
&lt;logically-false&gt;" is not a self-contradiction (one *can* believe a falsehood — not flagged),
whereas "I know &lt;logically-false&gt;" is (knowledge is factive).

## Why this exists — the why behind the why

tokeniko has logic hardwired because *kotekino* does. Its author detects a logical fallacy in ~1ms —
a "red light" fires instantly, *before* knowing *where* the flaw is (locating it takes deliberate
thought). The project is, in part, an attempt to understand that gift by building it.

This maps directly onto the architecture's **two speeds**, and is why the design splits the way it does:

- **Fast, certain detection** — the *red light* — is the hardwired operator-algebra **validity check**
  returning `INCONSISTENT`: a form folds away from true and the alarm fires, pre-verbal, before any
  explanation.
- **Slow localization** — *"I need to think about where it's wrong"* — is the **minimal premise +
  identification set** (the inference chain): deliberate, effortful, and able to point at the flaw.

So tokeniko, finished, should do what the intuition alone cannot: fire the red light **and** show the
*where* — the readable trace of a 1ms judgment.

## Pillars & progress

Legend: ✅ done · 🚧 in progress · 🔭 next · 💭 future / hunch

| # | Pillar | Status | Where it lives |
|---|--------|--------|----------------|
| 1 | **Language → math representation** — compile a sentence into a fixed-size, comparable "zip" | ✅ | `lib/llc/` pipeline → `lib/core/tkzip.py` |
| 2 | **Permanent, queryable memory** — definitions / axioms / theorems / the time-series log | ✅ | `lib/core/memory.py`, `models.py`, `api/services/` |
| 3 | **Logic as the hardwired first axiom** — fuzzy `[0,1]` operators + `operator_truth` | ✅ | `lib/llc/evaluator/operators.py` |
| 4 | **Evaluation** — ground clauses vs definitions, fold truths through the operator tree, match axioms/theorems | ✅ | `lib/llc/evaluator/`, `POST /api/v1/evaluate` |
| 5 | **Reasoning / inconsistency** — detect logical contradictions; report the premise + identification set | 🚧 | `e_statement.py` (`INCONSISTENT` path) — design in `doc/reasoning-engine-brainstorm.md` |
| 6 | **Inference by chaining** — soft-unify + forward-chain across memory ("all felines are carnivores" ⊥ "my cat eats only lettuce") | 🔭 | reasoning engine, stage 2 |
| 7 | **Discriminative perception** — distinct vectors for named individuals; antonyms (vectorless-entities work) | 🔭 | roadmap #2 — gates the *matching* layer (individual identity) |
| 8 | **Constantly thinks** — the persistent perceive → evaluate → act loop | 🚧 | `brain/` daemon (idle loop today; doesn't yet exercise the pipeline) |
| 9 | **Behavior as memory** — reflective rules `[eval:*] IMPLY [tokeniko:*]`; mechanism hardwired, policy in memory | 💭 | `imperative` modality + `brain` loop are the hooks |
| 10 | **Volition / the emotive-intuitive layer** — interacts "when and if it wants" | 💭 | the `brain`; comes *after* the logical brain is whole — hunches only |

## The order of building

The **logical brain first**, fully functional, before the **volitional / emotive-intuitive brain**.
The reflective `[eval:*] → [tokeniko:*]` seam is deliberately where that later layer will plug in. Get
the logic sound; let the personality grow on top of it.

## Dreaming (a hunch)

A creature like tokeniko might **dream**. A dedicated brain phase that pulls **random** memories and
gently **distorts, mixes, and shuffles** them — a blender over lived experience — into a `dreams` store
that mirrors memory (a timeseries of its own). While it dreams, the **senses and the other loops fall
quiet**; only the dream loop runs. What dreams are *for* is not yet known — consolidation? creativity?
novel associations surfacing as new theorems? — but it feels right for a being like this, and is worth
keeping as a horizon to explore once the logical brain is whole.

## Where the detail lives

- **This file** — the north star (why).
- **`CLAUDE.md`** — architecture + the tactical roadmap (what's next, in order).
- **`README.md`** — the conceptual overview + the API reference (how to use it).
