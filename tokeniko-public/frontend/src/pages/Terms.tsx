import React from 'react';
import './SubPage.css';

const Terms: React.FC = () => (
  <main className="subpage">
    <div className="subpage__hero">
      <div className="container">
        <div className="section-label">Legal</div>
        <h1 className="subpage__title">Terms of Service</h1>
        <p className="subpage__intro">Last updated: June 2026</p>
      </div>
    </div>

    <div className="container subpage__body subpage__legal">
      <section className="subpage__section">
        <h2>1. Acceptance of terms</h2>
        <p>
          By accessing and using this website, you accept and agree to be bound by these Terms of
          Service. If you do not agree, please do not use this website.
        </p>
      </section>
      <section className="subpage__section">
        <h2>2. Use of the website</h2>
        <p>
          You agree to use this website only for lawful purposes and in a manner that does not infringe
          the rights of others. Automated scraping, spam, or abuse of any API endpoints is prohibited.
        </p>
      </section>
      <section className="subpage__section">
        <h2>3. Intellectual property</h2>
        <p>
          All content on this website, including text, graphics, logos, and code, is the property of
          YourBrand GmbH or its content suppliers and is protected by applicable intellectual property
          laws.
        </p>
      </section>
      <section className="subpage__section">
        <h2>4. Limitation of liability</h2>
        <p>
          To the fullest extent permitted by law, YourBrand GmbH shall not be liable for any indirect,
          incidental, special, or consequential damages arising from your use of, or inability to use,
          this website.
        </p>
      </section>
      <section className="subpage__section">
        <h2>5. Governing law</h2>
        <p>
          These terms are governed by German law. Disputes shall be subject to the exclusive
          jurisdiction of the courts of Musterstadt, Germany.
        </p>
      </section>
      <section className="subpage__section">
        <h2>6. Changes to these terms</h2>
        <p>
          We may update these terms from time to time. Continued use of the website after changes
          constitutes acceptance of the new terms.
        </p>
      </section>
    </div>
  </main>
);

export default Terms;
