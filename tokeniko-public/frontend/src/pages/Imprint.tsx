import React from 'react';
import './SubPage.css';

const Imprint: React.FC = () => (
  <main className="subpage">
    <div className="subpage__hero">
      <div className="container">
        <div className="section-label">Legal</div>
        <h1 className="subpage__title">Imprint</h1>
        <p className="subpage__intro">
          Mandatory provider identification (§ 5 TMG / EU Directive 2000/31/EC)
        </p>
      </div>
    </div>

    <div className="container subpage__body subpage__legal">
      <section className="subpage__section">
        <h2>Company information</h2>
        <address>
          <strong>YourBrand GmbH</strong><br />
          Musterstraße 1<br />
          12345 Musterstadt<br />
          Germany
        </address>
      </section>

      <section className="subpage__section">
        <h2>Contact</h2>
        <p>Email: <a href="mailto:legal@yourbrand.com">legal@yourbrand.com</a></p>
        <p>Phone: +49 (0) 000 000 000</p>
      </section>

      <section className="subpage__section">
        <h2>Legal representatives</h2>
        <p>Managing Director: Max Mustermann</p>
      </section>

      <section className="subpage__section">
        <h2>Commercial register</h2>
        <p>Register court: Amtsgericht Musterstadt</p>
        <p>Register number: HRB 000000</p>
        <p>VAT ID (§ 27 a UStG): DE000000000</p>
      </section>

      <section className="subpage__section">
        <h2>Dispute resolution</h2>
        <p>
          The European Commission provides a platform for online dispute resolution (ODR):{' '}
          <a href="https://ec.europa.eu/consumers/odr/" target="_blank" rel="noopener noreferrer">
            https://ec.europa.eu/consumers/odr/
          </a>
        </p>
        <p>
          We are not obligated to participate in dispute resolution proceedings before a consumer
          arbitration body and do not voluntarily participate.
        </p>
      </section>

      <section className="subpage__section">
        <h2>Liability for content</h2>
        <p>
          As a service provider, we are responsible for our own content on these pages in accordance
          with general law. We are not obligated to monitor transmitted or stored third-party information
          or to investigate circumstances that indicate illegal activity.
        </p>
      </section>
    </div>
  </main>
);

export default Imprint;
