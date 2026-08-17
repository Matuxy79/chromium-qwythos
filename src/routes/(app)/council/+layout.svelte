<script lang="ts">
	import { getContext } from 'svelte';
	import { WEBUI_NAME } from '$lib/stores';

	const i18n = getContext('i18n');
</script>

<svelte:head>
	<title>
		{$i18n.t('LLM Council')} / {$WEBUI_NAME}
	</title>
</svelte:head>

<!-- Redirect stub — the child +page.svelte immediately navigates to /?model=llm-council -->
<slot />
