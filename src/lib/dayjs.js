import dayjs from 'dayjs';

// Every locale, but behind a dynamic import so only the active one ships on the
// critical path. Statically importing all 101 put a ~123KB chunk in the eager
// graph of every app route to make ~1.2KB of it reachable.
//
// These are written out as literals rather than built from a template string:
// Vite can only analyse `import()` when the specifier is static, so
// `import(`dayjs/locale/${lang}`)` silently fails to bundle anything. An
// import.meta.glob over /node_modules would also work, but it assumes a flat
// hoisted node_modules and breaks under pnpm or a workspace layout.
/** @type {Record<string, () => Promise<unknown>>} */
const LOCALE_LOADERS = {
	af: () => import('dayjs/locale/af'),
	am: () => import('dayjs/locale/am'),
	ar: () => import('dayjs/locale/ar'),
	az: () => import('dayjs/locale/az'),
	be: () => import('dayjs/locale/be'),
	bg: () => import('dayjs/locale/bg'),
	bi: () => import('dayjs/locale/bi'),
	bm: () => import('dayjs/locale/bm'),
	bn: () => import('dayjs/locale/bn'),
	bo: () => import('dayjs/locale/bo'),
	br: () => import('dayjs/locale/br'),
	bs: () => import('dayjs/locale/bs'),
	ca: () => import('dayjs/locale/ca'),
	cs: () => import('dayjs/locale/cs'),
	cv: () => import('dayjs/locale/cv'),
	cy: () => import('dayjs/locale/cy'),
	da: () => import('dayjs/locale/da'),
	de: () => import('dayjs/locale/de'),
	dv: () => import('dayjs/locale/dv'),
	el: () => import('dayjs/locale/el'),
	en: () => import('dayjs/locale/en'),
	eo: () => import('dayjs/locale/eo'),
	es: () => import('dayjs/locale/es'),
	et: () => import('dayjs/locale/et'),
	eu: () => import('dayjs/locale/eu'),
	fa: () => import('dayjs/locale/fa'),
	fi: () => import('dayjs/locale/fi'),
	fo: () => import('dayjs/locale/fo'),
	fr: () => import('dayjs/locale/fr'),
	fy: () => import('dayjs/locale/fy'),
	ga: () => import('dayjs/locale/ga'),
	gd: () => import('dayjs/locale/gd'),
	gl: () => import('dayjs/locale/gl'),
	gu: () => import('dayjs/locale/gu'),
	he: () => import('dayjs/locale/he'),
	hi: () => import('dayjs/locale/hi'),
	hr: () => import('dayjs/locale/hr'),
	ht: () => import('dayjs/locale/ht'),
	hu: () => import('dayjs/locale/hu'),
	id: () => import('dayjs/locale/id'),
	is: () => import('dayjs/locale/is'),
	it: () => import('dayjs/locale/it'),
	ja: () => import('dayjs/locale/ja'),
	jv: () => import('dayjs/locale/jv'),
	ka: () => import('dayjs/locale/ka'),
	kk: () => import('dayjs/locale/kk'),
	km: () => import('dayjs/locale/km'),
	kn: () => import('dayjs/locale/kn'),
	ko: () => import('dayjs/locale/ko'),
	ku: () => import('dayjs/locale/ku'),
	ky: () => import('dayjs/locale/ky'),
	lb: () => import('dayjs/locale/lb'),
	lo: () => import('dayjs/locale/lo'),
	lt: () => import('dayjs/locale/lt'),
	lv: () => import('dayjs/locale/lv'),
	me: () => import('dayjs/locale/me'),
	mi: () => import('dayjs/locale/mi'),
	mk: () => import('dayjs/locale/mk'),
	ml: () => import('dayjs/locale/ml'),
	mn: () => import('dayjs/locale/mn'),
	mr: () => import('dayjs/locale/mr'),
	ms: () => import('dayjs/locale/ms'),
	mt: () => import('dayjs/locale/mt'),
	my: () => import('dayjs/locale/my'),
	nb: () => import('dayjs/locale/nb'),
	ne: () => import('dayjs/locale/ne'),
	nl: () => import('dayjs/locale/nl'),
	nn: () => import('dayjs/locale/nn'),
	pl: () => import('dayjs/locale/pl'),
	pt: () => import('dayjs/locale/pt'),
	ro: () => import('dayjs/locale/ro'),
	ru: () => import('dayjs/locale/ru'),
	rw: () => import('dayjs/locale/rw'),
	sd: () => import('dayjs/locale/sd'),
	se: () => import('dayjs/locale/se'),
	si: () => import('dayjs/locale/si'),
	sk: () => import('dayjs/locale/sk'),
	sl: () => import('dayjs/locale/sl'),
	sq: () => import('dayjs/locale/sq'),
	sr: () => import('dayjs/locale/sr'),
	ss: () => import('dayjs/locale/ss'),
	sv: () => import('dayjs/locale/sv'),
	sw: () => import('dayjs/locale/sw'),
	ta: () => import('dayjs/locale/ta'),
	te: () => import('dayjs/locale/te'),
	tet: () => import('dayjs/locale/tet'),
	tg: () => import('dayjs/locale/tg'),
	th: () => import('dayjs/locale/th'),
	tk: () => import('dayjs/locale/tk'),
	tlh: () => import('dayjs/locale/tlh'),
	tr: () => import('dayjs/locale/tr'),
	tzl: () => import('dayjs/locale/tzl'),
	tzm: () => import('dayjs/locale/tzm'),
	uk: () => import('dayjs/locale/uk'),
	ur: () => import('dayjs/locale/ur'),
	uz: () => import('dayjs/locale/uz'),
	vi: () => import('dayjs/locale/vi'),
	yo: () => import('dayjs/locale/yo'),
	zh: () => import('dayjs/locale/zh'),
	'zh-tw': () => import('dayjs/locale/zh-tw'),
	'en-gb': () => import('dayjs/locale/en-gb')
};

