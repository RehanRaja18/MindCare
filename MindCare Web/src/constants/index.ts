// ============================================================
// MindCare — App-wide Constants (swap URLs for real API later)
// ============================================================

import type {
  NavItem,
  Feature,
  HowItWorksStep,
  Partner,
  Stat,
  PlatformStats,
  MoodEntry,
  StoryEntry,
  NGOPartnerEntry,
  TherapistFeature,
  AboutValueCard,
  AboutTimelineEntry,
  HelpTopQuestion,
  HelpGuide,
  PricingFeatureStrip,
  LegalSection,
  TeamMember,
} from '../types';

export const APP_NAME = 'MindCare';
export const APP_TAGLINE = 'A quieter mind is the work of a year, not a download.';

// ——— Navigation ———
export const NAV_ITEMS: NavItem[] = [
  { label: 'How it works', href: '/#how-it-works' },
  { label: 'For therapists', href: '/for-therapists' },
  { label: 'For NGOs', href: '/for-ngos' },
  { label: 'Stories', href: '/stories' },
  { label: 'Pricing', href: '/pricing' },
  { label: 'About us', href: '/about' },
  { label: 'Help', href: '/help' },
];

// ——— Landing page stats ———
// Values are live from the backend (see usePlatformStats); only labels live here.
export const HERO_STATS: { key: keyof PlatformStats; label: string }[] = [
  { key: 'people_in_care', label: 'People in care' },
  { key: 'verified_therapists', label: 'Verified therapists' },
  { key: 'cities', label: 'Cities' },
];

// ——— Partners ———
export const PARTNERS: Partner[] = [
  { name: 'Umang' },
  { name: 'Rozan' },
  { name: 'Karwan-e-Hayat' },
  { name: 'Taskeen' },
];

// ——— Team behind MindCare — photoUrl is populated from the backend ———
export const TEAM_MEMBERS: TeamMember[] = [
  { id: 'team-1', name: 'Muhammad Bilal Ibrahim', role: 'Full-Stack Developer' },
  { id: 'team-2', name: 'Raja Rehan Mustafa', role: 'Backend Developer' },
  { id: 'team-3', name: 'Malaika Irfan', role: 'Frontend Developer' },
];

// ——— How It Works steps ———
export const HOW_IT_WORKS: HowItWorksStep[] = [
  {
    number: '01',
    title: 'Tell us where you are',
    description: '15-minute intake. No labels, no diagnosis — just where it hurts and what you need.',
  },
  {
    number: '02',
    title: 'Match with a therapist',
    description: 'Verified, PMDC-listed clinicians. Aida proposes 3 — you pick. Switch any time.',
  },
  {
    number: '03',
    title: 'Weekly sessions, real ones',
    description: '50-minute video. Notes auto-prepared. Your therapist shapes your plan, not a bot.',
  },
  {
    number: '04',
    title: 'The days between matter',
    description: 'Body data, journaling, peer circles, dua, breath. Tiny exercises, all reviewed by your therapist.',
  },
];

// ——— What You Get features ———
export const FEATURES: Feature[] = [
  {
    id: 'therapist',
    icon: 'therapist',
    title: 'A real therapist',
    description: 'Weekly 50-minute video sessions. Switch any time, no questions asked.',
    color: 'from-emerald-400 to-emerald-600',
  },
  {
    id: 'aida',
    icon: 'aida',
    title: 'Aida, your co-pilot',
    description: 'AI between sessions — your therapist shapes what it can say and recommend.',
    color: 'from-purple-400 to-purple-600',
  },
  {
    id: 'mindband',
    icon: 'mindband',
    title: 'MindBand sensors',
    description: 'Optional wearable. Heart, breath, sleep — picked up so you don\'t have to log.',
    color: 'from-orange-400 to-orange-600',
  },
  {
    id: 'journal',
    icon: 'journal',
    title: 'Journaling that breathes',
    description: 'Prompts, freewrite, voice. Auto-summarised for your next session.',
    color: 'from-amber-400 to-amber-600',
  },
  {
    id: 'circles',
    icon: 'circles',
    title: 'Quiet peer circles',
    description: 'Anonymous, moderated. Anxiety, sober walks, grief, new parents.',
    color: 'from-rose-400 to-rose-600',
  },
  {
    id: 'sos',
    icon: 'sos',
    title: 'SOS, held by humans',
    description: 'One tap. Trained listener within 4 minutes, NGO escalation if needed.',
    color: 'from-red-400 to-red-600',
  },
];

