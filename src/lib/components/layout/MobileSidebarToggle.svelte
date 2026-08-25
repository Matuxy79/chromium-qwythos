<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';

	import { showSidebar } from '$lib/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	const i18n = getContext<Writable<I18n>>('i18n');

	const toggleSidebar = () => {
		showSidebar.update((isOpen) => !isOpen);
	};
</script>

<Tooltip
	content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
	touch={false}
	interactive={false}
	className="flex"
>
	<button
		id="sidebar-toggle-button"
		type="button"
		class="flex min-h-11 min-w-11 cursor-pointer touch-manipulation items-center justify-center rounded-xl text-gray-500 transition hover:bg-gray-100 active:scale-95 dark:text-gray-400 dark:hover:bg-gray-850 dark:hover:text-gray-200"
		aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
		aria-pressed={$showSidebar}
		on:click|stopPropagation={toggleSidebar}
	>
		<span class="flex size-8 items-center justify-center rounded-lg">
			<Sidebar className="size-4" />
		</span>
	</button>
</Tooltip>
