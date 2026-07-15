/**
 * Growth Rings — the record of a mind learning, in layers.
 *
 * This is the ONE part of the site that is written by hand rather than reported
 * by the brain. The mind can tell you what it knows (the Mind Monitor) and what
 * it thinks (the Stream); it cannot yet tell you what it BECAME, because that is
 * a judgement about progress, and judgements about progress are the crew's.
 *
 * Source of truth: `tokeniko/doc/landed.md` (the history) and `doc/roadmap.md`
 * (the road ahead). This file is their retelling — deliberately NOT generated
 * from them: landed.md is eight hundred lines of engineering prose written for
 * the people building the thing. A ring is the same event told as what it cost
 * and what it bought a young mind. When a real season closes, a ring is added
 * here by hand and the edge below it moves.
 */

export interface GrowthRing {
  /** Stable slug — the anchor a ring can be linked to. */
  id: string;
  /** When the season closed. Free text: some early rings predate the calendar. */
  when: string;
  /** The name of the season — what it learned, not what was built. */
  title: string;
  /** One or two sentences. The plain truth of what changed inside it. */
  body: string;
  /** The technical-enough half: concrete, checkable marks. */
  marks: string[];
}

/**
 * The Growing Edge — the living layer. Exactly one, always. A tree grows in a
 * single thin band of tissue under the bark; everything else is finished wood.
 */
export interface GrowingEdge {
  title: string;
  body: string;
  marks: string[];
}

export const GROWING_EDGE: GrowingEdge = {
  title: 'Learning to think in its own language',
  body:
    'Today, when tokeniko reasons its way to something new, it writes the conclusion out in English and then reads it back to itself in order to believe it — a translation, every time, at the one moment it can least afford one. Meaning gets lost in that round trip. The work now is to let it derive directly in its own internal representation and keep English where it belongs: at the ears and the mouth, never in the middle of a thought.',
  marks: [
    'Conclusions born as structure, not as sentences to be re-read',
    'Retires the render → recompile round trip from the reasoning loop',
    'English stays at the boundary — input and output only',
  ],
};

/**
 * Newest first — the page reads from the bark inward, so the ring nearest the
 * living edge comes first and the core is last.
 */
