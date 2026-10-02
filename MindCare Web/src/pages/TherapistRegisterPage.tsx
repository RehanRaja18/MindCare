// ============================================================
// MindCare — Therapist Registration Page ("Let's get you verified.")
// Page shell around the reusable registration wizard.
// ============================================================

import React from 'react';
import { Link } from 'react-router-dom';
import TherapistRegisterWizard from '../components/therapist/TherapistRegisterWizard';
import { ROUTES, THERAPIST_WHAT_HAPPENS_NEXT, THERAPIST_STATS } from '../constants';

const TherapistRegisterPage: React.FC = () => (
  <div className="min-h-screen bg-[#F5F0E8]">
    {/* Header */}
    <header className="flex items-center justify-between gap-4 px-4 sm:px-10 py-6">
      <Link to={ROUTES.HOME} className="text-xl font-bold tracking-tight text-gray-900 shrink-0">
        MindCare<span className="text-orange-500">.</span>
      </Link>
      <p className="text-sm text-gray-500 text-right">
        Already a therapist here?{' '}
        <Link to={ROUTES.THERAPIST_LOGIN} className="font-semibold text-gray-900 underline underline-offset-2">
          Sign in
        </Link>
      </p>
    </header>

    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24 grid grid-cols-1 lg:grid-cols-3 gap-10">
      <div className="lg:col-span-2">
        <p className="text-xs font-semibold tracking-widest text-gray-500 uppercase mb-4">
          Therapist · Apply to practice
        </p>
        <h1 className="text-4xl sm:text-5xl font-black text-gray-900 mb-4">
          Let&apos;s get you <span className="italic font-serif font-normal">verified.</span>
        </h1>
        <p className="text-gray-600 max-w-xl mb-8">
          MindCare only accepts licensed clinicians. After you apply, an admin reviews your details
          before your account is activated.
        </p>

        <TherapistRegisterWizard />
      </div>

      {/* Right sidebar */}
      <aside className="space-y-6">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
          <h3 className="text-xs font-bold tracking-widest text-gray-500 uppercase mb-5">What happens next</h3>
          <ol className="space-y-5">
            {THERAPIST_WHAT_HAPPENS_NEXT.map((item, i) => (
              <li key={item.id} className="flex gap-4">
                <span
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                    i === 0 ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-500'
                  }`}
                >
                  {i + 1}
                </span>
                <div>
                  <p className="text-sm font-bold text-gray-900">{item.title}</p>
                  <p className="text-xs text-gray-500">{item.meta}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>

        <div className="bg-gray-900 rounded-2xl p-6">
          <p className="text-xs font-semibold tracking-widest text-orange-400 uppercase mb-4">Why therapists join</p>
          <p className="text-3xl font-black text-white mb-3">{THERAPIST_STATS[0].value} take-home</p>
          <p className="text-sm text-gray-400 leading-relaxed">
            One of the most generous splits anywhere. You set your own session price.
          </p>
        </div>
      </aside>
    </main>
  </div>
);

export default TherapistRegisterPage;