// ——— Dummy mood data (replace with API call) ———
export const DUMMY_MOOD_DATA: MoodEntry[] = [
  { day: 'Mon', value: 3 },
  { day: 'Tue', value: 4 },
  { day: 'Wed', value: 3 },
  { day: 'Thu', value: 5 },
  { day: 'Fri', value: 4 },
  { day: 'Sat', value: 6 },
  { day: 'Sun', value: 5 },
];

// ——— Routes ———
export const ROUTES = {
  HOME: '/',
  CLIENT_APP: '/get-started',
  STORIES: '/stories',
  FOR_NGOS: '/for-ngos',
  FOR_THERAPISTS: '/for-therapists',
  THERAPIST_LOGIN: '/therapist/sign-in',
  THERAPIST_REGISTER: '/therapist/apply',
  ABOUT_US: '/about',
  HELP: '/help',
  PRICING: '/pricing',
  PRIVACY: '/privacy',
  TERMS: '/terms',
  HIPAA: '/hipaa-alignment',
  COOKIES: '/cookies',
} as const;

// ——— Stories page ———
export const STORIES: StoryEntry[] = [
  {
    id: 'story-1',
    quote: 'Day 90. The walks really do help.',
    name: 'Ammar',
    age: 34,
    location: 'Karachi',
    tag: 'sober walk',
    avatarInitials: 'A3',
    avatarColor: 'bg-emerald-700',
  },
  {
    id: 'story-2',
    quote: "First time I've felt heard without being fixed.",
    name: 'Hira',
    age: 26,
    location: 'Lahore',
    tag: 'grief',
    avatarInitials: 'H2',
    avatarColor: 'bg-rose-400',
  },
  {
    id: 'story-3',
    quote: 'My therapist saw my sleep break before I did.',
    name: 'Bilal',
    age: 36,
    location: 'Multan',
    tag: 'burnout',
    avatarInitials: 'B3',
    avatarColor: 'bg-amber-600',
  },
  {
    id: 'story-4',
    quote: 'Going through divorce. The couples circle saved me from doing it alone.',
    name: 'Fatima',
    age: 29,
    location: 'Islamabad',
    tag: 'divorce',
    avatarInitials: 'F2',
    avatarColor: 'bg-violet-500',
  },
];

export const STORIES_TOTAL_COUNT = 42;

// ——— For NGOs page ———
export const NGO_PARTNERS: NGOPartnerEntry[] = [
  {
    id: 'ngo-1',
    initials: 'UH',
    color: 'bg-orange-500',
    name: 'Umang Helpline',
    description: '24/7 helpline · nationwide',
    routedCount: 1240,
  },
  {
    id: 'ngo-2',
    initials: 'R',
    color: 'bg-emerald-700',
    name: 'Rozan',
    description: 'Counselling · referral · ISB/RWP',
    routedCount: 412,
  },
  {
    id: 'ngo-3',
    initials: 'K',
    color: 'bg-violet-500',
    name: 'Karwan-e-Hayat',
    description: 'Hospital partner · Karachi',
    routedCount: 86,
  },
  {
    id: 'ngo-4',
    initials: 'T',
    color: 'bg-amber-600',
    name: 'Taskeen',
    description: 'Helpline · 12h · LHR/FSD',
    routedCount: 268,
  },
];

export const NGO_STATS: Stat[] = [
  { value: '2,054', label: 'Cases routed YTD' },
  { value: '100%', label: 'Closed loop' },
  { value: 'Rs 220k', label: 'Monthly partner share' },
];

export const NGO_COVERAGE_TYPES = ['Helpline · 24/7', 'Counselling · referral', 'Hospital partner', 'Shelter / crisis care'];

