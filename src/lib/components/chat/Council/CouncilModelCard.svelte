<script lang="ts">
	import { getContext } from 'svelte';
	import { type Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { models } from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import ProfileImage from '../Messages/ProfileImage.svelte';
	import Spinner from '../../common/Spinner.svelte';
	import type { CouncilModelState } from '$lib/stores';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let model: CouncilModelState;
	export let stage: number;
	export let isChairman = false;

	$: meta = $models.find((m) => m.id === model.id);
	$: modelName = meta?.name ?? model.id;

	let expanded = false;

	$: statusLabel =
		model.status === 'thinking'
			? stage === 2
				? $i18n.t('Ranking answers…')
				: $i18n.t('Thinking…')
			: model.status === 'completed'
				? stage === 2
					? $i18n.t('Ballot cast')
					: $i18n.t('Answered')
				: model.status === 'failed'
					? $i18n.t('No response')
					: $i18n.t('Waiting…');

	$: statusColor =
		model.status === 'thinking'
			? 'text-amber-500'
			: model.status === 'completed'
				? 'text-green-600 dark:text-green-400'
				: model.status === 'failed'
					? 'text-red-500'
					: 'text-gray-400 dark:text-gray-500';

	$: dotColor =
		model.status === 'thinking'
			? 'bg-amber-400'
			: model.status === 'completed'
				? 'bg-green-500'
				: model.status === 'failed'
					? 'bg-red-500'
					: 'bg-gray-300 dark:bg-gray-600';

	const rankMedal = (rank: number | null) => {
		if (rank === 1) return '🥇';
		if (rank === 2) return '🥈';
		if (rank === 3) return '🥉';
		return null;
	};
</script>

<div
	class="rounded-xl border border-gray-100 bg-white p-2.5 shadow-sm dark:border-gray-800 dark:bg-gray-900"
>
	<div class="flex items-center gap-2">
		<div class="relative shrink-0">
			<ProfileImage
				className="size-7"
				src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model.id}&lang=${$i18n.language}`}
			/>
			<span
				class="absolute -bottom-0.5 -right-0.5 size-2.5 rounded-full ring-2 ring-white dark:ring-gray-900 {dotColor} {model.status ===
				'thinking'
					? 'animate-pulse'
					: ''}"
			></span>
		</div>

		<div class="min-w-0 flex-1">
			<div class="flex items-center gap-1.5">
				<span class="truncate text-[13px] font-medium text-gray-800 dark:text-gray-200">
					{modelName}
				</span>
				{#if isChairman}
					<span
						class="shrink-0 rounded-md bg-black/5 px-1.5 py-0.5 text-[10px] font-medium text-gray-600 dark:bg-white/10 dark:text-gray-300"
					>
						{$i18n.t('Chairman')}
					</span>
				{/if}
			</div>
			<div class="flex items-center gap-1.5 text-[11px] {statusColor}">
				{#if model.status === 'thinking'}
					<Spinner className="size-2.5" />
				{/if}
				<span class="truncate">{statusLabel}</span>
			</div>
		</div>

		<div class="flex shrink-0 flex-col items-end gap-1">
			<span
				class="rounded-md bg-gray-100 px-1.5 py-0.5 text-[10px] font-semibold text-gray-500 dark:bg-gray-800 dark:text-gray-400"
			>
				{model.label}
			</span>
			{#if model.rank !== null}
				<span class="text-[11px] font-medium text-gray-600 dark:text-gray-300">
					{rankMedal(model.rank) ?? `#${model.rank}`}
					{#if model.avgRank !== null}
						<span class="text-gray-400 dark:text-gray-500">({model.avgRank})</span>
					{/if}
				</span>
			{/if}
		</div>
	</div>

	{#if model.status === 'completed' && model.answer}
		<button
			type="button"
			class="mt-2 w-full cursor-pointer rounded-lg bg-gray-50 px-2.5 py-1.5 text-left dark:bg-gray-800/60"
			on:click={() => (expanded = !expanded)}
		>
			<div
				class="text-[12px] leading-relaxed text-gray-600 dark:text-gray-300 {expanded
					? 'whitespace-pre-wrap'
					: 'line-clamp-2'}"
			>
				{model.answer}
			</div>
			<div class="mt-1 text-[10px] font-medium text-gray-400 dark:text-gray-500">
				{expanded ? $i18n.t('Collapse') : $i18n.t('Expand')}
			</div>
		</button>
	{:else if model.status === 'failed'}
		<div
			class="mt-2 rounded-lg bg-red-50 px-2.5 py-1.5 text-[12px] text-red-500 dark:bg-red-950/40 dark:text-red-400"
		>
			{$i18n.t('This model did not produce an answer.')}
		</div>
	{/if}
</div>