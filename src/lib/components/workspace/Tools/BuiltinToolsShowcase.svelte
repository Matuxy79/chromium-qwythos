<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { fly, scale } from 'svelte/transition';
	import { quintOut, elasticOut } from 'svelte/easing';

	const i18n = getContext('i18n');

	export let onNavigate: (path: string) => void = () => {};
	export let onConfigure: (toolId: string) => void = () => {};

	interface ToolCard {
		id: string;
		name: string;
		tier: string;
		tierColor: string;
		tierGlow: string;
		icon: string;
		description: string;
		stats: { label: string; value: string }[];
		xp: number;
		maxXp: number;
		gradient: string;
		borderGradient: string;
		particleColor: string;
		howTo: string;
		prompt: string;
		route?: string;
		configurable?: boolean;
	}

	const tools: ToolCard[] = [
		{
			id: 'council',
			name: 'LLM Council',
			tier: 'LEGENDARY',
			tierColor: '#fbbf24',
			tierGlow: 'rgba(251, 191, 36, 0.4)',
			icon: '👑',
			description:
				'Summon a council of AI models to deliberate your question. Each model answers independently, then peer-ranks all responses. The chairman synthesizes the ultimate answer.',
			stats: [
				{ label: 'Stage 1', value: 'Parallel Answers' },
				{ label: 'Stage 2', value: 'Peer Ranking' },
				{ label: 'Stage 3', value: 'Chairman Synthesis' }
			],
			xp: 3,
			maxXp: 3,
			gradient: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
			borderGradient: 'linear-gradient(135deg, #fbbf24, #f59e0b, #d97706, #fbbf24)',
			particleColor: '#fbbf24',
			howTo: "Set COUNCIL_MODELS or pass a comma-separated models list per call",
			prompt: 'Use the LLM council to help me decide: ',
			route: '/council',
			configurable: true
		},
		{
			id: 'subagent',
			name: 'Sub-Agent',
			tier: 'EPIC',
			tierColor: '#a78bfa',
			tierGlow: 'rgba(167, 139, 250, 0.4)',
			icon: '🤖',
			description:
				'Delegate a focused task to an autonomous sub-agent. It runs in its own chat context with full tool access, then reports back with results.',
			stats: [
				{ label: 'Mode', value: 'Single Focus' },
				{ label: 'Context', value: 'Isolated Chat' },
				{ label: 'Tools', value: 'Full Access' }
			],
			xp: 2,
			maxXp: 3,
			gradient: 'linear-gradient(135deg, #1a1a2e 0%, #1e1b3a 50%, #2d1b69 100%)',
			borderGradient: 'linear-gradient(135deg, #a78bfa, #8b5cf6, #7c3aed, #a78bfa)',
			particleColor: '#a78bfa',
			howTo: 'Use run_sub_agent(description, prompt)',
			prompt: 'Delegate this to a sub-agent: '
		},
		{
			id: 'parallel',
			name: 'Parallel Agents',
			tier: 'RARE',
			tierColor: '#38bdf8',
			tierGlow: 'rgba(56, 189, 248, 0.4)',
			icon: '⚡',
			description:
				'Launch up to 5 sub-agents simultaneously. Each tackles a different task in parallel, dramatically reducing wait time for multi-part work.',
			stats: [
				{ label: 'Max Agents', value: '5 Concurrent' },
				{ label: 'Execution', value: 'Parallel' },
				{ label: 'Speedup', value: 'Up to 5×' }
			],
			xp: 1,
			maxXp: 3,
			gradient: 'linear-gradient(135deg, #0f172a 0%, #0c1e3a 50%, #0e3654 100%)',
			borderGradient: 'linear-gradient(135deg, #38bdf8, #0ea5e9, #0284c7, #38bdf8)',
			particleColor: '#38bdf8',
			howTo: 'Use run_parallel_sub_agents(tasks=[…])',
			prompt: 'Run this as parallel sub-agents: '
		}
	];

	let hoveredCard: string | null = null;
	let mounted = false;
	let particles: { id: number; x: number; y: number; size: number; delay: number; color: string }[] =
		[];

	const launchTool = (tool: ToolCard) => {
		if (tool.route) {
			onNavigate(tool.route);
			return;
		}
		onNavigate(`/?q=${encodeURIComponent(tool.prompt)}&submit=false`);
	};

	onMount(() => {
		mounted = true;
		// Generate floating particles
		for (let i = 0; i < 20; i++) {
			particles.push({
				id: i,
				x: Math.random() * 100,
				y: Math.random() * 100,
				size: Math.random() * 3 + 1,
				delay: Math.random() * 6,
				color: tools[Math.floor(Math.random() * tools.length)].particleColor
			});
		}
		particles = particles;
	});
