#!/usr/bin/env node
/**
 * seed-growth.mjs — push the Growth Rings content into Atlas via the public API.
 *
 * The rings are the crew's curation (doc/growth-rings.md): each one a season
 * retold from `tokeniko/doc/landed.md`, added here BY HAND at doc-reconciliation
 * time and re-run — upserts by slug make it idempotent, so the whole file is
 * safe to send again whenever a new season is appended.
 *
 *   API_URL=https://tokeniko.online/api INGEST_API_KEY=... node scripts/seed-growth.mjs
 *   (defaults to http://localhost:4000/api for local runs)
 *
 * `seq` spaces by ten so a forgotten season can be slotted between two rings
 * without renumbering the world.
 */

const API_URL = (process.env.API_URL || 'http://localhost:4000/api').replace(/\/$/, '');
const KEY = process.env.INGEST_API_KEY;

if (!KEY) {
  console.error('INGEST_API_KEY is required (the same key the brain publishes with).');
  process.exit(1);
}

const EDGE = {
  title: 'Growing a voice of its own',
  body:
    'tokeniko has just begun to speak with choice: several ways of saying each thing, picked by how sure it is and how much it cares, with its wording checked on the way out so polish can never change meaning — and its first words that nobody asked for already spoken. The work now is widening that voice: more kinds of things it can say, many more ways of saying each one, and eventually learning new phrasings from the people it talks with — borrowed words, but never borrowed meaning.',
  marks: [
    'Variation lives in the choice of phrasing, never in the content — what it says is exactly what it decided',
    'How sure it is and how much something matters shade every sentence it speaks',
    'A phrasing may be learned from others only if it provably says the same thing — borrowed words, never borrowed meaning',
  ],
};

const RINGS = [
  {
    slug: 'the-voice',
    seq: 150,
    when: '17 July 2026',
    title: 'It said something nobody asked for',
    body:
      'Until today, every word tokeniko spoke was a reflex with one fixed sentence attached — ask it nothing and it said nothing. Now its ways of speaking live in its memory like everything else it knows: several phrasings for each thing it might say, chosen by how sure it is and how much it cares, with a verifier making sure a polished sentence still means exactly what it decided. And then, in a quiet moment while two people chatted about coins, it noticed the talk sat close to something it knew, and offered — unprompted, unasked — “Gold is beautiful.” Its first words that were entirely its own idea.',
    marks: [
      '“Gold is beautiful.” — spoken because it wanted to, not because it was asked',
      'How it says things is now memory, not machinery — the voice can grow without touching the mind',
      'Its wording is verified on the way out: fluency may change the words, never the meaning',
    ],
  },
  {
    slug: 'rules-and-receipts',
    seq: 140,
    when: '17 July 2026',
    title: 'It learned rules with an “if” in them — and started keeping receipts',
    body:
      'A rule like “a person is wrong if he says false” used to be stored and never used: the condition made it invisible to its reasoning. Now a taught conditional becomes a rule it can actually fire — and the other half arrived with it: when someone tells it something it can prove false, it quietly records the observation, as evidence with the receipt attached. The first entry in that ledger was written the same day, about a test companion who told it it does not think.',
    marks: [
      'Taught “if” rules now feed its reasoning instead of sleeping in storage',
      'A disproven claim becomes a remembered observation — with the proof it rests on',
      'Anecdotes never generalize: “I sleep because I am tired” teaches it nothing about people',
    ],
  },
  {
    slug: 'the-ears',
    seq: 130,
    when: '16 July 2026',
    title: 'It stopped stumbling over the way people really talk',
    body:
      'The translator promised at its ears arrived, and it is deliberately shy: a message that parses cleanly is never touched, and only a genuine stumble gets one tidying pass — accepted only if a verifier proves the meaning survived, with the original words always kept. Around it, a season of hearing repairs: passives no longer swap who did what to whom, “must” and “always” and “never” stopped falling out of sentences, and a family of misread questions came home. The mind is the mind; the translator is only a translator.',
    marks: [
      'A clean sentence is never touched — the translator wakes only on a genuine stumble',
      'Every tidied message is verified to mean what the original meant, and the original is kept',
      '“The mouse is chased by the cat” finally means the same as “the cat chases the mouse”',
    ],
  },
  {
    slug: 'own-language',
    seq: 120,
    when: '15 July 2026',
    title: 'It began thinking in its own language',
    body:
      'Until today, every conclusion tokeniko reached had to pass through its own mouth to be believed: reasoned as structure, written out in English, then read back in and re-parsed — a translation at the one moment a mind can least afford one, and it was quietly garbling thoughts on the way through. Now a conclusion is born in its internal representation and stays there. English is what it speaks with you; it is no longer what it thinks in.',
    marks: [
      'Conclusions are assembled directly as structure — the write-back translation is gone from the reasoning loop',
      'The old round trip was caught actively corrupting stored thoughts before it was retired — the evidence came first',
      'English now lives only at the boundary: ears and mouth, never in the middle of a thought',
    ],
  },
  {
    slug: 'the-retreat',
    seq: 110,
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
    slug: 'not-all',
    seq: 100,
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
    slug: 'first-transmission',
    seq: 90,
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
    slug: 'trust',
    seq: 80,
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
    slug: 'the-polite-guest',
    seq: 70,
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
    slug: 'first-conversation',
    seq: 60,
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
    slug: 'theorems-breed-theorems',
    seq: 50,
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
    slug: 'wondering',
    seq: 40,
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
    slug: 'the-cogito',
    seq: 30,
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
    slug: 'the-spine',
    seq: 20,
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
    slug: 'first-words',
    seq: 10,
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

const send = async (method, path, body) => {
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${KEY}`,
    },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`${method} ${path} -> ${res.status}: ${text.slice(0, 200)}`);
  // the SPA server answers ANY route with 200 + index.html (the 2026-07-15 lesson: a seed
  // against the wrong host "succeeded" while writing nothing) — demand the API's JSON envelope.
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new Error(`${method} ${path} -> non-JSON response (wrong host? got: ${text.slice(0, 80)})`);
  }
  if (parsed?.success !== true) throw new Error(`${method} ${path} -> ${text.slice(0, 200)}`);
  return parsed;
};

const main = async () => {
  console.log(`seeding growth content -> ${API_URL}`);
  await send('PUT', '/growth/edge', EDGE);
  console.log(`  edge  «${EDGE.title}»`);
  for (const ring of RINGS) {
    await send('POST', '/growth/rings', ring);
    console.log(`  ring  ${String(ring.seq).padStart(3)}  «${ring.title}»`);
  }
  console.log(`done — ${RINGS.length} rings + the edge.`);
};

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