// ——— For Therapists page ———
export const THERAPIST_FEATURES: TherapistFeature[] = [
  {
    id: 'aida-voice',
    icon: 'code',
    title: 'Aida, in your voice',
    description: 'AI assistant suggests · you approve. Every nudge to your patient passes through your hand first.',
    color: 'bg-violet-500',
  },
  {
    id: 'booking',
    icon: 'calendar',
    title: 'Booking that respects you',
    description: 'Patients request. You confirm. No auto-bookings, no late-night surprises.',
    color: 'bg-emerald-700',
  },
  {
    id: 'notes',
    icon: 'file-text',
    title: 'Notes that write themselves',
    description: 'In-session voice → structured SOAP. You edit instead of typing.',
    color: 'bg-orange-500',
  },
  {
    id: 'care',
    icon: 'heart',
    title: 'Care that follows the week',
    description: 'Body, journal, exercises — all in one chart, with your name on it.',
    color: 'bg-rose-400',
  },
  {
    id: 'crisis',
    icon: 'shield',
    title: 'Crisis support, not on you',
    description: "SOS routes to trained listeners and NGO partners. You're notified, not on the hook.",
    color: 'bg-amber-600',
  },
];

export const THERAPIST_STATS: Stat[] = [
  { value: '72%', label: 'Take-home split' },
  { value: 'Rs 164k', label: 'Avg monthly · active therapists' },
  { value: '2–3 days', label: 'Verification turnaround' },
];

export const THERAPIST_TESTIMONIAL = {
  quote: 'I have my Sundays back. The notes thing alone was worth the switch.',
  name: 'Dr. Sana',
  meta: '2 yrs on MindCare',
  initials: 'SY',
};

// ——— Therapist login page ———
export const THERAPIST_LOGIN_TESTIMONIAL = {
  label: 'YOUR PEOPLE, MAY 27',
  quote: 'He listens like nobody is in a hurry. The panic loops have actually slowed down.',
  attribution: '— Layla S., in care with Dr. Tariq for 3 months',
};

export const THERAPIST_WAITING_ITEMS = [
  { id: 'w1', color: 'bg-rose-400', title: 'Session notes', meta: 'Layla S. · last Friday' },
  { id: 'w2', color: 'bg-emerald-700', title: 'Care plan amendment', meta: 'Aida proposed for Bilal R.' },
  { id: 'w3', color: 'bg-amber-600', title: '5 new patient requests', meta: 'inbox' },
];

// ——— Therapist registration ———
export const THERAPIST_ONBOARDING_STEPS: { id: string; label: string }[] = [
  { id: 'identity', label: 'Identity' },
  { id: 'credentials', label: 'Credentials' },
  { id: 'practice', label: 'Practice' },
  { id: 'review', label: 'Review' },
];

export const THERAPIST_WHAT_HAPPENS_NEXT = [
  { id: 'n1', title: 'You finish all 4 steps', meta: '~10 minutes' },
  { id: 'n2', title: 'Auto-checks run', meta: 'PMDC, HEC, Verisys — usually overnight' },
  { id: 'n3', title: 'A senior reviews flagged items', meta: '~24 hours' },
  { id: 'n4', title: 'You get a welcome email', meta: 'Onboarding call · then patients' },
];

export const THERAPIST_SPECIALTIES = [
  'Clinical psychologist',
  'Psychiatrist',
  'Counselling psychologist',
  'Marriage & family therapist',
];

export const THERAPIST_FOCUS_AREAS = [
  'Anxiety',
  'Burnout',
  'Trauma',
  'EMDR',
  'CBT',
  'Couples',
  'Family',
  'Grief',
  'Addiction',
  'Adolescent',
  'Sleep',
  'Identity',
  'Post-partum',
  'OCD',
];

// ——— About Us page ———
export const ABOUT_INTRO =
  "We started MindCare in 2026 after watching too many friends drift through three apps, two therapists, and zero continuity. The honest answer wasn't another app — it was a steady human, supported by good technology, with the dignity to outlast the bad weeks.";

