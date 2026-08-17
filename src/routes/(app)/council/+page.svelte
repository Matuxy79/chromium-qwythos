<script lang="ts">
	import { onMount, getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { getCouncilRunConfig, runCouncil } from '$lib/apis/council';
	import type { CouncilRunConfig, CouncilRunResult } from '$lib/apis/council';
	import { models as modelsStore } from '$lib/stores';

	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	const i18n = getContext('i18n');

	type Turn = {
		id: string;
		question: string;
		status: 'loading' | 'done' | 'error';
		result?: CouncilRunResult;
		error?: string;
		expanded: boolean;
	};

	let turns: Turn[] = [];
	let input = '';
	let textareaEl: HTMLTextAreaElement;
	let scrollEl: HTMLDivElement;
	let sending = false;

	let runConfig: CouncilRunConfig | null = null;
	let loadingConfig = true;

	const modelName = (id: string) => $modelsStore.find((m) => m.id === id)?.name ?? id;

	onMount(async () => {
		try {
			runConfig = await getCouncilRunConfig(localStorage.token);
		} catch (error) {
			runConfig = { enabled: false, models: [], chairman_model: '' };
		}
		loadingConfig = false;
	});

	const resize = () => {
		if (!textareaEl) return;
		textareaEl.style.height = 'auto';
		textareaEl.style.height = `${Math.min(textareaEl.scrollHeight, 200)}px`;
	};

	const scrollToBottom = async () => {
		await tick();
		scrollEl?.scrollTo({ top: scrollEl.scrollHeight, behavior: 'smooth' });
	};

	const send = async () => {
		const question = input.trim();
		if (!question || sending) return;
		if (!runConfig?.enabled) {
			toast.error($i18n.t('The council is not configured yet.'));
			return;
		}

		const turn: Turn = {
			id: `${turns.length}-${question.length}-${Math.random().toString(36).slice(2)}`,
			question,
			status: 'loading',
			expanded: false
		};
		turns = [...turns, turn];
		input = '';
		await tick();
		resize();
		scrollToBottom();

		sending = true;
		try {
			const result = await runCouncil(localStorage.token, question);
			turns = turns.map((t) => (t.id === turn.id ? { ...t, status: 'done', result } : t));
		} catch (error) {
			turns = turns.map((t) =>
				t.id === turn.id
					? { ...t, status: 'error', error: (error as any)?.detail ?? String(error) }
					: t
			);
		}
		sending = false;
		scrollToBottom();
	};

	const onKeydown = (e: KeyboardEvent) => {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			send();
		}
	};

	const toggleExpanded = (id: string) => {
		turns = turns.map((t) => (t.id === id ? { ...t, expanded: !t.expanded } : t));
	};
</script>

