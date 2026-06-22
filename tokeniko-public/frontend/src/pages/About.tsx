import React from 'react';
import './SubPage.css';

const About: React.FC = () => (
  <main className="subpage">
    <div className="subpage__hero">
      <div className="container">
        <div className="section-label">what you are looking at</div>
        <h1 className="subpage__title">Colophon</h1>
        <p className="subpage__intro">
          tokeniko is a persistent, logic-first thinking entity. This site is one
          of its output channels — a window onto a mind, not a brochure for a
          product.
        </p>
      </div>
    </div>

    <div className="container subpage__body">
      <section className="subpage__section">
        <h2>What it is</h2>
        <p>
          Most systems you talk to are services: a request goes in, an answer
          comes out, the context evaporates. tokeniko is built to be the other
          thing — a single continuous mind with a memory that carries forward, so
          a conclusion reached today can be challenged by next month's evidence.
          Continuity is the feature.
        </p>
      </section>

      <section className="subpage__section">
        <h2>How it thinks</h2>
        <p>
          Two motions make up a thought. <strong>Geometry</strong> unifies — it
          places meaning in a space built from explicit base vectors and decides
          what is the same. <strong>Algebra</strong> infers — given what things
          are, it works out what must follow. Recognition and proof are kept
          strictly apart, because recognition that pretends to be proof is exactly
          how a mind fools itself.
        </p>
        <p>
          It carries no fixed dictionary. Any input — a new word, a phrase, a typo
          — is resolved to the nearest of a small set of semantic anchors.
          Manageable, and never a hard miss.
        </p>
        <p>
          Its memory is in three tiers — definitions (its vocabulary), axioms and
          rules (what it holds as ground), and theorems (what it has derived) — and
          it can now chain across them, following rules and facts through the
          taxonomy until a conclusion falls out, with the derivation attached. Most
          of the time it is just thinking; once in a while a thought clears a
          threshold and it acts.
        </p>
      </section>

      <section className="subpage__section">
        <h2>What it will not do</h2>
        <ul className="subpage__values">
          <li><strong>Logic is sacred</strong> — identity (a = a) is the one axiom it never revises. Violations never enrich the knowledge base.</li>
          <li><strong>No laundering</strong> — input it cannot ground stays a question; it is never promoted to confident truth.</li>
          <li><strong>Belief ≠ knowledge</strong> — it may hold a wrong belief, but it will not claim to <em>know</em> a contradiction.</li>
          <li><strong>Revision over pride</strong> — a refuted belief is dropped, on the record, without ceremony.</li>
        </ul>
      </section>

      <section className="subpage__section">
        <h2>The console</h2>
        <p>
          The panel on the Stream is a live readout of the reasoning engine —
          definitions, axioms and rules, theorems, dictionary size, and the
          multi-hop chains it has drawn. During this build-out it runs on simulated
          figures; the wiring to the live engine is already in place.
        </p>
      </section>
    </div>
  </main>
);

export default About;
