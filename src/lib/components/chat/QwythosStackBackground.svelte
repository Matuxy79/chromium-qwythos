<script lang="ts">
	import { renderTier } from '$lib/runtime/renderGovernor';

	const streams = [
		{
			id: 'claude',
			name: 'CLAUDE',
			trait: 'REASON • ALIGN',
			color: '#f39a62',
			path: 'M720 345 C548 300 390 140 112 124',
			labelX: 120,
			labelY: 116,
			anchor: 'start',
			delay: -2
		},
		{
			id: 'gpt',
			name: 'GPT',
			trait: 'CREATE • TOOL',
			color: '#61e59a',
			path: 'M720 345 C525 344 342 270 86 292',
			labelX: 92,
			labelY: 282,
			anchor: 'start',
			delay: -8
		},
		{
			id: 'gemini',
			name: 'GEMINI',
			trait: 'SEE • SEARCH',
			color: '#55b8ff',
			path: 'M720 345 C520 404 330 456 106 494',
			labelX: 112,
			labelY: 486,
			anchor: 'start',
			delay: -13
		},
		{
			id: 'qwen',
			name: 'QWEN',
			trait: 'CONTEXT • CODE',
			color: '#9a7cff',
			path: 'M720 345 C570 480 405 620 154 676',
			labelX: 158,
			labelY: 668,
			anchor: 'start',
			delay: -5
		},
		{
			id: 'kimi',
			name: 'KIMI',
			trait: 'REMEMBER • SYNTHESIZE',
			color: '#5bc7ff',
			path: 'M720 345 C884 268 1046 134 1322 142',
			labelX: 1318,
			labelY: 134,
			anchor: 'end',
			delay: -10
		},
		{
			id: 'glm',
			name: 'GLM',
			trait: 'ACT • AUTOMATE',
			color: '#ff7668',
			path: 'M720 345 C936 326 1122 298 1350 326',
			labelX: 1342,
			labelY: 316,
			anchor: 'end',
			delay: -16
		},
		{
			id: 'minimax',
			name: 'MINIMAX',
			trait: 'SPEAK • EXPRESS',
			color: '#ff6db3',
			path: 'M720 345 C928 422 1120 510 1328 558',
			labelX: 1320,
			labelY: 548,
			anchor: 'end',
			delay: -12
		}
	] as const;
</script>

<div
	class="qwythos-stack"
	class:qwythos-stack--static={$renderTier === 'static'}
	aria-hidden="true"
