<script>
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { shortCodesToEmojis, loadShortCodesToEmojis } from '$lib/stores';

	// The table is fetched on demand rather than at app boot; until it lands the
	// fallback branch below renders the raw shortcode.
	loadShortCodesToEmojis();

	export let shortCode;
	export let className = 'size-4';
</script>

{#if $shortCodesToEmojis[shortCode]}
	<img
		src="{WEBUI_BASE_URL}/assets/emojis/{$shortCodesToEmojis[shortCode].toLowerCase()}.svg"
		alt={shortCode}
		class={className}
		loading="lazy"
	/>
{:else}
	<div>
		{shortCode}
	</div>
{/if}
