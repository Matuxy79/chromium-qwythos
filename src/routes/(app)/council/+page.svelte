<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { LLM_COUNCIL_MODEL_ID } from '$lib/constants';

	// The standalone /council page has been replaced by the integrated chat flow.
	// Selecting "LLM Council" in the model picker routes through the normal chat
	// pipeline, so chats are persisted and appear in the sidebar.
	onMount(() => {
		goto(`/?model=${encodeURIComponent(LLM_COUNCIL_MODEL_ID)}`, { replaceState: true });
	});
</script>
