// highlight.js, split so the common languages ship on the critical path and the
// long tail loads on demand.
//
// `highlight.js` (the package root) registers all 194 grammars, which built out
// to a 1.1MB chunk that every app route pulled in eagerly -- rendering any
// markdown was enough to require it. `highlight.js/lib/common` is the same
// engine with the ~36 most-used languages, around a tenth of the size.
//
// Nothing is lost, only deferred: lib/core.js constructs a single module-level
// HLJS instance, and both lib/common.js and the full lib/index.js register onto
// *that* object. Rollup dedupes them to one instance, so importing the full set
// later mutates the same singleton this module exports.
import hljs from 'highlight.js/lib/common';

let fullLanguageSet: Promise<void> | null = null;

/**
 * Register the remaining ~158 grammars onto the shared hljs instance.
 *
 * Idempotent and safe to call concurrently — the in-flight promise is reused.
 */
export const ensureAllLanguages = (): Promise<void> => {
	if (!fullLanguageSet) {
		fullLanguageSet = import('highlight.js')
			.then(() => undefined)
			.catch((error) => {
				console.error('Failed to load the full highlight.js language set:', error);
				// Allow a later call to retry rather than caching the failure.
				fullLanguageSet = null;
				throw error;
			});
	}
	return fullLanguageSet;
};

/**
 * Ensure `lang` is registered, pulling the full grammar set only if it isn't
 * already one of the common ones.
 *
 * @returns whether hljs can highlight `lang` after this call.
 */
export const ensureLanguage = async (lang: string | null | undefined): Promise<boolean> => {
	if (!lang) return false;
	if (hljs.getLanguage(lang)) return true;

	try {
		await ensureAllLanguages();
	} catch {
		return false;
	}

	return !!hljs.getLanguage(lang);
};

export default hljs;
