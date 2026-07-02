# tokeniko — process maps

> BPMN-style **swim-lane** diagrams of every information journey across the components — *the journey of
> each piece of information*, from where it enters to where it lands. Reference material (the roadmap's
> consolidation checkpoint), meant to keep the direction clear as we build. **Mermaid**, not strict BPMN2
> XML (over-formal for an internal map).

## How to view

Open **`viewer.html`** in a browser (no server needed — Mermaid loads from CDN). It's the **single
source of truth** for the diagrams: a styled, navigable viewer with one section per process.

*(GitHub won't render `viewer.html`'s diagrams inline; if we later want in-repo rendering, we mirror each
diagram into a `.md` mermaid block. For now the local viewer is the artifact.)*

## Convention

- **Lanes = stakeholders** — Client · API · Parser · Compiler · Evaluator · Brain · Senses · DB · … —
  each swim-lane is one actor/component the information passes through.
- **▸ green** = start event · **▸ grey** = end event · **◆ amber** = gateway (a fork/decision).
- **solid arrow** = data/control flow · **dotted arrow** = a read / side-lookup (e.g. the KB).
- Cross-lane arrows carry a **message label** (what data crosses).
- **"as-is"** diagrams reflect the code today; **"as-will-be"** diagrams (the senses going-live pieces)
  are *projectual* — drawn ahead to force forward-consistency, clearly marked.

## The maps

| | Process | Kind | Status |
|---|---|---|---|
| **A** | **API compilation pipeline** — sentence → parser → compiler → LLC+zip → contradiction guard → store | as-is | ✅ |
| **B** | **/evaluate** — compile → evaluator (ground / chain / classify) → verdict (PURE) | as-is | ✅ |
| **C** | **Brain coordinator tick** — Actions ▸ Priorities ▸ Thinking routing | as-is | ✅ |
| **D** | **Reactive loop** — perceive → think_one → eval:* → ideas → priorities → actions → senses-out | as-is (senses-out dry-run) | ✅ |
| **E** | **Wondering** — kb_wonder / memory-wondering → materialize (brain→API) | as-is | ✅ |
| **F** | **KB ingestion & tiers** — definitions-as-rules: untangle → edge/rule tiers → reader union | as-is | ✅ |
| **G** | **Senses I/O + public window** — inbound · outbound · blog/ATProto/public Atlas | as-will-be | ✅ |

All seven drawn in one idiom, Mermaid-parse-validated. "as-is" reflects the code today; **G** is largely
*projectual* (inbound listener + public window not built yet — marked purple in the viewer).