export const ABOUT_VALUES: AboutValueCard[] = [
  { id: 'val-1', title: 'Slow over flashy', description: 'A year of quiet work beats a viral feature.' },
  { id: 'val-2', title: 'Human at the center', description: 'AI assists. People decide.' },
  { id: 'val-3', title: 'Privacy by default', description: 'Your data is yours. Always.' },
  { id: 'val-4', title: 'Built where we live', description: 'In Urdu and English. With local NGOs.' },
];

// Milestones only — no dates or figures that haven't happened yet.
export const ABOUT_TIMELINE: AboutTimelineEntry[] = [
  {
    id: 'tl-1',
    date: '2026 · Founded',
    description: 'MindCare begins: one place that connects people with verified psychologists, without the stigma.',
  },
  {
    id: 'tl-2',
    date: 'Now',
    description: 'Building the web and mobile apps on one secure backend — sessions, journaling, communities and SOS.',
    current: true,
  },
  {
    id: 'tl-3',
    date: 'Next',
    description: 'Aida recommendations: exercise, sleep and diet plans that reach you only after your psychologist approves them.',
  },
  {
    id: 'tl-4',
    date: 'Next',
    description: 'MindCare Band: a wearable that shares heart-rate and breathing trends with your psychologist.',
  },
  {
    id: 'tl-5',
    date: 'Next',
    description: 'NGO partnerships for emergency support and help for those who can’t afford care.',
  },
];

// ——— Help page ———
// "Start here" guides. Patients use the mobile app; psychologists use the website.
export const HELP_GUIDES: HelpGuide[] = [
  {
    id: 'patient',
    tab: 'I’m a patient',
    intro: 'Your care happens in the MindCare mobile app. Here’s how to get going.',
    steps: [
      {
        id: 'p1',
        title: 'Get the app',
        where: 'Website',
        body: 'Tap Get started on this website, then download MindCare for Android or iPhone, or scan the QR code with your phone.',
        link: { label: 'Get the app', to: '/get-started' },
      },
      {
        id: 'p2',
        title: 'Create your account',
        where: 'Mobile app',
        body: 'Open the app and tap Create your account. Add your name, date of birth, gender, email, phone number, CNIC and a password. Your CNIC is only used for verification and is never shown publicly. Already registered? Tap Sign in instead.',
      },
      {
        id: 'p3',
        title: 'Tell us how you’re feeling',
        where: 'Mobile app',
        body: 'Pick the feelings that fit and how strong they are right now, then share a little of your story: whether you’ve seen a therapist before, any medication, and what’s been on your mind. You can skip anything. Tap Finish setup.',
      },
      {
        id: 'p4',
        title: 'Find your psychologist',
        where: 'Mobile app',
        body: 'Open the Care tab to browse verified psychologists. Sort and filter, open a profile, then start the 7-day free trial or choose a plan and pick a session time that suits you.',
      },
      {
        id: 'p5',
        title: 'Use MindCare between sessions',
        where: 'Mobile app',
        body: 'Home: check in your mood and chat with Aida. Care: your sessions, reschedules and your program. Pulse: your MindCare Band readings. Circles: peer support groups. Me: your profile, wallet and settings. The SOS button is always there if you need urgent help.',
      },
    ],
  },
  {
    id: 'psychologist',
    tab: 'I’m a psychologist',
    intro: 'Psychologists join and work with patients on the MindCare website.',
    steps: [
      {
        id: 't1',
        title: 'Apply to practice',
        where: 'Website',
        body: 'Go to For therapists and tap Apply. The form has 4 steps: Identity (name, email, phone, password), Credentials (PMDC licence number, specialty, focus areas, degree and supporting documents), Practice (session pricing, weekly availability and languages), then Review and submit. It takes about 10 minutes.',
        link: { label: 'Start your application', to: '/therapist/apply' },
      },
      {
        id: 't2',
        title: 'Get verified',
        where: 'Email',
        body: 'We check your PMDC, HEC and Verisys records, usually overnight, and a senior reviewer looks at anything flagged within about 24 hours. Once approved, you’ll get a welcome email and an onboarding call.',
      },
      {
        id: 't3',
        title: 'Sign in to your dashboard',
        where: 'Website',
        body: 'Once approved, sign in on the therapist sign-in page with the email and password you applied with.',
        link: { label: 'Therapist sign in', to: '/therapist/sign-in' },
      },
      {
        id: 't4',
        title: 'Work with your patients',
        where: 'Website',
        body: 'Requests: accept or decline new patients. Schedule and Today: your sessions. Patients: history, notes and MindCare Band trends. Care plans: review, edit and approve Aida’s recommendations before a patient sees them. Also Messages, Reports, and Profile & availability.',
      },
    ],
  },
];

