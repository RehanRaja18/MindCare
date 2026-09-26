// ============================================================
// MindCare — About Us Page ("Built by people who had to look for care.")
// ============================================================

import React, { useCallback, useState } from 'react';
import { motion } from 'framer-motion';
import { User } from 'lucide-react';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';
import Reveal, { RevealGroup, RevealItem } from '../components/motion/Reveal';
import ContactModal from '../components/contact/ContactModal';
import { ABOUT_INTRO, ABOUT_VALUES, ABOUT_TIMELINE, TEAM_MEMBERS } from '../constants';

const AboutUsPage: React.FC = () => {
  const [contactOpen, setContactOpen] = useState(false);
  const closeContact = useCallback(() => setContactOpen(false), []);

  return (
    <div className="min-h-screen mc-page-glow">
      <Navbar />

      <main className="pt-16 grid grid-cols-1 lg:grid-cols-2">
        {/* Left — story */}
        <div className="px-4 sm:px-6 lg:px-16 pt-24 pb-24">
          <Reveal>
            <p className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-6">About us</p>

            <h1 className="text-4xl sm:text-6xl font-black text-gray-900 leading-[1.05] mb-8">
              Built by people who had to <span className="italic font-serif font-normal">look</span>
              <br />
              for care, and didn&apos;t always <span className="italic font-serif font-normal">find</span> it.
            </h1>

            <p className="text-gray-600 text-lg leading-relaxed max-w-xl mb-12">{ABOUT_INTRO}</p>

            <h2 className="text-xs font-bold tracking-widest text-gray-900 uppercase mb-6">Our path</h2>
          </Reveal>
          <motion.ol
            className="space-y-6"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.2 }}
            variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.08 } } }}
          >
            {ABOUT_TIMELINE.map((entry) => (
              <motion.li
                key={entry.id}
                className="flex gap-4"
                variants={{
                  hidden: { opacity: 0, y: 20 },
                  visible: { opacity: 1, y: 0, transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] } },
                }}
              >
                <span className="flex flex-col items-center pt-1.5 shrink-0">
                  <span
                    className={`w-2.5 h-2.5 rounded-full ${entry.current ? 'bg-orange-500' : 'bg-gray-900'}`}
                    aria-hidden="true"
                  />
                  <span className="w-px flex-1 bg-gray-200 mt-1" aria-hidden="true" />
                </span>
                <div className="pb-1">
                  <p className="text-sm text-gray-500 mb-0.5">{entry.date}</p>
                  <p className="text-gray-900 font-medium">{entry.description}</p>
                </div>
              </motion.li>
            ))}
          </motion.ol>
        </div>

        {/* Right — values + team */}
        <div className="px-4 sm:px-6 lg:px-16 pt-24 pb-24 bg-[#EFE9DF] flex flex-col">
          <Reveal>
            <p className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-6">
              Values we&apos;re trying to hold
            </p>
          </Reveal>

          <RevealGroup className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-14" stagger={0.08}>
            {ABOUT_VALUES.map((value) => (
              <RevealItem key={value.id}>
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 h-full">
                  <p className="font-bold text-gray-900 mb-1">{value.title}</p>
                  <p className="text-sm text-gray-500 leading-relaxed">{value.description}</p>
                </div>
              </RevealItem>
            ))}
          </RevealGroup>

          <Reveal>
            <p className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-4">The team</p>
          </Reveal>
          <RevealGroup className="space-y-3 mb-auto" stagger={0.08}>
            {TEAM_MEMBERS.map((member) => (
              <RevealItem key={member.id}>
                <div className="flex items-center gap-3">
                  {member.photoUrl ? (
                    <img src={member.photoUrl} alt={member.name} className="w-10 h-10 rounded-full object-cover" />
                  ) : (
                    <span className="w-10 h-10 rounded-full bg-gray-900 flex items-center justify-center shrink-0" aria-hidden="true">
                      <User size={16} className="text-white/80" strokeWidth={1.75} />
                    </span>
                  )}
                  <div>
                    <p className="text-sm font-bold text-gray-900">{member.name}</p>
                    <p className="text-xs text-gray-500">{member.role}</p>
                  </div>
                </div>
              </RevealItem>
            ))}
          </RevealGroup>

          <Reveal>
          <div className="flex flex-wrap gap-3 mt-10">
            <button
              type="button"
              onClick={() => setContactOpen(true)}
              className="bg-gray-900 text-white text-sm font-semibold px-5 py-3 rounded-full hover:bg-gray-800 transition-colors"
            >
              Contact
            </button>
          </div>
          </Reveal>
        </div>
      </main>

      <Footer />

      <ContactModal open={contactOpen} onClose={closeContact} />
    </div>
  );
};

export default AboutUsPage;