</script>

<div class="builtin-showcase" class:mounted>
	<!-- Floating particles background -->
	<div class="particles-container">
		{#each particles as p (p.id)}
			<div
				class="particle"
				style="
					left: {p.x}%;
					top: {p.y}%;
					width: {p.size}px;
					height: {p.size}px;
					background: {p.color};
					animation-delay: {p.delay}s;
				"
			/>
		{/each}
	</div>

	<!-- Header -->
	{#if mounted}
		<div class="showcase-header" in:fly={{ y: -20, duration: 600, delay: 100, easing: quintOut }}>
			<div class="header-icon">⚔️</div>
			<h2 class="header-title">Native Power-Ups</h2>
			<p class="header-subtitle">
				Built-in abilities ready to deploy — no custom tools needed
			</p>
		</div>
	{/if}

	<!-- Cards Grid -->
	<div class="cards-grid">
		{#each tools as tool, idx (tool.id)}
			{#if mounted}
				<div
					class="tool-card"
					class:hovered={hoveredCard === tool.id}
					style="
						--card-gradient: {tool.gradient};
						--border-gradient: {tool.borderGradient};
						--tier-color: {tool.tierColor};
						--tier-glow: {tool.tierGlow};
						--particle-color: {tool.particleColor};
					"
					in:scale={{
						duration: 500,
						delay: 200 + idx * 150,
						start: 0.8,
						opacity: 0,
						easing: elasticOut
					}}
					on:mouseenter={() => (hoveredCard = tool.id)}
					on:mouseleave={() => (hoveredCard = null)}
					role="article"
				>
					<!-- Animated border -->
					<div class="card-border" />

					<!-- Card content -->
					<div class="card-inner">
						<!-- Tier badge -->
						<div class="tier-badge">
							<span class="tier-dot" />
							<span class="tier-text">{tool.tier}</span>
						</div>

						<!-- Icon & Name -->
						<div class="card-header">
							<div class="icon-container">
								<span class="tool-icon">{tool.icon}</span>
								<div class="icon-ring" />
								<div class="icon-ring icon-ring-2" />
							</div>
							<h3 class="tool-name">{tool.name}</h3>
						</div>

						<!-- Description -->
						<p class="tool-description">{tool.description}</p>

						<!-- Stats -->
						<div class="stats-grid">
							{#each tool.stats as stat}
								<div class="stat-item">
									<span class="stat-label">{stat.label}</span>
									<span class="stat-value">{stat.value}</span>
								</div>
							{/each}
						</div>

						<!-- XP Bar -->
						<div class="xp-section">
							<div class="xp-header">
								<span class="xp-label">POWER LEVEL</span>
								<span class="xp-value">{tool.xp}/{tool.maxXp}</span>
							</div>
							<div class="xp-bar">
								<div
									class="xp-fill"
									style="width: {(tool.xp / tool.maxXp) * 100}%"
								/>
								<div class="xp-shimmer" />
							</div>
						</div>

						<!-- How to use -->
						<div class="how-to">
							<code class="how-to-code">{tool.howTo}</code>
						</div>

						<!-- Launch -->
						<div class="launch-row">
							<button
								type="button"
								class="launch-btn"
								aria-label={tool.route
									? `Open ${tool.name}`
									: `Try ${tool.name} in a new chat`}
								on:click={() => launchTool(tool)}
							>
								<span>{tool.route ? 'Open' : 'Try it'}</span>
								<span class="launch-arrow" aria-hidden="true">→</span>
							</button>
							{#if tool.configurable}
								<button
									type="button"
									class="configure-btn"
									aria-label={`Configure ${tool.name}`}
									on:click={() => onConfigure(tool.id)}
								>
									Configure
								</button>
							{/if}
						</div>
					</div>
				</div>
			{/if}
		{/each}
	</div>

	<!-- Bottom hint -->
	{#if mounted}
		<div class="bottom-hint" in:fly={{ y: 20, duration: 600, delay: 800, easing: quintOut }}>
			<div class="hint-icon">💡</div>
			<span>Enable native function calling in a chat to unlock these abilities. Toggle per model in <strong>Model Editor → Builtin Tools</strong>.</span>
		</div>
	{/if}
</div>

<style>
	.builtin-showcase {
		position: relative;
		padding: 1.5rem 0.5rem 2rem;
		overflow: hidden;
		opacity: 0;
		transform: translateY(8px);
		transition: opacity 0.4s ease, transform 0.4s ease;
	}

	.builtin-showcase.mounted {
		opacity: 1;
		transform: translateY(0);
	}

	/* Particles */
	.particles-container {
		position: absolute;
		inset: 0;
		pointer-events: none;
		overflow: hidden;
	}

	.particle {
		position: absolute;
		border-radius: 50%;
		opacity: 0.15;
		animation: float-particle 8s infinite ease-in-out;
	}

	@keyframes float-particle {
		0%,
		100% {
			transform: translateY(0) translateX(0) scale(1);
			opacity: 0.1;
		}
		25% {
			transform: translateY(-30px) translateX(15px) scale(1.5);
			opacity: 0.25;
		}
		50% {
			transform: translateY(-15px) translateX(-10px) scale(1);
			opacity: 0.15;
		}
		75% {
			transform: translateY(-40px) translateX(20px) scale(1.3);
			opacity: 0.2;
		}
	}

	/* Header */
	.showcase-header {
		text-align: center;
		margin-bottom: 1.75rem;
		position: relative;
		z-index: 1;
	}

	.header-icon {
		font-size: 1.75rem;
		margin-bottom: 0.5rem;
		filter: drop-shadow(0 0 8px rgba(251, 191, 36, 0.3));
		animation: pulse-glow 3s infinite ease-in-out;
	}

	@keyframes pulse-glow {
		0%,
		100% {
			filter: drop-shadow(0 0 8px rgba(251, 191, 36, 0.2));
		}
		50% {
			filter: drop-shadow(0 0 16px rgba(251, 191, 36, 0.5));
		}
	}

	.header-title {
		font-size: 1.125rem;
		font-weight: 700;
		letter-spacing: 0.05em;
		background: linear-gradient(135deg, #e2e8f0, #f8fafc);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
		margin: 0 0 0.25rem;
	}

	:global(.dark) .header-title {
		background: linear-gradient(135deg, #e2e8f0, #f8fafc);
		-webkit-background-clip: text;
		background-clip: text;
	}

	:global(:not(.dark)) .header-title {
		background: linear-gradient(135deg, #1e293b, #334155);
		-webkit-background-clip: text;
		background-clip: text;
	}

	.header-subtitle {
		font-size: 0.75rem;
		color: #64748b;
		margin: 0;
	}

	/* Cards Grid */
	.cards-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
		gap: 1rem;
		position: relative;
		z-index: 1;
	}

	/* Card */
	.tool-card {
		position: relative;
		border-radius: 16px;
		cursor: default;
		transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1),
			box-shadow 0.3s ease;
	}

	.tool-card:hover {
		transform: translateY(-4px) scale(1.01);
	}

	.tool-card.hovered {
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3),
			0 0 20px var(--tier-glow);
	}

	/* Animated border */
	.card-border {
		position: absolute;
		inset: 0;
		border-radius: 16px;
		padding: 1.5px;
		background: var(--border-gradient);
		background-size: 300% 300%;
		animation: gradient-spin 4s linear infinite;
		-webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
		-webkit-mask-composite: xor;
		mask-composite: exclude;
		opacity: 0.6;
		transition: opacity 0.3s ease;
	}

	.tool-card:hover .card-border {
		opacity: 1;
	}

	@keyframes gradient-spin {
		0% {
			background-position: 0% 50%;
		}
		50% {
			background-position: 100% 50%;
		}
		100% {
			background-position: 0% 50%;
		}
	}

	/* Card inner */
	.card-inner {
		background: var(--card-gradient);
		border-radius: 16px;
		padding: 1.25rem;
		position: relative;
		overflow: hidden;
	}

	:global(:not(.dark)) .card-inner {
		background: linear-gradient(
			135deg,
			rgba(248, 250, 252, 0.95) 0%,
			rgba(241, 245, 249, 0.95) 50%,
			rgba(226, 232, 240, 0.95) 100%
		);
	}

	/* Tier badge */
	.tier-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.15rem 0.6rem;
		border-radius: 999px;
		font-size: 0.6rem;
		font-weight: 800;
		letter-spacing: 0.12em;
		color: var(--tier-color);
		background: rgba(0, 0, 0, 0.3);
		border: 1px solid rgba(255, 255, 255, 0.06);
		margin-bottom: 0.75rem;
	}

	:global(:not(.dark)) .tier-badge {
		background: rgba(0, 0, 0, 0.06);
		border-color: rgba(0, 0, 0, 0.08);
	}

	.tier-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--tier-color);
		box-shadow: 0 0 6px var(--tier-glow);
		animation: tier-pulse 2s infinite ease-in-out;
	}

	@keyframes tier-pulse {
		0%,
		100% {
			box-shadow: 0 0 4px var(--tier-glow);
		}
		50% {
			box-shadow: 0 0 10px var(--tier-glow), 0 0 20px var(--tier-glow);
		}
	}

	.tier-text {
		text-transform: uppercase;
	}

	/* Card header */
	.card-header {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 0.75rem;
	}

	.icon-container {
		position: relative;
		width: 44px;
		height: 44px;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	.tool-icon {
		font-size: 1.5rem;
		z-index: 2;
		position: relative;
		filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
		transition: transform 0.3s ease;
	}

	.tool-card:hover .tool-icon {
		transform: scale(1.15) rotate(-5deg);
	}

	.icon-ring {
		position: absolute;
		inset: 0;
		border-radius: 50%;
		border: 1.5px solid var(--tier-color);
		opacity: 0.2;
		animation: ring-expand 3s infinite ease-out;
	}

	.icon-ring-2 {
		animation-delay: 1.5s;
	}

	@keyframes ring-expand {
		0% {
			transform: scale(0.8);
			opacity: 0.3;
		}
		100% {
			transform: scale(1.6);
			opacity: 0;
		}
	}

	.tool-name {
		font-size: 1rem;
		font-weight: 700;
		margin: 0;
		color: #f1f5f9;
		letter-spacing: 0.02em;
	}

	:global(:not(.dark)) .tool-name {
		color: #1e293b;
	}

	/* Description */
	.tool-description {
		font-size: 0.7rem;
		line-height: 1.5;
		color: #94a3b8;
		margin: 0 0 0.875rem;
	}

	:global(:not(.dark)) .tool-description {
		color: #64748b;
	}

	/* Stats */
	.stats-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 0.5rem;
		margin-bottom: 0.875rem;
	}

	.stat-item {
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
		padding: 0.4rem 0.5rem;
		border-radius: 8px;
		background: rgba(255, 255, 255, 0.03);
		border: 1px solid rgba(255, 255, 255, 0.04);
		transition: background 0.2s ease, border-color 0.2s ease;
	}

	:global(:not(.dark)) .stat-item {
		background: rgba(0, 0, 0, 0.02);
		border-color: rgba(0, 0, 0, 0.05);
	}

	.tool-card:hover .stat-item {
		background: rgba(255, 255, 255, 0.06);
		border-color: rgba(255, 255, 255, 0.08);
	}

	:global(:not(.dark)) .tool-card:hover .stat-item {
		background: rgba(0, 0, 0, 0.04);
		border-color: rgba(0, 0, 0, 0.08);
	}

	.stat-label {
		font-size: 0.55rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: #64748b;
		font-weight: 600;
	}

	.stat-value {
		font-size: 0.65rem;
		color: #cbd5e1;
		font-weight: 500;
	}

	:global(:not(.dark)) .stat-value {
		color: #334155;
	}

	/* XP Bar */
	.xp-section {
		margin-bottom: 0.75rem;
	}

	.xp-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 0.3rem;
	}

	.xp-label {
		font-size: 0.55rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: #64748b;
		font-weight: 700;
	}

	.xp-value {
		font-size: 0.6rem;
		font-weight: 700;
		color: var(--tier-color);
		font-variant-numeric: tabular-nums;
	}

	.xp-bar {
		height: 4px;
		background: rgba(255, 255, 255, 0.06);
		border-radius: 999px;
		overflow: hidden;
		position: relative;
	}

	:global(:not(.dark)) .xp-bar {
		background: rgba(0, 0, 0, 0.08);
	}

	.xp-fill {
		height: 100%;
		background: linear-gradient(90deg, var(--tier-color), color-mix(in srgb, var(--tier-color), white 30%));
		border-radius: 999px;
		transition: width 1s cubic-bezier(0.34, 1.56, 0.64, 1);
		position: relative;
	}

	.xp-shimmer {
		position: absolute;
		inset: 0;
		background: linear-gradient(
			90deg,
			transparent 0%,
			rgba(255, 255, 255, 0.15) 50%,
			transparent 100%
		);
		animation: shimmer 2.5s infinite linear;
	}

	@keyframes shimmer {
		0% {
			transform: translateX(-100%);
		}
		100% {
			transform: translateX(100%);
		}
	}

	/* How to use */
	.how-to {
		margin-top: 0.25rem;
	}

	.how-to-code {
		display: block;
		font-size: 0.6rem;
		padding: 0.35rem 0.55rem;
		border-radius: 6px;
		background: rgba(0, 0, 0, 0.25);
		color: #94a3b8;
		font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace;
		border: 1px solid rgba(255, 255, 255, 0.04);
		overflow-x: auto;
		white-space: nowrap;
	}

	:global(:not(.dark)) .how-to-code {
		background: rgba(0, 0, 0, 0.04);
		color: #475569;
		border-color: rgba(0, 0, 0, 0.06);
	}

	/* Launch row */
	.launch-row {
		display: flex;
		align-items: stretch;
		gap: 0.5rem;
		margin-top: 0.75rem;
	}

	/* Launch button */
	.launch-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.35rem;
		flex: 1;
		padding: 0.45rem 0.75rem;
		border-radius: 8px;
		border: 1px solid var(--tier-color);
		background: transparent;
		color: var(--tier-color);
		font-size: 0.7rem;
		font-weight: 700;
		letter-spacing: 0.02em;
		cursor: pointer;
		transition: background 0.2s ease, transform 0.2s ease;
	}

	.configure-btn {
		flex-shrink: 0;
		padding: 0.45rem 0.75rem;
		border-radius: 8px;
		border: 1px solid rgba(148, 163, 184, 0.35);
		background: transparent;
		color: #94a3b8;
		font-size: 0.7rem;
		font-weight: 600;
		letter-spacing: 0.02em;
		cursor: pointer;
		transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
	}

	.configure-btn:hover,
	.configure-btn:focus-visible {
		background: rgba(148, 163, 184, 0.1);
		border-color: #94a3b8;
		color: #cbd5e1;
	}

	.configure-btn:focus-visible {
		outline: 2px solid #94a3b8;
		outline-offset: 2px;
	}

	:global(:not(.dark)) .configure-btn {
		color: #64748b;
		border-color: rgba(100, 116, 139, 0.3);
	}

	:global(:not(.dark)) .configure-btn:hover,
	:global(:not(.dark)) .configure-btn:focus-visible {
		background: rgba(100, 116, 139, 0.08);
		border-color: #64748b;
		color: #334155;
	}

	.launch-btn:hover,
	.launch-btn:focus-visible {
		background: var(--tier-glow);
		transform: translateY(-1px);
	}

	.launch-btn:focus-visible {
		outline: 2px solid var(--tier-color);
		outline-offset: 2px;
	}

	.launch-btn:active {
		transform: translateY(0);
	}

	.launch-arrow {
		transition: transform 0.2s ease;
	}

	.launch-btn:hover .launch-arrow {
		transform: translateX(2px);
	}

	/* Bottom hint */
	.bottom-hint {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-top: 1.5rem;
		padding: 0.75rem 1rem;
		border-radius: 12px;
		background: rgba(251, 191, 36, 0.04);
		border: 1px solid rgba(251, 191, 36, 0.1);
		font-size: 0.7rem;
		color: #94a3b8;
		line-height: 1.5;
		position: relative;
		z-index: 1;
	}

	:global(:not(.dark)) .bottom-hint {
		background: rgba(251, 191, 36, 0.06);
		border-color: rgba(251, 191, 36, 0.15);
		color: #64748b;
	}

	.bottom-hint strong {
		color: #fbbf24;
	}

	:global(:not(.dark)) .bottom-hint strong {
		color: #b45309;
	}

	.hint-icon {
		font-size: 1rem;
		flex-shrink: 0;
	}

	/* Responsive */
	@media (max-width: 640px) {
		.cards-grid {
			grid-template-columns: 1fr;
		}

		.stats-grid {
			grid-template-columns: 1fr;
		}
	}
</style>
