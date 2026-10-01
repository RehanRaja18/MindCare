// ============================================================
// MindCare — Country / language / timezone options for sign-up
// Values are the codes the backend expects (ISO 3166-1 alpha-2,
// ISO 639-1, IANA time zones); labels come from the browser's Intl
// data, so there's no long hand-maintained list of names.
// ============================================================

export interface Option {
  value: string;
  label: string;
}

const COUNTRY_CODES =
  'AF AL DZ AD AO AG AR AM AU AT AZ BS BH BD BB BY BE BZ BJ BT BO BA BW BR BN BG BF BI KH CM CA CV CF TD CL CN CO KM CG CD CR CI HR CU CY CZ DK DJ DM DO EC EG SV GQ ER EE SZ ET FJ FI FR GA GM GE DE GH GR GD GT GN GW GY HT HN HK HU IS IN ID IR IQ IE IL IT JM JP JO KZ KE KI KW KG LA LV LB LS LR LY LI LT LU MO MG MW MY MV ML MT MH MR MU MX FM MD MC MN ME MA MZ MM NA NR NP NL NZ NI NE NG KP MK NO OM PK PW PS PA PG PY PE PH PL PT PR QA RO RU RW KN LC VC WS SM ST SA SN RS SC SL SG SK SI SB SO ZA KR SS ES LK SD SR SE CH SY TW TJ TZ TH TL TG TO TT TN TR TM TV UG UA AE GB US UY UZ VU VA VE VN YE ZM ZW'.split(
    ' '
  );

const displayName = (type: 'region' | 'language', code: string) => {
  try {
    return new Intl.DisplayNames(['en'], { type }).of(code) ?? code;
  } catch {
    return code;
  }
};

/** Pakistan first (most users), then alphabetical. */
export const COUNTRY_OPTIONS: Option[] = [
  { value: 'PK', label: displayName('region', 'PK') },
  ...COUNTRY_CODES.filter((c) => c !== 'PK')
    .map((c) => ({ value: c, label: displayName('region', c) }))
    .sort((a, b) => a.label.localeCompare(b.label)),
];

/** Pakistan first, then alphabetical — applied to the live country list too. */
export const sortCountries = (opts: Option[]) => [
  ...opts.filter((o) => o.value === 'PK'),
  ...opts.filter((o) => o.value !== 'PK').sort((a, b) => a.label.localeCompare(b.label)),
];

/** Languages clinicians most often practise in here (ISO 639-1) — shown as quick picks. */
export const COMMON_LANGUAGE_CODES = ['en', 'ur', 'pa', 'sd', 'ps', 'ar', 'fa', 'hi', 'bn'];

export const LANGUAGE_OPTIONS: Option[] = COMMON_LANGUAGE_CODES.map((c) => ({
  value: c,
  label: displayName('language', c),
}));

/** Fallback until GET /reference/specializations/ loads (backend's seeded slugs). */
export const SPECIALIZATION_FALLBACK: Option[] = [
  ['anxiety', 'Anxiety'],
  ['depression', 'Depression'],
  ['trauma-ptsd', 'Trauma / PTSD'],
  ['couples-relationship', 'Couples / Relationship'],
  ['grief', 'Grief'],
  ['addiction-substance-use', 'Addiction / Substance use'],
  ['stress-management', 'Stress management'],
  ['ocd', 'OCD'],
  ['eating-disorders', 'Eating disorders'],
  ['sleep-issues', 'Sleep issues'],
  ['anger-management', 'Anger management'],
  ['family-therapy', 'Family therapy'],
].map(([value, label]) => ({ value, label }));

/** International phone format the backend requires (E.164), e.g. +923001234567. */
export const E164 = /^\+[1-9]\d{6,14}$/;
export const toE164 = (raw: string) => raw.replace(/[\s()-]/g, '');

/** The visitor's own time zone, falling back to Pakistan. */
export const DEFAULT_TIMEZONE = (() => {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Karachi';
  } catch {
    return 'Asia/Karachi';
  }
})();

export const TIMEZONE_OPTIONS: Option[] = (() => {
  let zones: string[] = [];
  try {
    zones = (Intl as unknown as { supportedValuesOf?: (k: string) => string[] }).supportedValuesOf?.('timeZone') ?? [];
  } catch {
    /* older browsers */
  }
  if (!zones.length) zones = ['Asia/Karachi', 'Asia/Dubai', 'Europe/London', 'America/New_York', 'UTC'];
  for (const z of [DEFAULT_TIMEZONE, 'Asia/Karachi']) if (!zones.includes(z)) zones.unshift(z);
  return zones.map((z) => ({ value: z, label: z.replace(/_/g, ' ') }));
})();
