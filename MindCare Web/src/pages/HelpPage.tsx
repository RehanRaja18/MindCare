// ============================================================
// MindCare — Help Center Page ("How can we help?")
// ============================================================

import React, { useCallback, useState } from 'react';
import { Link } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { ChevronDown, Mail, Phone } from 'lucide-react';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';
import Reveal from '../components/motion/Reveal';
import ContactModal from '../components/contact/ContactModal';
import { HELP_TOP_QUESTIONS, HELP_CRISIS_PHONE, HELP_CRISIS_PHONE_TEL, ROUTES } from '../constants';

const HelpPage: React.FC = () => {
  const [openId, setOpenId] = useState<string | null>(null);
  const [contactOpen, setContactOpen] = useState(false);
  const closeContact = useCallback(() => setContactOpen(false), []);

  return (
    <div className="min-h-screen mc-page-glow">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-32 pb-24 grid grid-cols-1 lg:grid-cols-2 gap-10">
        {/* Left column — intro + crisis support */}
        <div>
          <Reveal>
            <p className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-6">Help center</p>
            <h1 className="text-4xl sm:text-6xl font-black text-gray-900 leading-[1.05] mb-6">
              How can we <span className="italic font-serif font-normal">help?</span>
            </h1>
            <p className="text-gray-600 text-lg mb-10 max-w-md">
              Find answers to the questions we hear most, or send us a message and our team will get back to you.
            </p>
          </Reveal>

          <Reveal delay={0.1}>
            <div className="bg-orange-50 border border-orange-200 rounded-2xl p-6 sm:p-8">
              <p className="text-xs font-semibold tracking-widest text-orange-600 uppercase mb-4 flex items-center gap-2">
                ⚠ If you need help right now
              </p>
              <h2 className="text-2xl font-black text-gray-900 mb-3">Crisis support, free, 24/7.</h2>
              <p className="text-gray-700 leading-relaxed mb-6">
                If you or someone you love is in danger, please call Umang. A trained human picks up
                in under 90 seconds.
              </p>
              <div className="flex flex-wrap gap-3">
                <a
                  href={HELP_CRISIS_PHONE_TEL}
                  className="inline-flex items-center gap-2 bg-red-600 text-white text-sm font-semibold px-5 py-3 rounded-full hover:bg-red-700 transition-colors"
                >
                  <Phone size={15} aria-hidden="true" /> Call Umang · {HELP_CRISIS_PHONE}
                </a>
                <Link
                  to={ROUTES.CLIENT_APP}
                  className="bg-white border border-gray-200 text-gray-900 text-sm font-semibold px-5 py-3 rounded-full hover:border-gray-400 transition-colors"
                >
                  Tap SOS in the app
                </Link>
              </div>
            </div>
          </Reveal>
        </div>

        {/* Right column — top questions + email */}
        <div>
          <Reveal delay={0.1}>
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 sm:p-8">
              <p className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-1">Top questions</p>
              <h3 className="text-lg font-bold text-gray-900 mb-3">The 5 we get most</h3>

              <ol className="divide-y divide-gray-100">
                {HELP_TOP_QUESTIONS.map((q, i) => {
                  const open = openId === q.id;
                  const panelId = `faq-panel-${q.id}`;
                  return (
                    <li key={q.id}>
                      <button
                        type="button"
                        onClick={() => setOpenId(open ? null : q.id)}
                        aria-expanded={open}
                        aria-controls={panelId}
                        className="w-full flex items-center justify-between gap-4 py-4 text-left group"
                      >
                        <span className="flex items-baseline gap-4">
                          <span className="text-sm text-gray-400 font-mono">{String(i + 1).padStart(2, '0')}</span>
                          <span className="text-gray-800 font-medium group-hover:text-gray-900">{q.question}</span>
                        </span>
                        <ChevronDown
                          size={16}
                          aria-hidden="true"
                          className={`shrink-0 transition-transform duration-300 ${
                            open ? 'rotate-180 text-gray-900' : 'text-gray-400'
                          }`}
                        />
                      </button>

                      <AnimatePresence initial={false}>
                        {open && (
                          <motion.div
                            id={panelId}
                            role="region"
                            aria-label={q.question}
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                            className="overflow-hidden"
                          >
                            <div className="pl-9 pb-5 space-y-3 text-sm text-gray-600 leading-relaxed">
                              {q.answer.map((para) => (
                                <p key={para}>{para}</p>
                              ))}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </li>
                  );
                })}
              </ol>

              <div className="mt-4 pt-6 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => setContactOpen(true)}
                  className="w-full flex items-center gap-4 rounded-2xl bg-[#F7F3EC] hover:bg-[#EFE9DF] p-4 text-left transition-colors"
                >
                  <span className="w-11 h-11 rounded-full bg-white flex items-center justify-center shrink-0 shadow-sm">
                    <Mail size={18} aria-hidden="true" />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold text-gray-900">Email us</span>
                    <span className="block text-xs text-gray-500">
                      Didn&apos;t find your answer? Send a message and we&apos;ll reply by email.
                    </span>
                  </span>
                </button>
              </div>
            </div>
          </Reveal>
        </div>
      </main>

      <Footer />

      <ContactModal open={contactOpen} onClose={closeContact} />
    </div>
  );
};

export default HelpPage;
