# Handoff: input validation (backend)

**The rules and exact messages are in [../validation-rules.md](../validation-rules.md).**
The Web (`src/utils/validation.ts`) and the App (`lib/core/utils/validators.dart`) must
implement the same rules in the same order with the same messages, show the message
under the field as the user types or leaves it, and keep the submit button disabled
until the form is valid. Always still show the backend's message if it rejects
something.

## What changed in the API

No endpoint, request key or response shape changed. Only what is accepted changed:

| Where | Before | Now |
|---|---|---|
| `full_name` (register, every role) | anything up to 255 characters | person-name rule: letters (any script), spaces, `- ' .`; 2–100; at least 2 letters |
| `profile.city`, `city`, service-area `city` | anything up to 120 | person-name rule (label "City") |
| psychologist `license_number`, NGO `registration_number` | anything up to 64 | identifier rule; stored UPPERCASE with spaces collapsed |
| `license_issuing_authority`, `organization_name`, `registering_authority` | anything up to 200 | organisation-name rule, 2–150 |
| `qualifications` | up to 1000 | 10–1000, no HTML, at least 3 letters |
| `bio`, NGO `description` | up to 2000 | empty, or 30–2000 with no HTML and at least 3 letters |
| `years_of_experience` | 0–70 | **0–60**; message `Years of experience must be a whole number between 0 and 60.` |
| `phone_number`, `official_phone` | strict `+…` only | also `03001234567`, `0300-1234567`, `042 1234567`, `0092…`; **stored and returned as `+92…`** |
| `website` | any URL | `https://` only |
| `date_of_birth` | 18+ and not in the future | also age 120 or under |
| `password` (register) | Django's checks without user details | also "too similar to the email / full name" |
| AI form `Age` | 0–120, then the AI's 422 came back as `{"detail": "…"}` | **18–49**, refused by the backend as `{"Age": ["Age must be a whole number between 18 and 49."]}` |
| AI form numbers | any number | bounded (sleep 0–24, activity 0–168, heart rate 30–220, breathing 5–60, therapy 0–31, diet 1–10); messages like `Heart rate must be a number between 30 and 220.` |

All text is trimmed, control characters are removed and repeated spaces collapsed
before checking, so the frontends should do the same before validating.

## Error shape (unchanged)

Field errors are `{"field": ["message"]}`; register profile errors are
`{"profile": {"field": ["message"]}}`; NGO service areas are
`{"service_areas": {"0": {"city": ["message"]}}}` (keyed by the item's index).

## Examples

```http
POST /api/v1/accounts/register/
{"full_name": "Sara Ahmed 2", ...}

400 {"full_name": ["Full name can only contain letters, spaces, hyphens (-), apostrophes (') and dots (.)."]}
```

```http
PATCH /api/v1/patients/me/
{"phone_number": "0300-1234567"}

200 {..., "phone_number": "+923001234567", ...}
```

## Screens that must mirror the rules (once the frontend branches are on GitHub)

- **Web:** therapist apply wizard, therapist profile, availability switch (reason
  choice), decline / end reasons (choices), AI assessment form, admin and therapist
  sign-in (email + password present), NGO register form and `ngo/me` page.
- **App:** sign-up, sign-in, profile edit (city, phone, date of birth), and every
  later form.

## Demo data

`seed_demo` names are now plain ("Dr. Sara Ahmed"); psychologist bios start with
"Demo account, not a real psychologist." Re-run it once on production to rename the
accounts seeded earlier with "(Demo)".
