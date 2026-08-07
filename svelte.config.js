import adapter from '@sveltejs/adapter-static';
import * as child_process from 'node:child_process';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { pipeline } from 'node:stream/promises';

const buildDirectory = process.env.QWYTHOS_BUILD_DIR || 'build';

// Pre-compressing at build time replaces per-request brotli in the Python
// server, which ran synchronously on the event loop for every asset on every
// request. It also buys us quality 11 instead of the middleware's quality 4.
//
// Deliberately NOT adapter-static's `precompress: true`: that walks the entire
// output, which includes static/pyodide (~58MB of JS, one ~10MB file). Brotli
// q11 over that adds minutes to every Docker build for bytes no browser
// fetches on boot. Only the boot-critical graph is worth the build time.
const COMPRESS_ROOTS = ['_app/immutable', 'index.html', 'manifest.json'];
const COMPRESS_EXTENSIONS = new Set(['.js', '.css', '.json', '.svg', '.html', '.xml']);
// Below roughly a TCP segment the header overhead outweighs the savings.
const COMPRESS_MIN_BYTES = 512;

const collectCompressTargets = (root) => {
	const absolute = path.join(buildDirectory, root);
	if (!fs.existsSync(absolute)) return [];

	if (fs.statSync(absolute).isFile()) {
		return [absolute];
	}

	return fs
		.readdirSync(absolute, { recursive: true })
		.map((entry) => path.join(absolute, entry))
		.filter((candidate) => {
			if (!COMPRESS_EXTENSIONS.has(path.extname(candidate))) return false;
			const stats = fs.statSync(candidate);
			return stats.isFile() && stats.size >= COMPRESS_MIN_BYTES;
		});
};

const compressFile = async (file) => {
	const size = fs.statSync(file).size;
	const encoders = [
		[
			'.br',
			() =>
				zlib.createBrotliCompress({
					params: {
						[zlib.constants.BROTLI_PARAM_MODE]: zlib.constants.BROTLI_MODE_TEXT,
						[zlib.constants.BROTLI_PARAM_QUALITY]: zlib.constants.BROTLI_MAX_QUALITY,
						[zlib.constants.BROTLI_PARAM_SIZE_HINT]: size
					}
				})
		],
		['.gz', () => zlib.createGzip({ level: zlib.constants.Z_BEST_COMPRESSION })]
	];

	for (const [extension, createEncoder] of encoders) {
		await pipeline(
			fs.createReadStream(file),
			createEncoder(),
			fs.createWriteStream(file + extension)
		);
	}
};

const staticAdapter = adapter({
	pages: buildDirectory,
	assets: buildDirectory,
	fallback: 'index.html'
});

/** @type {import('@sveltejs/kit').Adapter} */
const precompressingAdapter = {
	name: 'qwythos-static-precompress',
	async adapt(builder) {
		await staticAdapter.adapt(builder);

		const targets = COMPRESS_ROOTS.flatMap(collectCompressTargets);
		builder.log.minor(`Pre-compressing ${targets.length} files (brotli q11 + gzip 9)`);
		await Promise.all(targets.map(compressFile));
	}
};

/** @type {import('@sveltejs/kit').Config} */
const config = {
	// Consult https://kit.svelte.dev/docs/integrations#preprocessors
	// for more information about preprocessors
	preprocess: vitePreprocess(),
	kit: {
		// adapter-auto only supports some environments, see https://kit.svelte.dev/docs/adapter-auto for a list.
		// If your environment is not supported or you settled on a specific environment, switch out the adapter.
		// See https://kit.svelte.dev/docs/adapters for more information about adapters.
		adapter: precompressingAdapter,
		// poll for new version name every 60 seconds (to trigger reload mechanic in +layout.svelte)
		version: {
			name: (() => {
				try {
					return child_process.execSync('git rev-parse HEAD').toString().trim();
				} catch {
					// if git is not available, fallback to package.json version
					// or current timestamp
					try {
						return (
							JSON.parse(fs.readFileSync(new URL('./package.json', import.meta.url), 'utf8'))
								?.version || Date.now().toString()
						);
					} catch {
						return Date.now().toString();
					}
				}
			})(),
			pollInterval: 60000
		}
	},
	vitePlugin: {
		// inspector: {
		// 	toggleKeyCombo: 'meta-shift', // Key combination to open the inspector
		// 	holdMode: false, // Enable or disable hold mode
		// 	showToggleButton: 'always', // Show toggle button ('always', 'active', 'never')
		// 	toggleButtonPos: 'bottom-right' // Position of the toggle button
		// }
	},
	onwarn: (warning, handler) => {
		const { code } = warning;
		if (code === 'css-unused-selector') return;

		handler(warning);
	}
};

export default config;