export const HELP_TOP_QUESTIONS: HelpTopQuestion[] = [
  {
    id: 'q-1',
    question: 'How do I switch my therapist?',
    answer: [
      'You can switch your psychologist any time you need. In the app, choose a different verified psychologist and send them a request. Once they accept, you can continue with them.',
    ],
  },
  {
    id: 'q-2',
    question: 'When am I charged for the trial?',
    answer: [
      'You aren’t. Your first 7 days are free and we don’t ask for a card to start.',
      'Payment only begins if you choose a plan after the trial ends, and you’ll see the price before you confirm. Every payment appears in your payment history with an invoice.',
    ],
  },
  {
    id: 'q-3',
    question: 'Can MindCare diagnose me?',
    answer: [
      'No. MindCare doesn’t diagnose anyone. Aida, your journal, your MindCare Band readings and your reports help your psychologist understand how you are doing, but they are not a medical diagnosis.',
      'Clinical judgement always stays with your verified psychologist, who reviews and approves every AI recommendation before it reaches you.',
    ],
  },
  {
    id: 'q-4',
    question: 'Is my data shared with my employer or insurer?',
    answer: [
      'No. We don’t share your information with your employer or insurer, we don’t sell it, and we don’t use it for ads.',
      'Only your own psychologist can see your therapy record, notes and health data, and everything is encrypted. The one exception is an SOS emergency, when the contacts you set up yourself and partner helplines may be alerted to get you help.',
    ],
  },
  {
    id: 'q-5',
    question: 'What if I miss a session?',
    answer: [
      'It happens, so don’t worry. Message your psychologist in the app and agree a new time together; sessions are always scheduled at times you both accept.',
      'If you’re struggling and can’t wait for your next session, use SOS in the app or call our 24/7 crisis line.',
    ],
  },
];

export const HELP_CRISIS_PHONE = '0311-7786264';
export const HELP_CRISIS_PHONE_TEL = 'tel:+923117786264';
// Official inbox for the About page "Contact" and Help page "Email us" form. Leave empty until the
// team's address is live — the form still works; once this is set, sending
// also opens the visitor's mail app with the message pre-filled to it.
export const CONTACT_EMAIL = '';

// ——— Pricing page ———
export const PRICING_PLAN = {
  price: 'Rs 6,500',
  period: '/month',
  trial: '7-day free trial · no card required',
  features: [
    'Weekly 50-minute session with a verified therapist',
    'Aida co-pilot between sessions',
    'Body, journal & peer circles — one app',
    'SOS crisis routing, 24/7',
    'Switch therapist any time, no fee',
  ],
};

export const PRICING_FEATURE_STRIPS: PricingFeatureStrip[] = [
  {
    id: 'pf-1',
    icon: 'heart',
    title: "Can't afford?",
    description: 'NGO scholarships cover up to 80%. Apply during signup.',
  },
  {
    id: 'pf-2',
    icon: 'shield',
    title: 'Includes SOS',
    description: '24/7 trained listener · NGO escalation when needed.',
  },
  {
    id: 'pf-3',
    icon: 'code',
    title: 'No upsells',
    description: 'No premium tier, no add-ons. One subscription does it all.',
  },
];

// ——— Legal: Privacy Policy ———
export const PRIVACY_LAST_UPDATED = 'September 2026';

