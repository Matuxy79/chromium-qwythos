<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { user, config, mobile, showSearch, showSidebar } from '$lib/stores';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import { getMenuItemMeta, isMenuItemVisible, getActiveMenuItemId } from './navItems';

	import EditPencilIcon from './icons/EditPencil.svelte';
	import SearchIcon from './icons/Search.svelte';
	import NotesIcon from './icons/Notes.svelte';
	import WorkspaceIcon from './icons/Workspace.svelte';
	import ClockIcon from './icons/Clock.svelte';
	import CalendarIcon from './icons/Calendar.svelte';
	import CodeIcon from './icons/Code.svelte';
	import UserIcon from './icons/User.svelte';

	const i18n = getContext('i18n');

	export let newChatHandler: () => void | Promise<void>;
	export let itemClickHandler: () => void | Promise<void>;

	export let side: 'top' | 'bottom' = 'bottom';
	export let align: 'start' | 'end' = 'start';

	let show = false;

	$: activeMenuItemId = getActiveMenuItemId($page.url.pathname);

	const navIds = ['workspace', 'notes', 'automations', 'calendar', 'playground'];

	const TOOL_CARDS = {
		council: {
			icon: '👑',
			tier: 'Legendary',
			label: 'LLM Council',
			description: 'Deliberate questions across multiple models with peer ranking and chairman synthesis',
			prompt: 'Use the LLM council to help me decide: ',
			tierClass: 'text-amber-700 dark:text-amber-400 bg-amber-400/20',
			cardClass:
				'border-amber-400/25 dark:border-amber-400/20 bg-amber-400/5 hover:bg-amber-400/10 dark:bg-amber-400/[0.05] dark:hover:bg-amber-400/10'
		},
		subagents: {
			icon: '🤖',
			tier: 'Epic',
			label: 'Sub-agents',
			description: 'Delegate focused work to parallel sub-agents',
			prompt: 'Delegate this to sub-agents: ',
			tierClass: 'text-violet-700 dark:text-violet-400 bg-violet-400/20',
			cardClass:
				'border-violet-400/25 dark:border-violet-400/20 bg-violet-400/5 hover:bg-violet-400/10 dark:bg-violet-400/[0.05] dark:hover:bg-violet-400/10'
		}
	} as const;

	const launchTool = async (id: keyof typeof TOOL_CARDS) => {
		show = false;
		await newChatHandler();
		goto(`/?q=${encodeURIComponent($i18n.t(TOOL_CARDS[id].prompt))}&submit=false`);
	};

	const goAdmin = async (e: MouseEvent) => {
		if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) {
			return;
		}
		e.preventDefault();
		show = false;
		goto('/admin');

		if ($mobile) {
			await tick();
			showSidebar.set(false);
		}
	};

	const rowClass =
		'flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[13px] transition select-none cursor-pointer hover:bg-gray-50/40 dark:hover:bg-gray-800/40';
</script>

<Dropdown bind:show {side} {align} contentClass="z-50">
	<slot />

	<div slot="content">
		<div
			class="w-[300px] max-w-[92vw] rounded-2xl p-1.5 border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-850 text-gray-900 dark:text-white shadow-lg"
		>
			<div class="flex flex-col gap-0.5">
				<a
					href="/"
					draggable="false"
					class={rowClass}
					aria-label={$i18n.t('New Chat')}
					on:click={() => {
						show = false;
						newChatHandler();
					}}
				>
					<EditPencilIcon className="size-3.5" strokeWidth="1.5" />
					<span class="truncate">{$i18n.t('New Chat')}</span>
				</a>

				<button
					type="button"
					class={rowClass}
					aria-label={$i18n.t('Search')}
					on:click={() => {
						show = false;
						showSearch.set(true);
					}}
				>
					<SearchIcon className="size-3.5" strokeWidth="1.5" />
					<span class="truncate">{$i18n.t('Search')}</span>
				</button>

				{#each navIds as id (id)}
					{@const meta = getMenuItemMeta(id)}
					{#if meta && isMenuItemVisible(id, $user, $config)}
						<a
							href={meta.href}
							draggable="false"
							class="{rowClass} {id === activeMenuItemId
								? 'bg-black/[0.035] dark:bg-white/[0.045]'
								: ''}"
							aria-label={$i18n.t(meta.label)}
							on:click={() => {
								show = false;
								itemClickHandler();
							}}
						>
							{#if id === 'notes'}
								<NotesIcon className="size-3.5" strokeWidth="1.5" />
							{:else if id === 'workspace'}
								<WorkspaceIcon className="size-3.5" strokeWidth="1.5" />
							{:else if id === 'automations'}
								<ClockIcon className="size-3.5" strokeWidth="1.5" />
							{:else if id === 'calendar'}
								<CalendarIcon className="size-3.5" strokeWidth="1.5" />
							{:else if id === 'playground'}
								<CodeIcon className="size-3.5" strokeWidth="1.5" />
							{/if}
							<span class="truncate">{$i18n.t(meta.label)}</span>
						</a>
					{/if}
				{/each}

				{#if $user?.role === 'admin'}
					<a href="/admin" draggable="false" class={rowClass} aria-label={$i18n.t('Admin Panel')} on:click={goAdmin}>
						<UserIcon className="size-3.5" strokeWidth="1.5" />
						<span class="truncate">{$i18n.t('Admin Panel')}</span>
					</a>
				{/if}
			</div>

			{#if ($config?.features?.enable_council ?? false) || ($config?.features?.enable_subagents ?? false)}
				<hr class="border-gray-50/30 dark:border-gray-800/30 my-1 mx-1" />

				<div
					class="px-1.5 pb-0.5 flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500"
				>
					<span aria-hidden="true">⚡</span><span>{$i18n.t('Power-Ups')}</span>
				</div>

				<div class="flex flex-col gap-1.5 px-0.5 pb-0.5">
					{#each Object.entries(TOOL_CARDS) as [id, card] (id)}
						{#if $config?.features?.[`enable_${id}`]}
							<button
								type="button"
								class="flex items-start gap-2 rounded-xl border px-2.5 py-2 text-left transition-all hover:scale-[1.015] {card.cardClass}"
								on:click={() => launchTool(id)}
							>
								<span class="text-base leading-none mt-0.5" aria-hidden="true">{card.icon}</span>
								<span class="min-w-0 flex-1">
									<span class="flex items-center gap-1.5">
										<span class="text-[13px] font-medium text-gray-800 dark:text-gray-100"
											>{$i18n.t(card.label)}</span
										>
										<span
											class="rounded-full px-1.5 py-px text-[9px] font-bold uppercase tracking-wide {card.tierClass}"
											>{$i18n.t(card.tier)}</span
										>
									</span>
									<span class="block text-[11px] leading-snug text-gray-500 dark:text-gray-400 line-clamp-2">
										{$i18n.t(card.description)}
									</span>
								</span>
							</button>
						{/if}
					{/each}
				</div>
			{/if}
		</div>
	</div>
</Dropdown>