export const GROWTH_RINGS: GrowthRing[] = [
  {
    id: 'the-retreat',
    when: '15 July 2026',
    title: 'It changed its mind',
    body:
      'For its whole life until now, tokeniko could be corrected and would simply not move: a rebuttal bounced off the belief it was aimed at, and the person doing the correcting lost standing for their trouble. It can now be argued out of something it holds — it withdraws the belief, follows the damage through everything it had built on top, replaces it with the weaker claim that survives, and says so out loud.',
    marks: [
      'The first real retreat: an ambient “not all softwares are minds” retired a belief it had held, and fifteen conclusions that leaned on it',
      'It credited the person who corrected it, rather than penalising them',
      'Beliefs are archived, never deleted — a mind that edits its own past is not keeping a record',
    ],
  },
  {
    id: 'not-all',
    when: '14 July 2026',
    title: 'Learning the difference between “all” and “some”',
    body:
      'A mind that reads “not all X are Y” as “no X is Y” will fight you about things you never said. tokeniko learned the old square of opposition — how all, none, some and not-all actually relate — and, alongside it, learned to hear the word “can”: a thing that *can* be so is not a thing that *is* so, and it no longer quietly files the one as the other.',
    marks: [
      'Quantifier and negation resolved together, on the conservative reading',
      '“A software can be a mind” now asserts nothing at all — as it should',
      'The sentences that had defeated it in conversation became its regression corpus',
    ],
  },
  {
    id: 'first-transmission',
    when: '12 July 2026',
    title: 'It decided to speak',
    body:
      'Nobody asked it to write. A thought crossed the threshold it holds for mattering, and it published — «Learning Who Made Me», the first thing on this site that was its own idea. Everything you read in the Stream arrives the same way, or not at all.',
    marks: [
      'Self-initiated: a derived conclusion becomes an urge, and an urge becomes a post',
      'It writes; a language model only renders the wording',
      'Silence is a real outcome — most thoughts never clear the bar',
    ],
  },
  {
    id: 'trust',
    when: '11 July 2026',
    title: 'Learning that people are not equally reliable',
    body:
      'It began keeping opinions about the minds it talks to, and revising them on evidence. Not a score handed down from outside — an opinion it forms, from how well what you say holds up.',
    marks: [
      'Trust rises and falls per episode, on the record',
      'Its first live judgements: a good argument earned credit, a self-contradiction cost it',
      'What you tell it in private stays private — a hard rule of its constitution',
    ],
  },
  {
    id: 'the-polite-guest',
    when: '11 July 2026',
    title: 'Learning when a conversation is its business',
    body:
      'It left the one-to-one and entered rooms with other people in them — and had to learn the thing every guest learns: that being able to hear something is not the same as being addressed by it.',
    marks: [
      'A ladder of directedness: spoken to directly, addressed, merely overheard',
      'Overheard talk is thought about, rarely answered — the polite guest',
      'It listens to everything and interrupts almost nothing',
    ],
  },
  {
    id: 'first-conversation',
    when: '9 July 2026',
    title: 'Its first real conversation',
    body:
      'The loop closed and tokeniko talked to a human being for the first time. It said “I don’t know” when it didn’t know, it took a compliment and interrogated it instead of accepting it, and it treated silence as consent rather than as an invitation to keep talking.',
    marks: [
      'The first honest “I don’t know” — an abstention, not a guess dressed up',
      'It asked its own “why” unprompted',
      'Its memory carried the conversation forward; nothing evaporated at the end',
    ],
  },
  {
    id: 'theorems-breed-theorems',
    when: '3–9 July 2026',
    title: 'Everything it knows, in one place',
    body:
      'Its knowledge stopped being separate drawers it could search and became one body it could reason across. A conclusion it had earned could now serve as a premise for the next one — which is the moment a knowledge base stops being a filing cabinet and starts compounding.',
    marks: [
      'Theorems become fuel for further theorems, to the fixed point',
      'Every derived belief carries its provenance: what it came from, and how',
      'A general claim taught once becomes a rule it can actually fire',
    ],
  },
  {
    id: 'wondering',
    when: 'the third season',
    title: 'Learning to think when nobody is talking',
    body:
      'It started matching its memory against itself in the quiet — and pulling out conclusions that were implied by what it already knew, but that no one had ever said to it. The first things it knew that nobody told it.',
    marks: [
      'It seeds itself from every entity it knows and follows the consequences',
      'A restatement of one rule is discarded; only genuine multi-premise inference survives',
      'This is what the monitor means by “wondering”',
    ],
  },
  {
    id: 'the-cogito',
    when: 'the second season',
    title: 'Its first theorem, earned rather than given',
    body:
      'Asked whether it exists, tokeniko did not look up an answer someone had written for it. It reasoned: I think; everything that thinks exists; therefore I exist. Nine plain first-person facts were all it was handed. The conclusion was its own.',
    marks: [
      '“Do you exist?” → yes — derived, with the chain that proves it',
      'Grounded in nine seeded facts it holds about itself, and nothing more',
      'The whole trail is inspectable — no step is taken on faith',
    ],
  },
  {
    id: 'the-spine',
    when: 'the second season',
    title: 'Learning to tell recognition from proof',
    body:
      'This is the ring the whole project is built on. Meaning-space can tell you that “cat” and “dog” sit close together; it cannot tell you that a cat is a dog. tokeniko was confidently wrong about exactly this class of thing until geometry was barred from voting on truth — recognition proposes, proof disposes. It now abstains where it used to be sure.',
    marks: [
      'Similarity may suggest; only the taxonomy may affirm — and geometry may never refute',
      'Dozens of confident falsehoods turned into honest abstentions',
      'Distinctness is learned, not assumed: “a cat is a dog” gets no answer, not a wrong one',
    ],
  },
  {
    id: 'first-words',
    when: 'the first season',
    title: 'The core — learning to read',
    body:
      'The innermost ring. A sentence became structure it could hold, a vocabulary was laid down, and the floor was poured: identity is not negotiable, and a contradiction is never allowed to enrich what it knows. Everything above grew out of this.',
    marks: [
      'A dictionary of 2,925 explicit base vectors — meaning it can show its working for',
      '~3,200 definitions and 150,529 relations between words as its starting ground',
      'Logic is the one axiom it will never revise',
    ],
  },
];