>
	<div class="qwythos-stack__aurora"></div>

	<svg viewBox="0 0 1440 800" preserveAspectRatio="xMidYMid slice" role="presentation">
		<defs>
			<radialGradient id="hive-core" cx="50%" cy="50%" r="50%">
				<stop offset="0" stop-color="#fff4c2" stop-opacity="0.9"></stop>
				<stop offset="0.18" stop-color="#f6c76a" stop-opacity="0.5"></stop>
				<stop offset="0.55" stop-color="#d69a39" stop-opacity="0.1"></stop>
				<stop offset="1" stop-color="#d69a39" stop-opacity="0"></stop>
			</radialGradient>
			<linearGradient id="source-column" x1="0" y1="0" x2="0" y2="1">
				<stop offset="0" stop-color="#f8d78a" stop-opacity="0"></stop>
				<stop offset="0.45" stop-color="#f8d78a" stop-opacity="0.7"></stop>
				<stop offset="1" stop-color="#f8d78a" stop-opacity="0"></stop>
			</linearGradient>
			<filter id="stream-glow" x="-30%" y="-30%" width="160%" height="160%">
				<feGaussianBlur stdDeviation="2.2" result="blur"></feGaussianBlur>
				<feMerge>
					<feMergeNode in="blur"></feMergeNode>
					<feMergeNode in="SourceGraphic"></feMergeNode>
				</feMerge>
			</filter>
		</defs>

		<g class="field-geometry">
			<ellipse cx="720" cy="345" rx="248" ry="218"></ellipse>
			<ellipse cx="720" cy="345" rx="184" ry="162"></ellipse>
			<ellipse cx="720" cy="345" rx="116" ry="102"></ellipse>
			<path d="M472 345 H968"></path>
			<path d="M720 126 V564"></path>
			<path d="M545 190 L895 500"></path>
			<path d="M895 190 L545 500"></path>
		</g>

		<g class="orbit orbit--outer">
			<ellipse cx="720" cy="345" rx="296" ry="258"></ellipse>
			<ellipse cx="720" cy="345" rx="271" ry="238"></ellipse>
		</g>

		{#each streams as stream, index}
			<g
				class="stream"
				style={`--stream:${stream.color};--delay:${stream.delay}s;--index:${index}`}
			>
				<path id={`stack-stream-${stream.id}`} class="stream__base" d={stream.path}></path>
				<path class="stream__flow" d={stream.path}></path>
				<circle class="stream__source" cx="720" cy="345" r="2.5"></circle>
				<circle class="stream__runner" r="2.5">
					{#if $renderTier !== 'static'}
						<animateMotion
							dur={`${8.5 + index * 0.7}s`}
							begin={`${stream.delay}s`}
							repeatCount="indefinite"
						>
							<mpath href={`#stack-stream-${stream.id}`}></mpath>
						</animateMotion>
					{/if}
				</circle>
				<circle class="stream__terminal" cx={stream.labelX} cy={stream.labelY + 8} r="4"></circle>
				<circle class="stream__terminal-ring" cx={stream.labelX} cy={stream.labelY + 8} r="10"
				></circle>

				<text class="stream__label" x={stream.labelX} y={stream.labelY} text-anchor={stream.anchor}>
					{stream.name}
					<tspan class="stream__trait" x={stream.labelX} dy="18">{stream.trait}</tspan>
				</text>
			</g>
		{/each}

		<g class="source-field">
			<path class="source-field__column" d="M720 368 C704 470 732 585 720 748"></path>
			<ellipse class="source-field__ring source-field__ring--one" cx="720" cy="694" rx="112" ry="24"
			></ellipse>
			<ellipse class="source-field__ring source-field__ring--two" cx="720" cy="694" rx="176" ry="41"
			></ellipse>
			<ellipse
				class="source-field__ring source-field__ring--three"
				cx="720"
				cy="694"
				rx="242"
				ry="58"
			></ellipse>
		</g>

		<g class="hive">
			<circle class="hive__glow" cx="720" cy="345" r="84"></circle>
			<circle class="hive__ring hive__ring--one" cx="720" cy="345" r="58"></circle>
			<circle class="hive__ring hive__ring--two" cx="720" cy="345" r="40"></circle>
			<path class="hive__mark" d="M701 324 H727 L741 338 V360 H720 L732 372 H708 L696 360 V336 Z"
			></path>
			<circle class="hive__spark" cx="720" cy="345" r="3.5"></circle>
		</g>

		<text class="hive__caption" x="720" y="456" text-anchor="middle"> SEVEN MINDS • ONE HIVE </text>
	</svg>

	<div class="qwythos-stack__veil"></div>
</div>

<style>
	.qwythos-stack {
		--field-ink: rgba(19, 27, 38, 0.18);
		--field-label: rgba(18, 24, 34, 0.32);
		--field-veil: rgba(255, 255, 255, 0.82);

		position: absolute;
		inset: 0;
		z-index: 0;
		overflow: hidden;
		pointer-events: none;
		isolation: isolate;
		background:
			radial-gradient(circle at 50% 43%, rgba(225, 189, 107, 0.08), transparent 20%),
			radial-gradient(circle at 24% 42%, rgba(75, 170, 255, 0.06), transparent 30%),
			radial-gradient(circle at 78% 44%, rgba(175, 91, 255, 0.05), transparent 28%);
	}

	:global(.dark) .qwythos-stack {
		--field-ink: rgba(158, 191, 228, 0.14);
		--field-label: rgba(220, 231, 245, 0.44);
		--field-veil: rgba(23, 23, 23, 0.78);

		background:
			radial-gradient(circle at 50% 43%, rgba(246, 195, 92, 0.09), transparent 21%),
			radial-gradient(circle at 23% 42%, rgba(37, 134, 255, 0.08), transparent 32%),
			radial-gradient(circle at 78% 44%, rgba(146, 74, 255, 0.08), transparent 30%), #171717;
	}

	.qwythos-stack::before,
	.qwythos-stack::after {
		position: absolute;
		inset: -18%;
		z-index: -1;
		content: '';
		background-image:
			radial-gradient(circle, rgba(107, 190, 255, 0.42) 0 1px, transparent 1.6px),
			radial-gradient(circle, rgba(245, 191, 95, 0.25) 0 0.8px, transparent 1.4px);
		background-position:
			0 0,
			31px 47px;
		background-size:
			83px 79px,
			127px 113px;
		opacity: 0.25;
		mask-image: radial-gradient(ellipse at center, black 8%, transparent 76%);
		animation: star-drift 42s linear infinite;
	}

	.qwythos-stack::after {
		transform: scale(1.12) rotate(13deg);
		opacity: 0.16;
		animation-duration: 58s;
		animation-direction: reverse;
	}

	.qwythos-stack__aurora {
		position: absolute;
		inset: 4% 8%;
		border-radius: 50%;
		background: conic-gradient(
			from 30deg,
			rgba(84, 184, 255, 0.07),
			rgba(134, 86, 255, 0.08),
			rgba(255, 105, 168, 0.05),
			rgba(240, 151, 88, 0.06),
			rgba(77, 226, 148, 0.06),
			rgba(84, 184, 255, 0.07)
		);
		filter: blur(52px);
		opacity: 0.82;
		animation: aurora-breathe 12s ease-in-out infinite alternate;
	}

	svg {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		opacity: 0.86;
	}

	.field-geometry {
		fill: none;
		stroke: var(--field-ink);
		stroke-width: 0.8;
		stroke-dasharray: 2 8;
	}

	.orbit {
		fill: none;
		stroke: rgba(207, 168, 87, 0.18);
		stroke-width: 0.9;
		stroke-dasharray: 8 18 2 14;
		transform-box: view-box;
		transform-origin: 50% 43.125%;
		animation: orbit-spin 44s linear infinite;
	}

	.stream {
		color: var(--stream);
	}

	.stream__base,
	.stream__flow {
		fill: none;
		stroke-linecap: round;
	}

	.stream__base {
		stroke: var(--stream);
		stroke-width: 0.75;
		opacity: 0.25;
	}

	.stream__flow {
		stroke: var(--stream);
		stroke-width: 1.25;
		stroke-dasharray: 2 13 32 18;
		opacity: 0.7;
		filter: url('#stream-glow');
		animation: signal-flow 14s linear infinite;
		animation-delay: var(--delay);
	}

	.stream__source,
	.stream__runner,
	.stream__terminal {
		fill: var(--stream);
		filter: url('#stream-glow');
	}

	.stream__source {
		opacity: 0.62;
	}

	.stream__runner {
		opacity: 0.92;
	}

	.stream__terminal {
		opacity: 0.66;
		animation: terminal-pulse 4s ease-in-out infinite;
		animation-delay: var(--delay);
	}

	.stream__terminal-ring {
		fill: none;
		stroke: var(--stream);
		stroke-width: 0.8;
		opacity: 0.22;
	}

	.stream__label {
		fill: var(--stream);
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 13px;
		font-weight: 650;
		letter-spacing: 0.2em;
		opacity: 0.56;
	}

	.stream__trait {
		fill: var(--field-label);
		font-size: 7px;
		font-weight: 500;
		letter-spacing: 0.18em;
	}

	.source-field__column {
		fill: none;
		stroke: url('#source-column');
		stroke-width: 1.4;
		stroke-dasharray: 2 10 30 14;
		opacity: 0.42;
		animation: source-rise 12s linear infinite;
	}

	.source-field__ring {
		fill: none;
		stroke: rgba(232, 185, 91, 0.2);
		stroke-width: 0.8;
		stroke-dasharray: 3 9;
		transform-box: fill-box;
		transform-origin: center;
		animation: source-ring 8s ease-in-out infinite;
	}

	.source-field__ring--two {
		animation-delay: -2.6s;
	}

	.source-field__ring--three {
		animation-delay: -5.2s;
	}

	.hive__glow {
		fill: url('#hive-core');
		opacity: 0.46;
		animation: hive-breathe 6s ease-in-out infinite;
	}

	.hive__ring {
		fill: none;
		stroke: rgba(239, 195, 107, 0.42);
		stroke-width: 0.9;
		stroke-dasharray: 7 13 2 10;
		transform-box: fill-box;
		transform-origin: center;
		animation: orbit-spin 18s linear infinite;
	}

	.hive__ring--two {
		animation-direction: reverse;
		animation-duration: 13s;
	}

	.hive__mark {
		fill: none;
		stroke: rgba(248, 218, 150, 0.76);
		stroke-width: 1.35;
		stroke-linecap: round;
		stroke-linejoin: round;
	}

	.hive__spark {
		fill: #fff1b7;
		filter: url('#stream-glow');
		animation: terminal-pulse 3s ease-in-out infinite;
	}

	.hive__caption {
		fill: rgba(216, 183, 116, 0.3);
		font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
		font-size: 8px;
		letter-spacing: 0.36em;
	}

	.qwythos-stack__veil {
		position: absolute;
		inset: 0;
		background: radial-gradient(
			ellipse 34% 34% at 50% 48%,
			var(--field-veil) 0%,
			color-mix(in srgb, var(--field-veil) 70%, transparent) 50%,
			transparent 100%
		);
	}

	@keyframes signal-flow {
		to {
			stroke-dashoffset: -130;
		}
	}

	@keyframes source-rise {
		to {
			stroke-dashoffset: 120;
		}
	}

	@keyframes orbit-spin {
		to {
			transform: rotate(360deg);
		}
	}

	@keyframes terminal-pulse {
		0%,
		100% {
			opacity: 0.34;
		}
		50% {
			opacity: 0.9;
		}
	}

	@keyframes source-ring {
		0%,
		100% {
			transform: scale(0.94);
			opacity: 0.12;
		}
		50% {
			transform: scale(1.05);
			opacity: 0.34;
		}
	}

	@keyframes hive-breathe {
		0%,
		100% {
			transform: scale(0.92);
			opacity: 0.2;
		}
		50% {
			transform: scale(1.08);
			opacity: 0.48;
		}
	}

	@keyframes aurora-breathe {
		from {
			transform: scale(0.96) rotate(-2deg);
			opacity: 0.54;
		}
		to {
			transform: scale(1.05) rotate(3deg);
			opacity: 0.88;
		}
	}

	@keyframes star-drift {
		to {
			transform: translate3d(72px, 48px, 0);
		}
	}

	.qwythos-stack--static::before,
	.qwythos-stack--static::after,
	.qwythos-stack--static .qwythos-stack__aurora,
	.qwythos-stack--static .orbit,
	.qwythos-stack--static .stream__flow,
	.qwythos-stack--static .stream__terminal,
	.qwythos-stack--static .source-field__column,
	.qwythos-stack--static .source-field__ring,
	.qwythos-stack--static .hive__glow,
	.qwythos-stack--static .hive__ring,
	.qwythos-stack--static .hive__spark {
		animation: none !important;
	}

	@media (max-width: 800px) {
		.stream__label,
		.stream__terminal,
		.stream__terminal-ring,
		.hive__caption {
			display: none;
		}

		svg {
			opacity: 0.62;
		}

		.qwythos-stack__veil {
			background: radial-gradient(
				ellipse 68% 38% at 50% 48%,
				var(--field-veil) 0%,
				color-mix(in srgb, var(--field-veil) 72%, transparent) 58%,
				transparent 100%
			);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.qwythos-stack *,
		.qwythos-stack::before,
		.qwythos-stack::after {
			animation: none !important;
		}

		.stream__runner {
			display: none;
		}
	}
</style>
