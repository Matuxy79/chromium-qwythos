<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	import { getOpenRouterCatalog, type OpenRouterCatalogModel } from '$lib/apis/openai';

	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	let q = $page.url.searchParams.get('q') ?? '';
	let catalog: OpenRouterCatalogModel[] | null = null;
	let loading = false;
	let loadError = '';
	let debounceTimer: ReturnType<typeof setTimeout>;
	let requestSeq = 0;

	const formatContext = (n?: number | null) => {
		if (!n || n <= 0) return '';
		if (n >= 1000) return `${Math.round(n / 100) / 10}K`;
		return `${n}`;
	};

	// OpenRouter pricing is USD per token; display per 1M tokens.
	const perMillion = (value?: string) => {
		const num = Number(value);
		if (!isFinite(num) || num <= 0) return null;
		const perM = num * 1_000_000;
		return `$${perM < 1 ? perM.toFixed(3) : perM.toFixed(2)}`;
	};

	const priceLabel = (model: OpenRouterCatalogModel) => {
		const input = perMillion(model.pricing?.prompt);
		const output = perMillion(model.pricing?.completion);
		if (!input && !output) return '';
		return `${$i18n.t('{{input}}/M in · {{output}}/M out', {
			input: input ?? '—',
			output: output ?? '—'
		})}`;
	};

	const syncUrl = (value: string) => {
		const url = new URL($page.url);
		if (value) {
			url.searchParams.set('q', value);
		} else {
			url.searchParams.delete('q');
		}
		history.replaceState(history.state, '', url);
	};

	const loadCatalog = async (query: string) => {
		const seq = ++requestSeq;
		loading = true;
		loadError = '';
		try {
			const res = await getOpenRouterCatalog(localStorage.token, query);
			if (seq !== requestSeq) return; // stale response
			catalog = res?.data ?? [];
		} catch (err) {
			if (seq !== requestSeq) return;
			catalog = null;
			loadError = `${err}`;
		} finally {
			if (seq === requestSeq) {
				loading = false;
			}
		}
	};

	const onInput = () => {
		clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			syncUrl(q);
			loadCatalog(q);
		}, 300);
	};

	const clearSearch = () => {
		q = '';
		syncUrl(q);
		loadCatalog(q);
	};

	onMount(() => {
		loadCatalog(q);
	});
</script>

<div class="mt-6 px-2 pb-8">
	<div class="mb-1 flex items-center gap-1.5 text-[11px] font-normal text-gray-400 dark:text-gray-600">
		<GlobeAlt className="size-3" />
		{$i18n.t('Discover models on OpenRouter')}
	</div>

	<div class="mb-2 flex h-8 w-full items-center gap-2">
		<div class="flex min-w-0 flex-1 items-center">
			<div class="self-center ml-1 mr-3">
				<Search className="size-3.5" />
			</div>
			<input
				class="w-full bg-transparent py-1 text-sm outline-hidden"
				bind:value={q}
				aria-label={$i18n.t('Search OpenRouter models')}
				placeholder={$i18n.t('Search OpenRouter models (e.g. venice, qwen, glm)')}
				maxlength="200"
				on:input={onInput}
			/>
			{#if q}
				<div class="self-center pl-1.5">
					<button
						class="rounded-full p-0.5 transition hover:bg-gray-100 dark:hover:bg-gray-900"
						aria-label={$i18n.t('Clear search')}
						on:click={clearSearch}
					>
						<XMark className="size-3" strokeWidth="2" />
					</button>
				</div>
			{/if}
		</div>
	</div>

	{#if loading && catalog === null}
		<div class="flex w-full items-center justify-center py-6">
			<Spinner className="size-4" />
		</div>
	{:else if loadError}
		<div class="py-2 text-xs text-gray-500 dark:text-gray-400">
			{$i18n.t('Could not load the OpenRouter catalog: {{error}}', { error: loadError })}
		</div>
	{:else if catalog !== null}
		<div class="mb-1 text-[11px] text-gray-400 dark:text-gray-600">
			{$i18n.t('{{count}} models', { count: catalog.length })}
		</div>
		<div class="max-h-72 overflow-y-auto">
			{#each catalog as model (model.id)}
				<button
					class="flex w-full cursor-pointer items-center justify-between gap-3 rounded px-1 py-1.5 text-left transition hover:bg-gray-50 dark:hover:bg-gray-900"
					on:click={() => goto(`/?model=${encodeURIComponent(model.id)}`)}
					title={model.id}
				>
					<div class="min-w-0">
						<div class="line-clamp-1 text-[13px] font-normal text-gray-700 dark:text-gray-200">
							{model.name}
						</div>
						<div class="line-clamp-1 text-xs text-gray-500 dark:text-gray-500">
							{model.id}
							{#if formatContext(model.context_length)}
								· {formatContext(model.context_length)} {$i18n.t('context')}
							{/if}
							{#if priceLabel(model)}
								· {priceLabel(model)}
							{/if}
						</div>
					</div>
					<ChevronRight className="size-3.5 shrink-0 text-gray-400 dark:text-gray-600" />
				</button>
			{:else}
				<div class="py-2 text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('No OpenRouter models match your search.')}
				</div>
			{/each}
		</div>
	{/if}
</div>