<div class="flex flex-col h-full">
	<div bind:this={scrollEl} class="flex-1 overflow-y-auto px-3 sm:px-4">
		<div class="max-w-3xl mx-auto w-full py-4 flex flex-col gap-4">
			{#if loadingConfig}
				<div class="flex justify-center py-10">
					<Spinner className="size-5" />
				</div>
			{:else if !runConfig?.enabled}
				<div class="flex flex-col items-center text-center gap-2 py-16 px-4">
					<div class="text-2xl" aria-hidden="true">👑</div>
					<div class="text-sm font-medium">{$i18n.t('The council is not configured yet')}</div>
					<div class="text-xs text-gray-500 max-w-sm">
						{$i18n.t(
							'An admin needs to pick 2-5 models for the council in Workspace → Tools → LLM Council → Configure.'
						)}
					</div>
					<a
						href="/workspace/tools"
						class="mt-2 text-xs px-3 py-1.5 rounded-full bg-black text-white dark:bg-white dark:text-black"
					>
						{$i18n.t('Go to Workspace → Tools')}
					</a>
				</div>
			{:else if turns.length === 0}
				<div class="flex flex-col items-center text-center gap-2 py-16 px-4">
					<div class="text-2xl" aria-hidden="true">👑</div>
					<div class="text-sm font-medium">{$i18n.t('Ask the council')}</div>
					<div class="text-xs text-gray-500 max-w-sm">
						{$i18n.t(
							'Your question goes to {{count}} models in parallel, they peer-rank each other, and a chairman model synthesizes the final answer.',
							{ count: runConfig.models.length }
						)}
					</div>
					<div class="flex flex-wrap justify-center gap-1.5 mt-1">
						{#each runConfig.models as modelId}
							<span
								class="text-[11px] px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300"
							>
								{modelName(modelId)}
							</span>
						{/each}
					</div>
				</div>
			{/if}

			{#each turns as turn (turn.id)}
				<div class="flex flex-col gap-2">
					<div
						class="self-end max-w-[90%] sm:max-w-[75%] rounded-2xl rounded-br-sm bg-gray-900 text-white dark:bg-white dark:text-black px-3.5 py-2 text-sm whitespace-pre-wrap break-words"
					>
						{turn.question}
					</div>

					<div
						class="self-start w-full sm:max-w-[85%] rounded-2xl rounded-bl-sm border border-gray-100 dark:border-gray-800 px-3.5 py-3"
					>
						{#if turn.status === 'loading'}
							<div class="flex items-center gap-2 text-xs text-gray-500">
								<Spinner className="size-3.5" />
								{$i18n.t('Council deliberating…')}
							</div>
						{:else if turn.status === 'error'}
							<div class="text-xs text-red-500">{turn.error}</div>
						{:else if turn.result}
							<div
								class="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-amber-600 dark:text-amber-400 mb-1.5"
							>
								<span aria-hidden="true">👑</span>
								{$i18n.t('Chairman synthesis')} · {modelName(turn.result.chairman)}
							</div>
							<div class="text-sm">
								<Markdown
									id={`council-${turn.id}-final`}
									content={turn.result.final_answer}
									done={true}
								/>
							</div>

							<button
								type="button"
								class="mt-3 flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
								on:click={() => toggleExpanded(turn.id)}
							>
								<span class="transition-transform {turn.expanded ? 'rotate-180' : ''}">
									<ChevronDown className="size-3" />
								</span>
								{turn.expanded
									? $i18n.t('Hide individual answers & ranking')
									: $i18n.t('Show individual answers & ranking ({{count}})', {
											count: turn.result.responses.length
										})}
							</button>

							{#if turn.expanded}
								<div class="mt-2 flex flex-col gap-3">
									{#if turn.result.failed_models.length > 0}
										<div class="text-xs text-gray-400">
											{$i18n.t('Did not respond: {{models}}', {
												models: turn.result.failed_models.map(modelName).join(', ')
											})}
										</div>
									{/if}
									{#each turn.result.ranking as item (item.model)}
										{@const response = turn.result.responses.find((r) => r.model === item.model)}
										<div class="rounded-xl bg-gray-50 dark:bg-gray-900 px-3 py-2.5">
											<div class="flex items-center justify-between gap-2 mb-1">
												<div class="text-xs font-medium flex items-center gap-1.5">
													<span
														class="inline-flex items-center justify-center size-4 rounded-full bg-gray-200 dark:bg-gray-700 text-[10px]"
													>
														{item.rank}
													</span>
													{modelName(item.model)}
												</div>
												{#if item.avg_rank !== null}
													<div class="text-[10px] text-gray-400">
														{$i18n.t('avg rank {{rank}}', { rank: item.avg_rank })}
													</div>
												{/if}
											</div>
											{#if response}
												<div class="text-xs text-gray-600 dark:text-gray-400">
													<Markdown
														id={`council-${turn.id}-${item.model}`}
														content={response.answer}
														done={true}
														compactPreview
													/>
												</div>
											{/if}
										</div>
									{/each}
								</div>
							{/if}
						{/if}
					</div>
				</div>
			{/each}
		</div>
	</div>

	<div class="shrink-0 border-t border-gray-50 dark:border-gray-850 px-3 sm:px-4 py-2.5">
		<div class="max-w-3xl mx-auto w-full flex items-end gap-2">
			<textarea
				bind:this={textareaEl}
				bind:value={input}
				on:input={resize}
				on:keydown={onKeydown}
				rows="1"
				placeholder={$i18n.t('Ask the council…')}
				disabled={!runConfig?.enabled || loadingConfig}
				class="flex-1 resize-none max-h-[200px] rounded-2xl border border-gray-100 dark:border-gray-800 bg-transparent px-3.5 py-2.5 text-sm outline-hidden focus:border-gray-300 dark:focus:border-gray-600 disabled:opacity-50"
			></textarea>
			<button
				type="button"
				on:click={send}
				disabled={!input.trim() || sending || !runConfig?.enabled}
				aria-label={$i18n.t('Send')}
				class="shrink-0 size-9 flex items-center justify-center rounded-full bg-black text-white dark:bg-white dark:text-black disabled:opacity-30 transition"
			>
				{#if sending}
					<Spinner className="size-4" />
				{:else}
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 24 24"
						fill="currentColor"
						class="size-4"
					>
						<path
							fill-rule="evenodd"
							d="M12 20a1 1 0 0 1-1-1V7.414L6.707 11.707a1 1 0 1 1-1.414-1.414l6-6a1 1 0 0 1 1.414 0l6 6a1 1 0 0 1-1.414 1.414L13 7.414V19a1 1 0 0 1-1 1Z"
							clip-rule="evenodd"
						/>
					</svg>
				{/if}
			</button>
		</div>
	</div>
</div>