/** @type {Map<string, Promise<unknown>>} */
const loaded = new Map();

/**
 * Resolve a language tag to a locale dayjs ships, or null if it has none.
 *
 * Accepts i18next-style tags (`pt-BR`, `zh-TW`) and falls back to the base
 * language when the region-specific locale isn't available.
 *
 * @param {string} lang
 * @returns {string | null}
 */
const resolveLocaleKey = (lang) => {
	if (!lang || typeof lang !== 'string') return null;

	const normalized = lang.toLowerCase();
	if (LOCALE_LOADERS[normalized]) return normalized;

	const base = normalized.split('-')[0];
	return LOCALE_LOADERS[base] ? base : null;
};

/**
 * Register a single dayjs locale and return the tag to pass to `dayjs.locale()`.
 *
 * Returns 'en' — built into dayjs itself, needing no import — for anything
 * unrecognised, so the result is always safe to hand to `dayjs.locale()`.
 *
 * @param {string} lang
 * @returns {Promise<string>}
 */
export const loadDayjsLocale = async (lang) => {
	const key = resolveLocaleKey(lang);
	if (!key || key === 'en') return 'en';

	if (!loaded.has(key)) {
		loaded.set(
			key,
			LOCALE_LOADERS[key]().catch((/** @type {unknown} */ error) => {
				console.error(`Failed to load dayjs locale "${key}":`, error);
				// Drop the rejected promise so a later attempt can retry.
				loaded.delete(key);
				throw error;
			})
		);
	}

	try {
		await loaded.get(key);
	} catch {
		return 'en';
	}

	return key;
};

/**
 * Apply the first supported locale from an i18next `languages` list.
 *
 * Components used to inline this as a loop that called `dayjs.locale()` inside
 * a try/catch and broke on the first "success" — but dayjs.locale() never
 * throws for an unknown locale, it just keeps the current one, so the loop
 * always stopped on the first entry regardless of whether it was supported.
 * Resolving against the loader table gives the fallback the loop was after.
 *
 * @param {string[] | string | undefined} locales
 * @returns {Promise<string>}
 */
export const applyDayjsLocale = async (locales) => {
	const candidates = Array.isArray(locales) ? locales : locales ? [locales] : [];

	for (const candidate of candidates) {
		if (!resolveLocaleKey(candidate)) continue;
		const resolved = await loadDayjsLocale(candidate);
		dayjs.locale(resolved);
		return resolved;
	}

	dayjs.locale('en');
	return 'en';
};

export default dayjs;
