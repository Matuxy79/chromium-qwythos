// What is held here reflects what the browser can breathe through.
// A slow device should not run the same constellation as a flagship phone,
// so the tier is adjusted against observed frame timing once the page is up.
// Boot hints are read once and sealed; only runtime frames are load-bearing.

import { writable, type Writable } from 'svelte/store';

export type RenderTier = 'static' | 'light' | 'full';

export const TIER_RANK: Record<RenderTier, number> = {
	static: 0,
	light: 1,
	full: 2
};

// Hysteresis gap between promote and demote thresholds prevents oscillation
// when the device sits at the boundary.
export const TIER_DEMOTE_FPS = 42;
export const TIER_PROMOTE_FPS = 57;
export const DEMOTE_WINDOW_MS = 2000;
export const PROMOTE_WINDOW_MS = 10000;
export const PROMOTE_CHECK_INTERVAL_MS = 250;
export const MIN_DEMOTE_SAMPLES = 20;
export const MIN_PROMOTE_SAMPLES = 30;
export const LONGTASK_DEMOTE_THRESHOLD = 3;
export const LONGTASK_DURATION_MS = 50;

type BrowserHints = {
	deviceMemory: number | undefined;
	hardwareConcurrency: number | undefined;
	saveData: boolean | undefined;
	prefersReducedMotion: boolean;
};

function detectBootHints(): Readonly<BrowserHints> {
	if (typeof navigator === 'undefined' || typeof window === 'undefined') {
		return Object.freeze({
			deviceMemory: undefined,
			hardwareConcurrency: undefined,
			saveData: undefined,
			prefersReducedMotion: false
		});
	}
	const nav = navigator as Navigator & {
		deviceMemory?: number;
		connection?: { saveData?: boolean };
	};
	const motionQuery =
		typeof window.matchMedia === 'function'
			? window.matchMedia('(prefers-reduced-motion: reduce)')
			: null;
	return Object.freeze({
		deviceMemory: nav.deviceMemory,
		hardwareConcurrency: nav.hardwareConcurrency,
		saveData: nav.connection?.saveData,
		prefersReducedMotion: Boolean(motionQuery?.matches)
	});
}

export const bootHints: Readonly<BrowserHints> = detectBootHints();

function pickInitialTier(hints: Readonly<BrowserHints>): RenderTier {
	if (hints.prefersReducedMotion) return 'static';
	if (hints.saveData) return 'static';
	return 'light';
}

export const renderTier: Writable<RenderTier> = writable(pickInitialTier(bootHints));

let currentTier: RenderTier = pickInitialTier(bootHints);
renderTier.subscribe((value) => {
	currentTier = value;
});

export function setRenderTier(next: RenderTier, reason: string): void {
	if (next === currentTier) return;
	renderTier.set(next);
	if (typeof window !== 'undefined') {
		try {
			window.dispatchEvent(
				new CustomEvent('qwythos:render-tier-change', {
					detail: { tier: next, reason, hints: bootHints }
				})
			);
		} catch {
			// CustomEvent may fail to construct in some test harnesses; ignore.
		}
	}
}

type StopFn = () => void;
let started = false;

type Sample = { t: number; dt: number };

export function startFrameGovernor(): StopFn {
	if (started || typeof window === 'undefined') {
		return () => {};
	}
	started = true;

	const samples: Sample[] = [];
	let lastFrame = performance.now();
	let longTaskCount = 0;
	let rafId = 0;
	let promoteTimer: ReturnType<typeof setInterval> | null = null;

	const resetBaseline = () => {
		samples.length = 0;
		lastFrame = performance.now();
		longTaskCount = 0;
	};

	const onVisibility = () => {
		if (!document.hidden) {
			resetBaseline();
		}
	};
	document.addEventListener('visibilitychange', onVisibility);

	let observer: PerformanceObserver | null = null;
	try {
		observer = new PerformanceObserver((list) => {
			for (const entry of list.getEntries()) {
				if (entry.duration > LONGTASK_DURATION_MS) longTaskCount += 1;
			}
		});
		observer.observe({ entryTypes: ['longtask'] });
	} catch {
		observer = null;
	}

	const prune = (cutoff: number) => {
		while (samples.length && samples[0].t < cutoff) {
			samples.shift();
		}
	};

	const evaluateDemote = () => {
		const now = lastFrame;
		const cutoff = now - DEMOTE_WINDOW_MS;
		prune(cutoff);
		if (samples.length < MIN_DEMOTE_SAMPLES) return;
		const span = samples[samples.length - 1].t - samples[0].t;
		if (span < DEMOTE_WINDOW_MS * 0.9) return;
		const total = samples.reduce((acc, s) => acc + s.dt, 0);
		const fps = (1000 * samples.length) / total;

		if (currentTier === 'full' && fps < TIER_DEMOTE_FPS) {
			setRenderTier('light', `fps-${fps.toFixed(1)}-longtask-${longTaskCount}`);
			return;
		}
		if (
			currentTier === 'light' &&
			(fps < TIER_DEMOTE_FPS || longTaskCount >= LONGTASK_DEMOTE_THRESHOLD)
		) {
			setRenderTier('static', `fps-${fps.toFixed(1)}-longtask-${longTaskCount}`);
		}
	};

	const onFrame = (now: number) => {
		rafId = requestAnimationFrame(onFrame);
		if (document.hidden) {
			lastFrame = now;
			return;
		}
		const dt = now - lastFrame;
		lastFrame = now;
		samples.push({ t: now, dt });
		evaluateDemote();
	};
	rafId = requestAnimationFrame(onFrame);

	const evaluatePromote = () => {
		if (document.hidden) return;
		const now = lastFrame;
		const cutoff = now - PROMOTE_WINDOW_MS;
		prune(cutoff);
		if (samples.length < MIN_PROMOTE_SAMPLES) return;
		const span = samples[samples.length - 1].t - samples[0].t;
		if (span < PROMOTE_WINDOW_MS * 0.9) return;
		const total = samples.reduce((acc, s) => acc + s.dt, 0);
		const fps = (1000 * samples.length) / total;
		if (currentTier === 'light' && fps > TIER_PROMOTE_FPS) {
			setRenderTier('full', `promoted-fps-${fps.toFixed(1)}`);
		}
	};
	promoteTimer = setInterval(evaluatePromote, PROMOTE_CHECK_INTERVAL_MS);

	return () => {
		cancelAnimationFrame(rafId);
		if (promoteTimer !== null) clearInterval(promoteTimer);
		document.removeEventListener('visibilitychange', onVisibility);
		if (observer) observer.disconnect();
		samples.length = 0;
		longTaskCount = 0;
		started = false;
	};
}
