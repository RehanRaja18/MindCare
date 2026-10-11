# MindCare Backend

Unified Django REST Framework backend serving MindCare Web (React) and MindCare App (Flutter). See @docs/architecture.md for full system design and @docs/decisions.md for the reasoning behind key choices.

## Stack
Django + DRF, PostgreSQL, Celery + Redis, JWT auth (simplejwt), Stripe, Zoom API, Firebase Cloud Messaging.

## Hard rules — do not violate these
- NEVER put business logic in views.py. Views parse requests, call a service/selector function, serialize the result. All business rules live in services.py (writes) or selectors.py (reads).
- NEVER let AI-generated patient recommendations reach a patient without going through the psychologist approval workflow in apps/recommendations. This is a non-negotiable product rule.
- NEVER touch files inside "MindCare Web" or "MindCare App" folders from this branch.
- ALWAYS filter psychologist-facing querysets to that psychologist's own patients — role-based access alone is not enough, every query needs an object-level ownership check.
- NEVER log PHI (patient names, journal content, clinical notes, health data) in plaintext in application logs. Use core/audit.py for access logging instead.
- ALWAYS write a service-layer test (tests/test_services.py) for new business logic before considering a feature done.
- Ask before adding a new third-party package not already in requirements/base.txt.
- After implementing any new service, selector, or API endpoint, append an entry to docs/module-reference.md in its existing table format. Never skip this — it is required for the project's final documentation.

## Hard rule: validate every input field
A psychologist name once accepted digits. That must never happen again, on any field,
anywhere.
1. **One source of truth:** @docs/validation-rules.md lists every field type with its
   rule and its exact error message. The backend and both frontends match it exactly.
2. **The backend is the authority:** reusable validators live in `core/validators.py`
   and are applied on the MODEL fields, so the API, Django admin and management
   commands are all covered. Minimum rules:
   - Person and organisation names: letters (including Unicode/Urdu), spaces, hyphens,
     apostrophes and dots only; no digits or symbols; 2–100 characters; trimmed; no
     repeated spaces.
   - Email: valid format, lowercased, unique where it should be.
   - Phone: E.164; Pakistan numbers also accepted in local form and normalised.
   - Dates: no future dates where that makes no sense; date of birth means 18+ and a
     realistic age (max 120).
   - Numbers: explicit min/max (years of experience 0–60, fees > 0, ratings in range);
     no negatives unless meaningful.
   - Free text (bio, qualifications, reasons, complaints, notes): min and max length,
     trimmed, control characters stripped, HTML/script rejected or escaped, not just
     whitespace or symbols.
   - Licence numbers, codes, IDs: an allowed character set and length.
   - URLs (video links etc.): https only, with allowed domains where relevant
     (zoom.us, meet.google.com).
   - Choices and enums: only the listed values (DRF already does this; keep it).
   - Passwords: Django's validators (length, common, numeric, similar to user details).
   - File uploads: an allowlist of types checked by real content (magic bytes), not
     the extension; a max size; filenames sanitised/renamed.
   - Unknown fields are rejected (`RejectUnknownFieldsMixin`; keep it).
3. **Frontends mirror the same rules (Web and App):** inline error under the field as
   the user types or leaves it, the same message text as validation-rules.md, sensible
   input types (numeric keyboard for phone, date pickers, max lengths), and the submit
   button disabled until the form is valid. Still show the backend's error if it rejects
   something.
4. **Tests:** every validated field gets at least one valid case and several invalid
   ones (digits in names, too long, only spaces, script tags, wrong file type, out of
   range). The frontends' form validators get unit tests where the project has a test
   setup.
5. **Every module follows this rule:** a module isn't done until every one of its
   fields is validated on both sides.
If tightening a rule could reject existing production data, put it in the question list
with options (clean up the data / allow old values / migrate).

## Requirements Interview
Before implementing any new feature, significant change, or design decision, run a requirements interview first — do not start writing code while it's unresolved.
- Ask the questions in ONE batch per phase (see "Working agreement" below), not one at a time.
- Challenge assumptions rather than agreeing with the requested approach by default.
- Actively surface missing requirements and ambiguities — don't silently fill gaps with assumptions.
- Explicitly consider: user roles, permissions/authorization, expected behavior, edge cases, failure states, validation, data requirements, integration/dependency implications, and acceptance criteria.
- Continue until requirements are sufficiently specified, then summarize the finalized requirements and proposed implementation approach, and ask for confirmation before implementing.
- Trivial changes with no meaningful ambiguity or design risk may skip the interview.

## Working agreement
- Batch questions: before implementing, collect EVERY decision for the
  whole phase into ONE numbered list, each with options (A/B/C), your
  recommendation marked (Recommended), and one line on why. I answer
  once, e.g. "defaults except 3: B".
- Then work autonomously to the end. Decide small things yourself
  using decisions.md and the existing conventions, and log them. Stop
  mid-way ONLY for: production data or Render/Supabase settings,
  security or privacy trade-offs not covered by decisions.md, payments,
  changing existing behaviour, or a real blocker. If you must stop,
  batch everything again.
- Never run anything against production; give me the exact commands.
- One branch per module, off main. Files staged by name. No .env changes.

### Definition of done (every module)
A module is done only when every bullet in its description in @docs/modules.md works
end to end:
1. Backend: models, services, endpoints, permissions, throttling, OpenAPI docs, tests
   first. Full suite with warnings as errors, `makemigrations --check`, strict schema
   check, pre-commit.
2. MindCare Web (psychologist/admin) and MindCare App (patient, run with
   `flutter run -d chrome --web-port 5000`): every screen for that module calls the
   real backend. No mock, static or hardcoded data left in that module's screens;
   delete the mock data once replaced.
3. Frontend quality: reuse the existing design system, components, API client and
   token handling; no redesigns. Loaders (the backend cold-starts in ~40s), empty
   states and the backend's error messages. Handle 401 (refresh, then login), 403 and
   429. Run `flutter analyze` (plus `flutter test`) and the Web's checks.
4. Demo data: extend `seed_demo` with realistic, clearly fake data for the module.
5. `docs/handoff/<module>.md`: endpoints, examples, errors, screens.
6. One PR per module (backend + Web + App) with a checklist of the module's bullets,
   each marked done or deferred with the reason.
If a bullet conflicts with @docs/decisions.md or can't be done in the phase, put it in
the question list with options; never skip it silently. Before editing a Web or App
screen, check the open frontend branches and build on them. Update
@docs/status/module-tracker.md after every module.

## Commands
- Activate venv: [OS-appropriate command]
- Run server: python manage.py runserver
- Run tests: pytest
- Make migrations: python manage.py makemigrations
- Migrate: python manage.py migrate

## Current status
See @docs/decisions.md and update it whenever an architectural choice is made.
