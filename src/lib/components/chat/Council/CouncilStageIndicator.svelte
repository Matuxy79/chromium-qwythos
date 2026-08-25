<script lang="ts">
	import { getContext } from 'svelte';
	import { type Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import Spinner from '../../common/Spinner.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');

	// 0 = idle, 1 = answers, 2 = ranking, 3 = synthesis, 4 = complete
	export let stage: number;
	export let chairmanName: string | null = null;

	const stages = [
		{
			id: 1,
			title: () => $i18n.t('Stage 1 · Independent answers'),
			detail: () => $i18n.t('Every council model answers the question in parallel.')
		},
		{
			id: 2,
			title: () => $i18n.t('Stage 2 · Peer ranking'),
			detail: () => $i18n.t('Models rank the anonymized answers; ballots are averaged.')
		},
		{
			id: 3,
			title: () => $i18n.t('Stage 3 · Chairman synthesis'),
			detail: () => $i18n.t('The chairman weighs the ranking and synthesizes the final answer.')
		}
	];

	$: stateOf = (id: number) =>
		stage === 4 || stage > id ? 'done' : stage === id ? 'active' : 'pending';
</script>

<ol class="flex flex-col">
	{#each stages as s, i}
		<li class="relative flex gap-2.5 pb-4">
			{#if i < stages.length - 1}
				<span
					class="absolute left-[11px] top-6 bottom-0 w-px {stateOf(s.id) === 'done'
						? 'bg-green-400/60'
						: 'bg-gray-200 dark:bg-gray-700'}"
				></span>
			{/if}

			<span
				class="relative z-10 flex size-6 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold {stateOf(
					s.id
				) === 'done'
					? 'bg-green-500 text-white'
					: stateOf(s.id) === 'active'
						? 'bg-amber-400/20 text-amber-600 ring-1 ring-amber-400 dark:text-amber-300'
						: 'bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500'}"
			>
				{#if stateOf(s.id) === 'done'}
					<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" class="size-3">
						<path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
					</svg>
				{:else if stateOf(s.id) === 'active'}
					<Spinner className="size-3" />
				{:else}
					{s.id}
				{/if}
			</span>

			<div class="min-w-0 flex-1 pt-0.5">
				<div
					class="text-[12px] font-medium {stateOf(s.id) === 'pending'
						? 'text-gray-400 dark:text-gray-500'
						: 'text-gray-800 dark:text-gray-200'}"
				>
					{s.title()}
					{#if s.id === 3 && chairmanName}
						<span class="text-gray-400 dark:text-gray-500">· {chairmanName}</span>
					{/if}
				</div>
				{#if stateOf(s.id) === 'active'}
					<div class="mt-0.5 text-[11px] text-gray-500 dark:text-gray-400">{s.detail()}</div>
				{/if}
			</div>
		</li>
	{/each}

	<li class="relative flex gap-2.5">
		<span
			class="relative z-10 flex size-6 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold {stage ===
			4
				? 'bg-green-500 text-white'
				: 'bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500'}"
		>
			{#if stage === 4}
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" class="size-3">
					<path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
				</svg>
			{:else}
				★
			{/if}
		</span>
		<div class="min-w-0 flex-1 pt-0.5">
			<div
				class="text-[12px] font-medium {stage === 4
					? 'text-gray-800 dark:text-gray-200'
					: 'text-gray-400 dark:text-gray-500'}"
			>
				{$i18n.t('Final answer')}
			</div>
		</div>
	</li>
</ol>