export const PRIVACY_SECTIONS: LegalSection[] = [
  {
    id: 'what-we-collect',
    title: 'What we collect',
    body: [
      'Client accounts: name, age, gender, and contact details, plus an optional mental health history and profile photo you can edit any time.',
      'Psychologist accounts: certifications, medical background, specialization areas, and the licenses/credentials you upload for verification.',
      'Sensor & health data: breathing rate, heart rate, and step count from your connected wearable, used to monitor your mental and physical state in real time and personalize exercise recommendations.',
      'Therapy records: session notes and observations your psychologist maintains, progress tracked over time, and the automated weekly/monthly reports the system generates from your sessions, mood check-ins, and sensor data.',
      'Community activity: anything you post, comment, or volunteer for inside a Community Support space.',
      'Engagement data: points, badges, streaks, and levels earned from wellness activities, sessions, and daily check-ins.',
      'Emergency data: any emergency contacts you configure, and the details of an SOS activation — the helplines, hospitals, or contacts notified.',
      'Payment data: session fees, number of sessions taken, and amounts paid. Card and mobile-wallet details are handled by our payment processor and never stored on our servers.',
    ],
  },
  {
    id: 'how-we-use-it',
    title: 'How we use it',
    body: [
      'To verify and onboard psychologists, match you with one, and run your sessions — including any third-party video conferencing tool (such as Zoom or Google Meet) your psychologist chooses to integrate.',
      "To power the AI recommendation engine, which reviews your therapy history and sensor data to suggest personalised exercises. Your psychologist approves every recommendation, including ones surfaced live during a session, before it reaches you.",
      'To run the 24/7 AI chat assistant, which can answer common questions, suggest coping strategies, perform initial triage, and — if it detects signs of distress — proactively trigger SOS support on your behalf.',
      'To personalise your Lifestyle & Wellness content and Motivation Corner (duas, quotes, surahs) around your stated needs.',
      "To generate your automated progress reports for your psychologist's review.",
      'We do not sell your data, and we do not use it to serve ads. That is a promise, not a feature toggle.',
    ],
  },
  {
    id: 'who-can-see-it',
    title: 'Who can see it',
    body: [
      'Your assigned psychologist sees your full therapy record, notes, sensor data, and generated reports. Other psychologists on the platform cannot.',
      'Admins can view the credentials psychologists submit for verification, and any reports or complaints raised in Community spaces — never your private therapy notes.',
      'Anything you post publicly in a Community space, or a volunteering role you sign up for, is visible to other members of that community.',
      'If you opt into an engagement leaderboard, your display name and points may be visible to other users — this is optional and off by default.',
      'During an SOS activation, your pre-configured emergency contacts, partnered helplines/hospitals, and an available psychologist may be contacted, and the event is logged for admin follow-up.',
    ],
  },
  {
    id: 'security',
    title: 'How we protect it',
    body: [
      'All data — including sensor readings, therapy notes, and uploaded credentials — is encrypted in transit (TLS) and at rest.',
      'Access to identifiable care records requires authenticated, logged sessions — every view is auditable.',
      'We follow the safeguards described in our HIPAA Alignment page, even though MindCare is not a US covered entity.',
    ],
  },
  {
    id: 'your-rights',
    title: 'Your rights',
    body: [
      'You can request an export of everything we hold on you, ask us to correct it, or ask us to delete your account and associated care data.',
      'You can remove emergency contacts, opt out of public leaderboards, or leave a community at any time.',
      'You can switch psychologists or leave the platform at any time — your data does not hold you hostage.',
      'Reach us at privacy@mindcare.pk for any of the above; we respond within 5 business days.',
    ],
  },
  {
    id: 'changes',
    title: 'Changes to this policy',
    body: [
      "If we materially change how we handle your data, we'll email you before the change takes effect, not just post a quiet update here.",
    ],
  },
];

// ——— Legal: Terms of Service ———
export const TERMS_LAST_UPDATED = 'September 2026';

