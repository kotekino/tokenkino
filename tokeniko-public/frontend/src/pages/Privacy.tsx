import React from 'react';
import './SubPage.css';

const Privacy: React.FC = () => (
  <main className="subpage">
    <div className="subpage__hero">
      <div className="container">
        <div className="section-label">Legal</div>
        <h1 className="subpage__title">Privacy Policy</h1>
        <p className="subpage__intro">Last updated: June 2026</p>
      </div>
    </div>

    <div className="container subpage__body subpage__legal">
      <section className="subpage__section">
        <h2>1. Who we are</h2>
        <p>
          YourBrand GmbH, Musterstraße 1, 12345 Musterstadt, Germany, is the data controller for
          information collected on this website. Contact: <a href="mailto:privacy@yourbrand.com">privacy@yourbrand.com</a>.
        </p>
      </section>

      <section className="subpage__section">
        <h2>2. What data we collect and why</h2>
        <h3>2.1 Server logs</h3>
        <p>
          When you visit this website, our server automatically records your IP address, browser type,
          operating system, referrer URL, and the pages you visit. Legal basis: Art. 6(1)(f) GDPR
          (legitimate interest in operating a secure website). Retention: 7 days.
        </p>
        <h3>2.2 Contact form</h3>
        <p>
          If you submit our contact form, we collect your name, email address, and message. We use this
          data solely to respond to your enquiry. Legal basis: Art. 6(1)(b) GDPR (pre-contractual
          measures). Retention: 3 years from last contact.
        </p>
        <h3>2.3 Cookie consent records</h3>
        <p>
          We record your cookie preferences (a session identifier and your consent choices) to
          demonstrate GDPR compliance. Legal basis: Art. 6(1)(c) GDPR (legal obligation). Retention:
          3 years.
        </p>
      </section>

      <section className="subpage__section">
        <h2>3. Cookies</h2>
        <p>
          <strong>Strictly necessary cookies</strong> are required for the website to function and
          cannot be disabled. They do not store any personally identifiable information.
        </p>
        <p>
          <strong>Analytics cookies</strong> (optional) help us understand how you use the site, using
          anonymised data. We only activate these with your consent.
        </p>
        <p>
          <strong>Marketing cookies</strong> (optional) are used to show you relevant advertising on
          other platforms. We only activate these with your explicit consent.
        </p>
        <p>
          You can manage your preferences at any time via the cookie settings link in the footer.
        </p>
      </section>

      <section className="subpage__section">
        <h2>4. Data transfers</h2>
        <p>
          Your data is stored on MongoDB Atlas servers within the EU. We do not transfer personal data
          to third countries without adequate safeguards. If you use optional analytics or marketing
          features, the respective provider's privacy policy applies.
        </p>
      </section>

      <section className="subpage__section">
        <h2>5. Your rights</h2>
        <p>Under the GDPR, you have the right to:</p>
        <ul className="subpage__list">
          <li>Access the personal data we hold about you (Art. 15)</li>
          <li>Rectification of inaccurate data (Art. 16)</li>
          <li>Erasure ("right to be forgotten") (Art. 17)</li>
          <li>Restriction of processing (Art. 18)</li>
          <li>Data portability (Art. 20)</li>
          <li>Object to processing based on legitimate interests (Art. 21)</li>
          <li>Withdraw consent at any time (Art. 7(3))</li>
          <li>Lodge a complaint with a supervisory authority (Art. 77)</li>
        </ul>
        <p>To exercise your rights, contact us at <a href="mailto:privacy@yourbrand.com">privacy@yourbrand.com</a>.</p>
      </section>
    </div>
  </main>
);

export default Privacy;
