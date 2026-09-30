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

/** Languages clinicians most often practise in here (ISO 639-1). */
export const LANGUAGE_OPTIONS: Option[] = ['en', 'ur', 'pa', 'sd', 'ps', 'ar', 'fa', 'hi', 'bn'].map((c) => ({
  value: c,
  label: displayName('language', c),
}));

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
