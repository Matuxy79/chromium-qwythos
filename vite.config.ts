import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import { VitePWA } from 'vite-plugin-pwa';

import { viteStaticCopy } from 'vite-plugin-static-copy';

export default defineConfig({
	plugins: [
		sveltekit(),
		viteStaticCopy({
			targets: [
				{
					src: 'node_modules/onnxruntime-web/dist/*.jsep.*',

					dest: 'wasm'
				}
			]
		}),
		VitePWA({
			registerType: 'autoUpdate',
			injectRegister: 'auto',
			includeAssets: ['favicon.ico', 'favicon.png', 'robots.txt', 'apple-touch-icon.png'],
			manifest: {
				name: 'Qwythos',
				short_name: 'Qwythos',
				description: 'Qwythos is an open, extensible, user-friendly interface for AI that adapts to your workflow.',
				theme_color: '#0d0f14',
				background_color: '#0d0f14',
				display: 'standalone',
				orientation: 'any',
				scope: '/',
				id: '/',
				start_url: '/',
				icons: [
					{
						src: '/static/web-app-manifest-192x192.png',
						sizes: '192x192',
						type: 'image/png',
						purpose: 'any maskable'
					},
					{
						src: '/static/web-app-manifest-512x512.png',
						sizes: '512x512',
						type: 'image/png',
						purpose: 'any maskable'
					}
				],
				share_target: {
					action: '/',
					method: 'GET',
					params: {
						text: 'shared'
					}
				}
			},
			workbox: {
				globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
				navigateFallback: '/index.html',
				navigateFallbackDenylist: [/^\/api\//, /^\/ws\//, /^\/ollama\//, /^\/openai\//],
				runtimeCaching: [
					{
						urlPattern: /^\/api\/config$/,
						handler: 'NetworkFirst',
						options: {
							cacheName: 'api-config-cache',
							expiration: {
								maxEntries: 10,
								maxAgeSeconds: 60 * 60 // 1 hour
							}
						}
					},
					{
						urlPattern: /^\/static\/.*/i,
						handler: 'CacheFirst',
						options: {
							cacheName: 'static-assets-cache',
							expiration: {
								maxEntries: 100,
								maxAgeSeconds: 60 * 60 * 24 * 30 // 30 days
							}
						}
					},
					{
						urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp|ico)$/i,
						handler: 'CacheFirst',
						options: {
							cacheName: 'image-cache',
							expiration: {
								maxEntries: 60,
								maxAgeSeconds: 60 * 60 * 24 * 30 // 30 days
							}
						}
					},
					{
						urlPattern: /\.(?:woff|woff2|ttf|otf|eot)$/i,
						handler: 'CacheFirst',
						options: {
							cacheName: 'font-cache',
							expiration: {
								maxEntries: 20,
								maxAgeSeconds: 60 * 60 * 24 * 365 // 1 year
							}
						}
					}
				]
			},
			devOptions: {
				enabled: false
			}
		})
	],
	define: {
		APP_VERSION: JSON.stringify(process.env.npm_package_version),
		APP_BUILD_HASH: JSON.stringify(process.env.APP_BUILD_HASH || 'dev-build')
	},
	build: {
		// Sourcemaps are the single largest memory consumer in the rollup pass and
		// are dead weight in a shipped container. Keep them for local dev builds only.
		sourcemap: process.env.ENV === 'dev'
	},
	worker: {
		format: 'es'
	},
	esbuild: {
		pure: process.env.ENV === 'dev' ? [] : ['console.log', 'console.debug', 'console.error']
	}
});
