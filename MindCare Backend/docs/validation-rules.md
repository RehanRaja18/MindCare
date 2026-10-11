# Validation rules

**The single source of truth for input validation.** The backend
(`core/validators.py`, applied on model fields and serializers), MindCare Web
(`src/utils/validation.ts`) and MindCare App (`lib/core/utils/validators.dart`) all
implement exactly these rules, **in this order**, with **exactly these messages**.
Each check stops at the first failure, so a field shows one message at a time.

The hard rule behind this file is in @../CLAUDE.md ("validate every input field").
A module isn't done until every one of its fields appears here and is validated on
both sides.

In messages, `{Label}` is the field label from the field table (bottom of this file).

## How enforcement works (backend)

- Validators live in `core/validators.py` and are attached to **model fields**
  (via the field classes in `core/fields.py`), so Django admin forms validate them.
- Models with user-entered fields use `core.models.ValidatedModelMixin`: `save()`
  runs `full_clean()` (field rules only; uniqueness and foreign keys are left to the
  database), so services and management commands are covered too. A failure becomes a
  `DomainValidationError`, which the API returns as a 400.
  - `save(update_fields=[...])` validates only those fields, so old rows that
    predate a rule (e.g. a name with digits) can still log in. The rule applies the
    next time that field is written.
  - **Not covered:** `bulk_create()`, `QuerySet.update()` and raw SQL. Don't use them
    on user-entered fields.
- Serializers run the same validator, so the API answers with the field's own key
  (e.g. `profile.city`) before anything reaches the model.

## Normalisation (applied before validation, on every side)

| Kind | What happens |
|---|---|
| Single-line text (names, identifiers, phones, emails, URLs, search) | Control characters removed; leading/trailing spaces removed; runs of spaces collapsed to one |
| Multi-line text (bio, qualifications, description, quote text) | `\r\n` → `\n`; control characters except `\n` removed (a tab becomes a space); spaces collapsed within each line; leading/trailing whitespace removed |
| Identifiers (license / registration numbers) | Single-line normalisation, then UPPERCASE |
| Email | Single-line normalisation, then lowercase |
| Phone | Spaces, dashes, dots and brackets removed; a leading `00` becomes `+`; a Pakistani local number (a single leading `0` then 9–10 digits, e.g. `03001234567`, `0421234567`) becomes `+92…` without the `0` |

## Rules by type

### Person name
Used for: full name, city name, quote author.
1. Only Unicode letters (any script, including Urdu, with its combining marks),
   spaces, hyphens `-`, apostrophes `'` `’` and dots `.`
   → `{Label} can only contain letters, spaces, hyphens (-), apostrophes (') and dots (.).`
2. Length 2–100 characters (after normalisation)
   → `{Label} must be between 2 and 100 characters.`
3. At least 2 letters → `{Label} must contain at least 2 letters.`

### Organisation name
Used for: NGO organisation name, license issuing authority, registering authority, and
admin-edited reference names (country, language, specialization).
1. Only letters, digits, spaces and `& , . ' ’ - ( ) /`
   → `{Label} can only contain letters, numbers, spaces and & , . ' - ( ) /`
2. Length 2–150 characters (reference names: 2–100)
   → `{Label} must be between 2 and 150 characters.`
3. At least 2 letters → `{Label} must contain at least 2 letters.`

### Free text
Used for: qualifications, bio, NGO description, quote text; later reasons, complaints
and notes.
1. Length between the field's min and max (after normalisation)
   → `{Label} must be between {min} and {max} characters.`
2. No HTML: rejected if it contains `<` followed by a letter, `/`, `!` or `?`
   (a plain `<` or `>` like "< 6 months" is fine) → `{Label} can't contain HTML tags.`
3. At least 3 letters (so not just spaces, digits or symbols)
   → `{Label} must contain at least 3 letters.`

Optional free-text fields may be left empty; the rules apply only when something is
entered.

