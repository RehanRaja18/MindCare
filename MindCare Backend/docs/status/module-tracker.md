# Module tracker

Status of every bullet in the official module list ([../modules.md](../modules.md)),
per component. Built from the 2026-10-08 audit ([2026-10-08-status.md](2026-10-08-status.md))
and checked against `main` at `a295f11`. **Update this file at the end of every module.**

Status values: **done** (works end to end on real data) · **partial** (some of the
bullet works; the note says what's missing) · **mock only** (screens exist with
hardcoded data, no backend calls) · **not started** · **—** (that component has no
role in the bullet).

The Web is the psychologist/admin client; the App is the patient client. "Branch"
means the work sits on an unmerged branch.

Last updated: 2026-10-10 (input-validation-hardening, backend part). Re-checked against
`origin` on 2026-10-10: no frontend changes have been pushed since 2026-10-08.

## 6.1 User Onboarding and Profile

| Bullet | Backend | Web | App | Notes |
|---|---|---|---|---|
| Register with name, age, gender, contact details; optional mental health history | partial | — | partial (branch `mobile/patient-signup-api`) | Register takes name, email, password, 18+ declaration, timezone. DOB, gender and phone are set later through `PATCH /patients/me/`. No mental health history (decisions.md: no health data before the PHI audit trail) |
| Profile photo upload; view and edit profile any time | partial | — | mock only | `GET/PATCH /patients/me/` done; no photo (needs file storage) |
| Choose which information is public and which is private | partial | — | mock only | One `is_profile_public` flag (decisions.md 2026-09-26), not per-field |

## 6.2 Psychologist Onboarding

| Bullet | Backend | Web | App | Notes |
|---|---|---|---|---|
| Register with personal and professional info, certifications, background, specializations | done | done | — | Text credentials at registration (Phase 2) |
| Upload credentials and licences for verification | not started | not started | — | Needs file storage; pending accounts can't log in today |
| Set availability, manage session bookings, video conferencing (Zoom / Meet) | partial | partial | — | Only the "accepting new patients" switch exists. Working hours, booking and video links not started (roadmap Phase 4) |

## 6.3 Admin Panel

| Bullet | Backend | Web | App | Notes |
|---|---|---|---|---|
| Verify psychologist credentials; approve or reject registrations | partial | partial (branch `web/admin-psychologist-approvals`) | — | Django admin only; API contract agreed (option A) |
| Monitor platform activities; ensure policies are followed | not started | mock only | — | Overview and Users pages use `constants/adminConsole.ts` |
| Moderate community content; manage reports and complaints | not started | mock only | not started | Moderation page is mock. Community moderation comes with 6.8 |

## 6.4 Patient Profiling

| Bullet | Backend | Web | App | Notes |
|---|---|---|---|---|
| Psychologists keep therapy notes and observations after each session | not started | mock only | — | Needs the PHI audit trail (roadmap Phase 5) |
| Psychologists track progress and changes over time | not started | mock only | — | |
| Users view summarised insights of their progress | not started | — | mock only | |

## 6.5 Sensor Monitoring and Health Tracking

| Bullet | Backend | Web | App | Notes |
|---|---|---|---|---|
| Track breathing rate, heart rate and sweating through sensors | not started | — | mock only | project-vision §15 dropped sweating for motion; resolve before this module starts |
| Use the data to monitor mental/physical state in real time and personalise exercise recommendations | not started | — | mock only | |
| Notifications and reminders based on sensor data | not started | — | mock only | Needs notifications (roadmap Phase 10) |

## 6.6 AI Recommendations with Therapy Sessions

| Bullet | Backend | Web | App | Notes |
|---|---|---|---|---|
| AI analyses mental health and sensor data to recommend exercises, sleep schedule and diet | partial | partial | — | `/ai/anxiety-prediction/` live (form input, nothing stored). `/patient-summary` forwarding and Web display on branch `web/ai-recommendations` |
| AI learns from psychologist feedback (approval or update) | not started | not started | — | Needs the stored triple and separate training consent (decisions.md 2026-09-27) |
| Psychologist approves or updates recommendations | not started | mock only | not started | Care plan editor is mock |