export const TERMS_SECTIONS: LegalSection[] = [
  {
    id: 'not-a-crisis-service',
    title: 'MindCare is not a replacement for emergency services',
    body: [
      "The SOS button, available from every screen, connects you to local helplines and nearby hospitals, notifies your pre-configured emergency contacts, and attempts to connect you with an available psychologist in real time. Our AI chat assistant can also trigger SOS on its own if it detects signs of distress in a conversation.",
      'If you or someone else is in immediate danger, please call Umang at 0311-7786264 or your local emergency number first. SOS is a bridge to help, not a substitute for emergency medical care.',
    ],
  },
  {
    id: 'eligibility',
    title: 'Eligibility & onboarding',
    body: [
      'You must be 18 or older to create a client account, or have a parent/guardian complete intake on your behalf where locally permitted. An optional mental health history can be provided at signup.',
      'Psychologists register with their certifications, medical background, and specialization, and upload licenses/credentials for verification. An admin reviews and approves or rejects each application before the account can take patients.',
    ],
  },
  {
    id: 'the-relationship',
    title: 'The psychologist relationship',
    body: [
      'Psychologists on MindCare are independent, licensed clinicians — not MindCare employees. Clinical judgment, the therapy notes they keep on you, and treatment decisions are theirs alone.',
      'Psychologists set their own availability, manage their own bookings, and choose the video conferencing tool (e.g. Zoom, Google Meet) used for your session.',
    ],
  },
  {
    id: 'ai-features',
    title: 'AI recommendations & the AI chat assistant',
    body: [
      'Our AI analyses your therapy history and sensor data to suggest personalised exercises, including suggestions surfaced live during a session — but nothing reaches you without your psychologist reviewing and approving it first. The AI does not diagnose and is not a licensed clinician.',
      'The 24/7 AI chat assistant offers general information, coping strategies, and initial triage. It is not a substitute for professional care, and serious concerns should always be raised with your psychologist or, in an emergency, via SOS.',
    ],
  },
  {
    id: 'community-and-conduct',
    title: 'Community, volunteering & acceptable use',
    body: [
      "Community spaces are moderated by admins, who review reports and complaints and can remove content or suspend accounts. Harassment, sharing another member's private information, or impersonating a clinician will get an account suspended.",
      'Volunteering roles within a community are subject to admin approval and can be withdrawn if guidelines are not followed.',
      'You agree not to attempt to reverse-engineer, scrape, or resell any part of the platform.',
    ],
  },
  {
    id: 'engagement-rewards',
    title: 'Points, badges & rewards',
    body: [
      'Points, badges, streaks, and levels earned through wellness activities and check-ins are for motivation only and have no cash value.',
      'Rewards such as discounts, premium content, or session benefits are offered at our discretion and may change or be withdrawn. Leaderboard participation is optional.',
    ],
  },
  {
    id: 'billing',
    title: 'Fees & billing',
    body: [
      'Your profile shows your session fees, total sessions taken, and total amount paid at all times. Payment can be made by credit/debit card or mobile wallet, and invoices/receipts are issued for every transaction.',
      'NGO scholarships, where approved, can cover up to 80% of your cost.',
    ],
  },
  {
    id: 'liability',
    title: 'Limitation of liability',
    body: [
      'MindCare provides a platform connecting you with licensed psychologists; we are not liable for clinical outcomes, which depend on the independent judgment of your treating psychologist.',
      'To the extent permitted by law, our liability for platform issues is limited to the fees you paid in the preceding 3 months.',
    ],
  },
  {
    id: 'governing-law',
    title: 'Governing law',
    body: ['These terms are governed by the laws of Pakistan. Disputes are subject to the courts of Pakistan. Questions about these terms can be sent to legal@mindcare.pk.'],
  },
];

// ——— Legal: HIPAA Alignment ———
export const HIPAA_LAST_UPDATED = 'September 2026';