### Identifier
Used for: license number, NGO registration number.
1. Only letters, digits, spaces, dots, slashes and hyphens (after uppercasing)
   → `{Label} can only contain letters, numbers, spaces, dots (.), slashes (/) and hyphens (-).`
2. Length 3–64 → `{Label} must be between 3 and 64 characters.`
3. At least one digit → `{Label} must contain at least one number.`

### Phone
Used for: patient phone number, NGO official phone.
After normalisation, must be E.164: `+`, a non-zero digit, then 6–14 more digits
→ `Enter a phone number in international format (e.g. +923001234567), or a Pakistani number starting with 0 (e.g. 03001234567).`

### Email
Valid address (Django's `EmailValidator`), max 254 characters, lowercased
→ `Enter a valid email address.`
Account email is unique → `A user with this email already exists.`

### HTTPS URL
Used for: NGO website; later video links (allowed domains `zoom.us`,
`meet.google.com`, including subdomains).
1. Valid URL starting with `https://`
   → `{Label} must be a full https:// address (e.g. https://example.org).`
2. Max 200 characters → `{Label} must be at most 200 characters.`
3. Where domains are restricted: host is one of them or a subdomain
   → `{Label} must be a link on one of: {domains}.`

### Date of birth
1. Not in the future → `Date of birth can't be in the future.`
2. Age 18 or over on today's date → `You must be 18 or older to use MindCare.`
3. Age 120 or under → `Enter a real date of birth (age 120 or under).`

### Numbers
Whole numbers unless stated. Out of range or not a number
→ `{Label} must be a whole number between {min} and {max}.` (decimals:
`{Label} must be a number between {min} and {max}.`)

### Choices
Only the listed values. DRF's messages: `"{value}" is not a valid choice.` /
`Choose a valid option.` (services). The frontends offer only the listed values
(dropdowns, radio buttons), so these normally never show.

### Password
Django's validators, run with the user's email and name so similarity is checked:
- `This password is too short. It must contain at least 8 characters.`
- `This password is too common.`
- `This password is entirely numeric.`
- `The password is too similar to the {email / full name}.`

The frontends check length (8+) and "not only digits" while typing. "Too common" and
"too similar" are checked only by the backend, and its message is shown.

### Unknown fields
Any key a serializer doesn't declare → `This field can't be set.`
(`RejectUnknownFieldsMixin`).

### Search text (query parameters)
Single-line normalisation, max 120 characters. Not stored, so no character rule.
(`GET /reference/cities/` rejects a null character with `Null characters are not
allowed.` instead of stripping it.)

### File uploads
Introduced with the storage foundation. Each upload field lists its allowed types; the
type is detected from the file's first bytes (magic bytes), never the extension or the
browser's content type. The stored name is a random UUID plus the detected extension;
the original filename is never used as a path.
- Wrong type → `{Label} must be one of: {types}.`
- Too big → `{Label} must be {max} MB or smaller.`
- Empty → `{Label} is empty.`

## Field table

| Field (API key) | Where | Label | Type | Required | Extra |
|---|---|---|---|---|---|
| `email` | register (all roles), login | Email | Email | yes | unique |
| `password` | register, login | Password | Password | yes | login: required only |
| `full_name` | register (all roles) | Full name | Person name | yes | |
| `is_adult_confirmed` | register | — | Choice (`true`) | yes | `You must confirm you are 18 or older.` |
| `profile.timezone` | register, profiles | Timezone | Choice (IANA) | yes | `'{value}' is not a recognised IANA timezone.`; set by the device / a dropdown |
| `profile.city`, `city` | psychologist and NGO register/profile, patient profile | City | Person name | psychologist/NGO yes; patient no | matched to an existing city, else created unverified |
| `profile.country`, `country` | profiles | Country | Choice (ISO code) | psychologist/NGO yes | |
| `date_of_birth` | patient profile | Date of birth | Date of birth | no | can be corrected, never cleared once set |
| `gender` | patient/psychologist profile | Gender | Choice | no | |
| `phone_number` | patient profile | Phone number | Phone | no | |
| `preferred_language` | patient profile | Preferred language | Choice | no | |
| `is_profile_public` | patient profile | — | Choice (true/false) | no | |
| `license_number` | psychologist register | License number | Identifier | yes | unique per issuing country; locked after registration |
| `license_issuing_country` | psychologist register | Issuing country | Choice | yes | locked |
| `license_issuing_authority` | psychologist register | Issuing authority | Organisation name | yes | locked |
| `qualifications` | psychologist register | Qualifications | Free text 10–1000 | yes | locked |
| `specializations` | psychologist register/profile | Specializations | Choice, at least 1 | yes | |
| `languages` | psychologist register/profile | Languages | Choice, at least 1 | yes | |
| `years_of_experience` | psychologist register/profile | Years of experience | Number 0–60 | yes | |
| `bio` | psychologist register/profile | Bio | Free text 30–2000 | no | |
| `organization_name` | NGO register | Organisation name | Organisation name | yes | locked |
| `registration_number` | NGO register | Registration number | Identifier | yes | unique per country; locked |
| `registration_country` | NGO register | Registration country | Choice | yes | locked |
| `registering_authority` | NGO register | Registering authority | Organisation name | yes | locked |
| `official_phone` | NGO register/profile | Official phone | Phone | yes | |
| `official_email` | NGO register/profile | Official email | Email | yes | not unique |
| `website` | NGO register/profile | Website | HTTPS URL | no | any domain |
| `description` | NGO register/profile | Description | Free text 30–2000 | no | |
| `service_areas[].country` / `.city` | NGO register/profile | Country / City | Choice / Person name | country yes, city no | at least one area |
| `accepting` + `reason` | psychologist availability | — | Choice | reason required when off | |
| `reason` | decline / end relationship | — | Choice | decline no, end yes | |
| `psychologist` | patient request | — | Number ≥ 1 | yes | |
| `search` | directory, cities | Search | Search text | no | |
| AI form: `Age` | AI assessment | Age | Number 18–49 | yes | `Age must be a whole number between 18 and 49.` (the AI's supported range) |
| AI form: `Sleep Hours` | AI assessment | Sleep hours | Decimal 0–24 | yes | |
| AI form: `Physical Activity (hrs/week)` | AI assessment | Physical activity | Decimal 0–168 | yes | |
| AI form: `Heart Rate (bpm)` | AI assessment | Heart rate | Decimal 30–220 | yes | |
| AI form: `Breathing Rate (breaths/min)` | AI assessment | Breathing rate | Decimal 5–60 | yes | |
| AI form: `Therapy Sessions (per month)` | AI assessment | Therapy sessions | Decimal 0–31 | yes | |
| AI form: `Diet Quality (1-10)` | AI assessment | Diet quality | Decimal 1–10 | yes | |
| AI form: caffeine servings (4 fields) | AI assessment | Cups of coffee / Cups of tea / Energy drinks / Cans of soda | Number 0–20 | yes | |
| AI form: PSS answers (4 fields) | AI assessment | Stress question 1–4 | Number 0–4 (radio) | yes | |
| AI form: `Occupation`, `Family History of Anxiety` | AI assessment | — | Choice | yes | |
| Quote `text` | Django admin | Quote | Free text 10–500 | yes | |
| Quote `author` | Django admin | Author | Person name | no | |
| Quote `category` | Django admin | — | Choice | no | |
| Country / Language / Specialization `name` | Django admin | Name | Organisation name 2–100 | yes | |
| Country `code` | Django admin | — | 2 uppercase letters | yes | `Enter a two-letter ISO country code, e.g. PK.` |
| Language `code` | Django admin | — | 2 lowercase letters | yes | `Enter a two-letter ISO 639-1 code, e.g. ur.` |
| City `name` | Django admin | City | Person name | yes | |
