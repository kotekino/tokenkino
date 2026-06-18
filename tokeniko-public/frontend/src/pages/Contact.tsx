import React, { useState } from 'react';
import { ContactFormData } from '../types';
import './SubPage.css';
import './Contact.css';

type Status = 'idle' | 'loading' | 'success' | 'error';

const Contact: React.FC = () => {
  const [form, setForm] = useState<ContactFormData>({ name: '', email: '', message: '' });
  const [status, setStatus] = useState<Status>('idle');
  const [error, setError] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('loading');
    setError('');

    try {
      const apiUrl = import.meta.env.VITE_API_URL || '/api';
      const res = await fetch(`${apiUrl}/contact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      const data = await res.json();

      if (!res.ok) throw new Error(data.message || 'Something went wrong');

      setStatus('success');
      setForm({ name: '', email: '', message: '' });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. Please try again.');
      setStatus('error');
    }
  };

  return (
    <main className="subpage">
      <div className="subpage__hero">
        <div className="container">
          <div className="section-label">Say hello</div>
          <h1 className="subpage__title">Contact</h1>
          <p className="subpage__intro">
            Have a project in mind? We'd love to hear about it.
          </p>
        </div>
      </div>

      <div className="container subpage__body">
        <div className="contact-layout">
          <div className="contact-info">
            <h2>Let's talk</h2>
            <p>
              Whether you have a fully-formed brief or just an idea you'd like to explore, we're happy
              to jump on a call and see if there's a fit.
            </p>
            <dl className="contact-details">
              <div>
                <dt>Email</dt>
                <dd><a href="mailto:hello@yourbrand.com">hello@yourbrand.com</a></dd>
              </div>
              <div>
                <dt>Response time</dt>
                <dd>Within 1 business day</dd>
              </div>
              <div>
                <dt>Location</dt>
                <dd>Osaka, Japan · EU-based servers</dd>
              </div>
            </dl>
          </div>

          <div className="contact-form-wrap">
            {status === 'success' ? (
              <div className="contact-success" role="alert">
                <div className="contact-success__icon">✓</div>
                <h3>Message sent!</h3>
                <p>Thank you for reaching out. We'll get back to you shortly.</p>
                <button className="btn btn--outline" onClick={() => setStatus('idle')}>
                  Send another message
                </button>
              </div>
            ) : (
              <form className="contact-form" onSubmit={handleSubmit} noValidate>
                {status === 'error' && (
                  <div className="form-error" role="alert">
                    {error}
                  </div>
                )}

                <div className="form-group">
                  <label htmlFor="name" className="form-label">Full name</label>
                  <input
                    id="name"
                    name="name"
                    type="text"
                    className="form-input"
                    value={form.name}
                    onChange={handleChange}
                    placeholder="Jane Smith"
                    required
                    autoComplete="name"
                    disabled={status === 'loading'}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="email" className="form-label">Email address</label>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    className="form-input"
                    value={form.email}
                    onChange={handleChange}
                    placeholder="jane@example.com"
                    required
                    autoComplete="email"
                    disabled={status === 'loading'}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="message" className="form-label">Message</label>
                  <textarea
                    id="message"
                    name="message"
                    className="form-input form-input--textarea"
                    value={form.message}
                    onChange={handleChange}
                    placeholder="Tell us about your project..."
                    required
                    rows={5}
                    disabled={status === 'loading'}
                  />
                </div>

                <p className="form-privacy">
                  By submitting this form, you agree to our{' '}
                  <a href="/legal/privacy">Privacy Policy</a>. We will never share your data.
                </p>

                <button
                  type="submit"
                  className="btn btn--primary btn--submit"
                  disabled={status === 'loading'}
                >
                  {status === 'loading' ? 'Sending…' : 'Send message'}
                </button>
              </form>
            )}
          </div>
        </div>
      </div>
    </main>
  );
};

export default Contact;