## 6.7 AI Chat Assistance

| Bullet | Backend | Web | App | Notes |
|---|---|---|---|---|
| 24/7 chatbot answering common mental health questions | not started | — | mock only | Aida chat screen is mock |
| Suggests therapy or wellness options | not started | — | mock only | |
| Initial triage, coping strategies, directs to resources or psychologists | not started | — | mock only | |

## 6.8 Community Support

| Bullet | Backend | Web | App | Notes |
|---|---|---|---|---|
| Join or create communities; share experiences | not started | mock only | mock only | Creator approval required (project-vision §22) |
| Interact, advise, volunteer, organise real-world activities | not started | mock only | mock only | |
| Emotional support and belonging | not started | — | mock only | Outcome of the two bullets above |

## 6.9 Lifestyle and Wellness

| Bullet | Backend | Web | App | Notes |
|---|---|---|---|---|
| Content: diet plans, exercise routines, stress-reduction techniques | not started | — | mock only | Program and breathing screens are mock |
| Personalised suggestions from mental health needs and sensor data | not started | — | mock only | Must go through psychologist approval if AI-generated |
| Resources: mindfulness, yoga, nutrition, relaxation | not started | — | mock only | |

## 6.10 Motivation Corner

| Bullet | Backend | Web | App | Notes |
|---|---|---|---|---|
| Duas (audio + text) | not started | — | mock only | Own table, opt-in (decisions.md 2026-10-08) |
| Quotes | done | — | mock only | `GET /motivation/quotes/`, `/random/` |
| Surahs (audio + text) | not started | — | mock only | Own table, opt-in |

## 6.11 Payments

| Bullet | Backend | Web | App | Notes |
|---|---|---|---|---|
| View session fees, total sessions and total paid | not started | mock only | mock only | Roadmap Phase 9 |
| Multiple secure payment methods (card, mobile wallets) | not started | mock only | mock only | Stripe test mode only (decisions.md 2026-10-06) |
| Invoicing, receipts and session booking | not started | mock only | mock only | |

## 6.12 NGO Onboarding and Emergency SOS

| Bullet | Backend | Web | App | Notes |
|---|---|---|---|---|
| SOS button on every screen starts an emergency flow | not started | — | mock only | NGO signup and profile done (backend) |
| Helplines, nearby hospitals, emergency contacts, live psychologist connection | not started | mock only | mock only | Thresholds and escalation must not be invented (project-vision §27) |
| Chatbot detects distress and activates SOS; emergency activity logged for admins | not started | mock only | — | Depends on 6.7 |

## 6.13 Engagement and Rewards

| Bullet | Backend | Web | App | Notes |
|---|---|---|---|---|
| Points, badges and streaks for activities, sessions and check-ins | not started | — | mock only | |
| Levels and milestones | not started | — | mock only | |
| Rewards (discounts, premium content, session benefits), optional leaderboards | not started | — | mock only | Premium model not decided (project-vision §28); leaderboards need a privacy review against the pseudonym rules |

## 6.14 Automated Reports

| Bullet | Backend | Web | App | Notes |
|---|---|---|---|---|
| Weekly and monthly reports on activity, mood and therapy progress | not started | mock only | — | Depends on 6.4, 6.5 and sessions |
| Visual insights: trends, behaviour changes, sensor indicators | not started | mock only | — | |
| Psychologists use reports to adjust treatment | not started | mock only | — | |

## Cross-cutting

| Item | Status | Notes |
|---|---|---|
| Patient ↔ psychologist relationships | Backend done, Web done, App mock only | Patient side in the App is Phase 1 item (f) |
| File storage (`integrations/storage_client`) | not started | Phase 1 item (b) |
| DB-backed PHI access audit trail | not started | Phase 1 item (b); required before any health data is stored |
| Web lint / typecheck / tests | missing | `package.json` has only `dev`, `build`, `preview` |
| Input validation (docs/validation-rules.md) | Backend done; Web and App not started | Backend enforces every rule on models and serializers. The Web/App part waits for the frontend partner's branches |
