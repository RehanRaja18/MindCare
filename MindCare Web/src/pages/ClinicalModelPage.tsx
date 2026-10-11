// ============================================================
// MindCare — Clinical model (for psychologists)
// How care works on MindCare today. Every statement here describes
// behaviour the backend already enforces — keep it that way: update
// this page when the rules change, and don't describe planned features.
// ============================================================

import React from 'react';
import { Link } from 'react-router-dom';
import { Inbox, Users, Sparkles, ShieldCheck, type LucideIcon } from 'lucide-react';
import Navbar from '../components/layout/Navbar';
import Footer from '../components/layout/Footer';
import Button from '../components/common/Button';
import Reveal, { RevealGroup, RevealItem } from '../components/motion/Reveal';
import { ROUTES } from '../constants';

interface ModelSection {
  id: string;
  icon: LucideIcon;
  color: string;
  title: string;
  points: string[];
}

const SECTIONS: ModelSection[] = [
  {
    id: 'requests',
    icon: Inbox,
    color: 'bg-violet-600',
    title: 'How patients reach you',
    points: [
      'Patients find you in the MindCare app’s psychologist directory and send you a request.',
      'Before you answer, you see a pseudonym — not their name — plus age, gender, country, preferred language and time zone.',
      'A request stays open for 3 days, then expires on its own.',
      'If you decline, you can give a reason, and that patient can’t request you again for 30 days.',
      'A patient has one psychologist (or one open request) at a time.',
    ],
  },
  {
    id: 'patients',
    icon: Users,
    color: 'bg-emerald-700',
    title: 'Your patients',
    points: [
      'Once you accept, you see the patient’s real name and contact details.',
      'You see their age, never their exact date of birth.',
      'You can end care at any time with a reason (treatment completed, referred elsewhere, or other). The patient can end it too.',
      'Your “accepting new patients” switch controls whether new requests can reach you. Turning it off doesn’t affect current patients.',
    ],
  },
  {
    id: 'ai',
    icon: Sparkles,
    color: 'bg-orange-500',
    title: 'AI as decision support',
    points: [
      'The anxiety-risk assessment is a tool for you, not for patients: only approved psychologists can use it.',
      'You enter the answers; it returns Low, Medium or High with a confidence level and any warnings.',
      'A result is never shown to the patient, and nothing you enter is saved.',
      'It supports ages 18–49. Every result needs your clinical review — a confident result doesn’t mean the patient is safe.',
    ],
  },
  {
    id: 'safety',
    icon: ShieldCheck,
    color: 'bg-blue-950',
    title: 'Verification and privacy',
    points: [
      'Every psychologist account is reviewed by a MindCare admin. You can sign in only after your account is approved.',
      'You only ever see your own requests and patients.',
      'Every patient gets an automatic pseudonym (like “Patient-3fa2c1”), so their identity stays private until they’re in your care.',
    ],
  },
];

const ClinicalModelPage: React.FC = () => (
  <div className="min-h-screen mc-page-glow flex flex-col">
    <Navbar
      cta={{ label: 'Apply to practice →', to: ROUTES.THERAPIST_REGISTER }}
      secondary={{ label: 'Sign in', to: ROUTES.THERAPIST_LOGIN }}
    />

    <main className="flex-1 max-w-5xl mx-auto w-full px-4 sm:px-6 pt-32 pb-16">
      <Reveal>
        <p className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-6">For therapists · Clinical model</p>
        <h1 className="text-4xl sm:text-6xl font-black text-gray-900 leading-[1.05] mb-6">
          How care works <span className="italic font-serif font-normal">on MindCare.</span>
        </h1>
        <p className="text-gray-600 text-lg leading-relaxed max-w-2xl mb-14">
          From a patient’s first request to ending care — what you see, what you decide, and where the AI fits in.
        </p>
      </Reveal>

      <RevealGroup className="grid grid-cols-1 md:grid-cols-2 gap-5" stagger={0.1}>
        {SECTIONS.map((section, i) => {
          const Icon = section.icon;
          return (
            <RevealItem key={section.id}>
              <section
                aria-labelledby={`cm-${section.id}`}
                className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 sm:p-7 h-full"
              >
                <div className="flex items-center gap-3 mb-4">
                  <span className={`w-11 h-11 rounded-xl flex items-center justify-center text-white shrink-0 ${section.color}`}>
                    <Icon size={20} aria-hidden="true" />
                  </span>
                  <h2 id={`cm-${section.id}`} className="text-lg font-bold text-gray-900">
                    <span className="text-gray-400 font-semibold mr-1.5">{i + 1}.</span>
                    {section.title}
                  </h2>
                </div>
                <ul className="space-y-2.5">
                  {section.points.map((point) => (
                    <li key={point} className="flex gap-3 text-sm text-gray-700 leading-relaxed">
                      <span className="w-1.5 h-1.5 rounded-full bg-gray-400 mt-2 shrink-0" aria-hidden="true" />
                      <span>{point}</span>
                    </li>
                  ))}
                </ul>
              </section>
            </RevealItem>
          );
        })}
      </RevealGroup>

      <Reveal delay={0.1}>
        <div className="flex flex-wrap gap-4 mt-14">
          <Link to={ROUTES.THERAPIST_REGISTER}>
            <Button variant="primary" size="lg">
              Apply to practice →
            </Button>
          </Link>
          <Link to={ROUTES.FOR_THERAPISTS}>
            <Button variant="secondary" size="lg">
              Back to For therapists
            </Button>
          </Link>
        </div>
      </Reveal>
    </main>

    <Footer />
  </div>
);

export default ClinicalModelPage;
