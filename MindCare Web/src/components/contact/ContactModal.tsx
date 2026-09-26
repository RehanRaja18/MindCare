// ============================================================
// MindCare — "Contact us" dialog (About page)
// ============================================================

import React, { useEffect, useRef, useState } from 'react';
import { CheckCircle2, Phone } from 'lucide-react';
import Button from '../common/Button';
import Sheet, { sheetInputClass as inputClass } from '../common/Sheet';
import { sendContactMessage } from '../../services/api.service';
import { validateEmail } from '../../utils/validation';
import { CONTACT_EMAIL, HELP_CRISIS_PHONE, HELP_CRISIS_PHONE_TEL } from '../../constants';
import { cn } from '../../utils/cn';

interface ContactModalProps {
  open: boolean;
  onClose: () => void;
}

const TOPICS = ['General question', 'Therapy & sessions', 'Partnerships', 'Press', 'Feedback'];
const MIN_CHARS = 10;
const MAX_CHARS = 1000;

const ContactModal: React.FC<ContactModalProps> = ({ open, onClose }) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [topic, setTopic] = useState(TOPICS[0]);
  const [message, setMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const firstFieldRef = useRef<HTMLInputElement>(null);

  // Reset the form each time the dialog opens
  useEffect(() => {
    if (!open) return;
    setName('');
    setEmail('');
    setTopic(TOPICS[0]);
    setMessage('');
    setError(null);
    setDone(false);
    const t = setTimeout(() => firstFieldRef.current?.focus(), 150);
    return () => clearTimeout(t);
  }, [open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return setError('Please tell us your name.');
    const emailError = validateEmail(email);
    if (emailError) return setError(emailError);
    if (message.trim().length < MIN_CHARS) return setError(`Please write at least ${MIN_CHARS} characters.`);

    setError(null);
    setSubmitting(true);
    const payload = { name: name.trim(), email: email.trim().toLowerCase(), topic, message: message.trim() };
    const res = await sendContactMessage(payload);
    setSubmitting(false);
    if (res.error) return setError(res.error);

    // Once the official inbox exists, also hand off to the visitor's mail app
    if (CONTACT_EMAIL) {
      const subject = encodeURIComponent(`[MindCare] ${payload.topic}`);
      const body = encodeURIComponent(`${payload.message}\n\n— ${payload.name} (${payload.email})`);
      window.location.href = `mailto:${CONTACT_EMAIL}?subject=${subject}&body=${body}`;
    }
    setDone(true);
  };

  return (
    <Sheet open={open} onClose={onClose} labelledBy="contact-title">
      {done ? (
        <div className="px-6 sm:px-8 py-12 text-center">
          <CheckCircle2 size={44} className="mx-auto text-emerald-500 mb-4" aria-hidden="true" />
          <h2 id="contact-title" className="text-2xl font-black text-gray-900 mb-3">
            Message received.
          </h2>
          <p className="text-sm text-gray-600 leading-relaxed max-w-sm mx-auto mb-8">
            Thank you for reaching out. Our team will reply to <strong>{email.trim()}</strong> within
            2 working days.
          </p>
          <Button variant="primary" size="md" onClick={onClose} className="rounded-full">
            Done
          </Button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} noValidate className="px-6 sm:px-8 pt-6 sm:pt-8 pb-6">
          <p className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-2">Contact</p>
          <h2 id="contact-title" className="text-2xl sm:text-3xl font-black text-gray-900 leading-tight mb-4 pr-8">
            Talk to <span className="italic font-serif font-normal">the team.</span>
          </h2>

          {/* Not a crisis channel — point people in distress to the helpline */}
          <a
            href={HELP_CRISIS_PHONE_TEL}
            className="flex items-start gap-3 rounded-xl bg-rose-50 border border-rose-100 p-3.5 mb-6 text-xs text-rose-800 leading-relaxed hover:bg-rose-100/70 transition-colors"
          >
            <Phone size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
            <span>
              In crisis or need help right now? Don&apos;t wait for an email. Call our helpline{' '}
              <strong className="whitespace-nowrap">{HELP_CRISIS_PHONE}</strong>.
            </span>
          </a>

          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="contact-name" className="block text-sm font-semibold text-gray-800 mb-1.5">
                  Name
                </label>
                <input
                  id="contact-name"
                  ref={firstFieldRef}
                  value={name}
                  onChange={(e) => setName(e.target.value.slice(0, 60))}
                  autoComplete="name"
                  className={inputClass}
                  required
                />
              </div>
              <div>
                <label htmlFor="contact-email" className="block text-sm font-semibold text-gray-800 mb-1.5">
                  Email
                </label>
                <input
                  id="contact-email"
                  type="email"
                  inputMode="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  placeholder="you@example.com"
                  className={inputClass}
                  required
                />
              </div>
            </div>

            <fieldset>
              <legend className="block text-sm font-semibold text-gray-800 mb-2">What&apos;s it about?</legend>
              <div className="flex flex-wrap gap-2">
                {TOPICS.map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setTopic(t)}
                    aria-pressed={topic === t}
                    className={cn(
                      'px-3.5 py-1.5 rounded-full border text-sm transition-colors',
                      topic === t
                        ? 'bg-gray-900 border-gray-900 text-white'
                        : 'bg-white border-gray-200 text-gray-700 hover:border-gray-400'
                    )}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </fieldset>

            <div>
              <label htmlFor="contact-message" className="block text-sm font-semibold text-gray-800 mb-1.5">
                Message
              </label>
              <textarea
                id="contact-message"
                value={message}
                onChange={(e) => setMessage(e.target.value.slice(0, MAX_CHARS))}
                rows={5}
                placeholder="How can we help?"
                className={cn(inputClass, 'resize-none')}
                required
              />
              <p className="mt-1 text-right text-xs text-gray-400">
                {message.length}/{MAX_CHARS}
              </p>
            </div>
          </div>

          {error && (
            <p role="alert" className="mt-4 text-sm text-rose-600">
              {error}
            </p>
          )}

          <div className="mt-6 flex flex-col-reverse sm:flex-row sm:justify-end gap-3">
            <Button type="button" variant="ghost" size="md" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="md" loading={submitting}>
              Send message
            </Button>
          </div>
        </form>
      )}
    </Sheet>
  );
};

export default ContactModal;
