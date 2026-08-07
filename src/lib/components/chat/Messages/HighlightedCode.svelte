<script lang="ts">
	import hljs, { ensureLanguage } from '$lib/utils/highlight';

	// The theme lives with the markup that carries the .hljs classes, so anything
	// rendering this component is styled without a separate import.
	import 'highlight.js/styles/github-dark.min.css';

	export let code = '';
	export let lang = '';
	export let className = '';
	export let style = '';

	// Only the ~36 common grammars ship eagerly (see $lib/utils/highlight). For
	// anything outside that set this renders as plain text for one frame while
	// the full set loads, then the counter re-keys the markup to highlight it.
	// Common languages resolve synchronously and never re-render.
	let highlightGeneration = 0;
	$: if (lang && !hljs.getLanguage(lang)) {
		ensureLanguage(lang).then((available) => {
			if (available) highlightGeneration++;
		});
	}
</script>

<pre class={className} {style}><code
		class="language-{lang} rounded-t-none whitespace-pre text-sm"
		>{#key highlightGeneration}{#if lang && hljs.getLanguage(lang)}{@html hljs.highlight(code, {
					language: lang,
					ignoreIllegals: true
				}).value}{:else}{code}{/if}{/key}</code
	></pre>