export const HIPAA_SECTIONS: LegalSection[] = [
  {
    id: 'what-alignment-means',
    title: 'What "HIPAA-aligned" means here',
    body: [
      'HIPAA is a US federal law, and MindCare currently operates in Pakistan — so we are not a HIPAA "covered entity" in the legal sense. What we mean by HIPAA-aligned is that we voluntarily hold ourselves to the same safeguards HIPAA requires of US healthcare providers, across therapy notes, sensor data, and the automated reports generated from them — because mental health records deserve that bar regardless of jurisdiction.',
    ],
  },
  {
    id: 'administrative',
    title: 'Administrative safeguards',
    body: [
      'Psychologist accounts only gain access to patient records after an admin has verified their certifications, medical background, and uploaded licenses.',
      'Every team member with any access to care data completes a confidentiality agreement before onboarding. Access is role-based and reviewed quarterly — a support engineer cannot open a therapy note; only your assigned psychologist and a narrow clinical-safety team can.',
      'Admins moderating Community content or reviewing complaints can see the report itself, never the therapy notes or sensor data behind it.',
    ],
  },
  {
    id: 'technical',
    title: 'Technical & physical safeguards',
    body: [
      'Encryption in transit (TLS 1.2+) and at rest for therapy notes, sensor readings (breathing rate, heart rate, steps), automated reports, and uploaded credentials alike.',
      'Every access to a patient record is logged and auditable — we can show, on request, exactly who viewed what and when.',
      'Session video is not recorded by default; if a psychologist enables recording for supervision, it requires your explicit, separate consent.',
    ],
  },
  {
    id: 'third-party-tools',
    title: 'Third-party video conferencing',
    body: [
      'Psychologists may integrate a video tool of their choice, such as Zoom or Google Meet, to run sessions. These are external platforms we do not control directly; we require psychologists to use accounts with appropriate security settings, and encourage the same scrutiny you would apply to any telehealth call.',
    ],
  },
  {
    id: 'confidentiality',
    title: 'Confidentiality obligations',
    body: [
      "Psychologists are bound by professional confidentiality standards and a platform-level data agreement — the same information a psychologist could not disclose in a physical clinic, they cannot disclose here.",
    ],
  },
  {
    id: 'breach-notification',
    title: 'Breach notification commitment',
    body: [
      "In the unlikely event of a data breach involving your health information, we commit to notifying affected users within 72 hours of confirming the breach, consistent with HIPAA's own notification window.",
    ],
  },
  {
    id: 'your-rights-mirrored',
    title: 'Rights mirrored from HIPAA',
    body: [
      'Access your full record — including sensor data, session notes, and generated reports — request corrections, request an export, and request deletion, the same rights HIPAA grants US patients, extended to everyone on MindCare regardless of where they live. Security questions or a disclosure to report can go to security@mindcare.pk.',
    ],
  },
];

// ——— Legal: Cookie Policy ———
export const COOKIE_LAST_UPDATED = 'September 2026';

export const COOKIE_SECTIONS: LegalSection[] = [
  {
    id: 'what-we-use',
    title: 'What cookies we use',
    body: [
      'Essential cookies: keep you signed in and your session secure across the web dashboard. The platform will not function without these.',
      'Preference cookies: remember small choices, like whether you dismissed a banner or which tab you had open in Settings.',
      'Limited analytics cookies: aggregate, anonymised usage patterns — e.g. which of the Wellness, Community, or Motivation Corner sections get used — so we can improve the product. Never tied to your therapy notes, sensor data, or journal content.',
    ],
  },
  {
    id: 'what-we-dont-use',
    title: "What we deliberately don't use",
    body: [
      "No advertising or cross-site tracking cookies. We don't run ads, so we have no reason to track you across the web — this is one of our core promises, not a setting you have to find and turn off.",
    ],
  },
  {
    id: 'third-party',
    title: 'Third-party cookies',
    body: [
      'Our payment processor sets a small number of cookies during checkout to prevent fraud. We do not control these directly, but we vet any processor we use for the same privacy bar we hold ourselves to.',
    ],
  },
  {
    id: 'managing-cookies',
    title: 'Managing cookies',
    body: [
      'You can block or delete cookies in your browser settings at any time. Blocking essential cookies will sign you out and may prevent the app from working correctly. Questions about cookies or tracking can be sent to privacy@mindcare.pk.',
    ],
  },
];

// ——— API base URL (swap to real endpoint) ———
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL ?? 'https://api.mindcare.pk/v1';