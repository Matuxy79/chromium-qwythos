<script lang="ts">
	import { getContext } from 'svelte';
	import { type Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { councilState, models, showControls } from '$lib/stores';
	import CouncilStageIndicator from './CouncilStageIndicator.svelte';
	import CouncilModelCard from './CouncilModelCard.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');

	$: state = $councilState;

	$: chairmanMeta = $models.find((m) => m.id === state.chairman);
	$: chairmanName = chairmanMeta?.name ?? state.chairman;

	$: hasDeliberation = state.models.length > 0 || state.stage > 0;

	$: stageHeading =
		state.stage === 1
			? $i18n.t('Collecting answers…')
			: state.stage === 2
				? $i18n.t('Peer ranking…')
				: state.stage === 3
					? $i18n.t('Chairman synthesis…')
					: state.stage === 4
						? $i18n.t('Deliberation complete')
						: $i18n.t('Idle');

	let finalExpanded = false;
</script>

<div class="flex h-full min-h-0 flex-col">
	<!-- Header -->
	<div class="flex items-center justify-between px-3 pt-2 pb-1 shrink-0">
		<div class="flex items-center gap-2">
			<span class="text-base">🏛️</span>
			<span class="text-sm font-semibold text-gray-800 dark:text-gray-200">
				{$i18n.t('LLM Council')}
			</span>
			{#if state.active}
				<span
					class="rounded-md bg-amber-400/15 px-1.5 py-0.5 text-[10px] font-semibold text-amber-600 dark:text-amber-300"
				>
					{$i18n.t('Live')}
				</span>
			{/if}
		</div>
		<button
			class="cursor-pointer p-1 rounded-lg text-gray-500 dark:text-gray-400"
			on:click={() => showControls.set(false)}
			aria-label={$i18n.t('Close')}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="1.5"
				class="size-4"
			>
				<path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
			</svg>
		</button>
	</div>

	{#if !hasDeliberation}
		<div class="flex flex-1 items-center justify-center px-6">
			<div class="text-center text-[12px] text-gray-400 dark:text-gray-500">
				<div class="mb-2 text-2xl">🏛️</div>
				{$i18n.t('No council deliberation yet. Select the LLM Council model and send a message to watch the models deliberate here.')}
			</div>
		</div>
	{:else}
		<div class="flex-1 min-h-0 overflow-y-auto px-3 pb-3 scrollbar-hidden">
			<!-- Question -->
			{#if state.question}
				<div
					class="mb-3 rounded-xl bg-gray-50 px-3 py-2 text-[12px] text-gray-600 dark:bg-gray-800/60 dark:text-gray-300"
				>
					<div class="mb-0.5 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
						{$i18n.t('Question')}
					</div>
					<div class="line-clamp-3">{state.question}</div>
				</div>
			{/if}

			<!-- Stage timeline -->
			<div class="mb-3">
				<CouncilStageIndicator stage={state.stage} chairmanName={chairmanName} />
			</div>

			{#if state.error}
				<div
					class="mb-3 rounded-xl bg-red-50 px-3 py-2 text-[12px] text-red-600 dark:bg-red-950/40 dark:text-red-400"
				>
					{state.error}
				</div>
			{/if}

			<!-- Stage 1: model answers -->
			<div class="mb-1 flex items-center justify-between">
				<span class="text-[11px] font-semibold uppercase tracking-wide text-gray-400">
					{$i18n.t('Council models')}
				</span>
				{#if state.active && state.stage === 1}
					<span class="text-[11px] text-gray-400">{stageHeading}</span>
				{/if}
			</div>
			<div class="mb-3 flex flex-col gap-2">
				{#each state.models as model (model.id)}
					<CouncilModelCard {model} stage={state.stage} isChairman={model.id === state.chairman} />
				{/each}
			</div>

			<!-- Stage 2: ranking -->
			{#if state.ranking.length > 0}
				<div class="mb-1">
					<span class="text-[11px] font-semibold uppercase tracking-wide text-gray-400">
						{$i18n.t('Aggregate ranking')}
					</span>
				</div>
				<div class="mb-3 overflow-hidden rounded-xl border border-gray-100 dark:border-gray-800">
					{#each state.ranking as entry, i (entry.model)}
						<div
							class="flex items-center gap-2 px-2.5 py-1.5 text-[12px] {i %
							2
								? 'bg-gray-50/60 dark:bg-gray-800/40'
								: 'bg-white dark:bg-gray-900'}"
						>
							<span class="w-5 text-center font-semibold text-gray-500 dark:text-gray-400">
								{entry.rank === 1 ? '🥇' : entry.rank === 2 ? '🥈' : entry.rank === 3 ? '🥉' : `#${entry.rank}`}
							</span>
							<span class="min-w-0 flex-1 truncate text-gray-700 dark:text-gray-300">
								{$models.find((m) => m.id === entry.model)?.name ?? entry.model}
							</span>
							{#if entry.avgRank !== null}
								<span class="text-[11px] text-gray-400 dark:text-gray-500">
									{$i18n.t('avg')} {entry.avgRank}
								</span>
							{/if}
						</div>
					{/each}
				</div>
			{/if}

			<!-- Stage 3: final answer -->
			{#if state.finalAnswer}
				<div class="mb-1">
					<span class="text-[11px] font-semibold uppercase tracking-wide text-gray-400">
						{$i18n.t('Final answer')} · {chairmanName ?? ''}
					</span>
				</div>
				<button
					type="button"
					class="w-full cursor-pointer rounded-xl border border-green-200 bg-green-50/60 px-3 py-2 text-left dark:border-green-900/50 dark:bg-green-950/30"
					on:click={() => (finalExpanded = !finalExpanded)}
				>
					<div
						class="text-[12px] leading-relaxed text-gray-700 dark:text-gray-200 {finalExpanded
							? 'whitespace-pre-wrap'
							: 'line-clamp-4'}"
					>
						{state.finalAnswer}
					</div>
					<div class="mt-1 text-[10px] font-medium text-gray-400 dark:text-gray-500">
						{finalExpanded ? $i18n.t('Collapse') : $i18n.t('Expand')}
					</div>
				</button>
			{/if}
		</div>
	{/if}
</div>