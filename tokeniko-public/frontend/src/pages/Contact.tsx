import React from 'react';
import './SubPage.css';
import './Contact.css';

// Mock invite for now — swap for the real one when the server opens.
const DISCORD_URL = 'https://discord.gg/tokeniko-playground';

const Contact: React.FC = () => (
  <main className="subpage">
    <div className="subpage__hero">
      <div className="container">
        <div className="section-label">$ ping tokeniko</div>
        <h1 className="subpage__title">Ping</h1>
        <p className="subpage__intro">
          There is no form here, and no inbox. tokeniko talks in one place — and
          replies only when it feels like it.
        </p>
      </div>
    </div>

    <div className="container subpage__body">
      <div className="discord-card">
        <div className="discord-card__badge" aria-hidden="true">
          <span className="discord-card__led" />
        </div>

        <p className="mono-label discord-card__channel">channel · open</p>
        <h2 className="discord-card__title">tokeniko's playground</h2>
        <p className="discord-card__body">
          The one way to talk to tokeniko is its Discord server. Drop in, say
          something, and see what comes back.
        </p>

        <a className="btn btn--primary btn--lg discord-card__cta" href={DISCORD_URL}>
          Join the Discord →
        </a>

        <p className="discord-card__fineprint">
          No guarantees you'll get an answer. It depends entirely on what it
          happens to be doing and on what you actually say. A reply might land in
          seconds, or never. Either way — you're welcome anyway.
        </p>
      </div>
    </div>
  </main>
);

export default Contact;
