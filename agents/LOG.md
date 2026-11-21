# Agent activity log

## 2026-11-21 — Railway frontend install investigation
- The iPhone status-bar fix is already present in commit `6da01ee`, but the pictured Railway build failed before deployment. Its `npm ci` failure log is clipped; the onnxruntime-node Linux installer independently reproduces the visible HTTP stack when fetching its CUDA archive, which returned 404.
- Scoped `ONNXRUNTIME_NODE_INSTALL_CUDA=skip` to the frontend Docker build's `npm ci`; the browser build does not need Node's CUDA provider. The same installer exits successfully with this setting.
- Verified by: checking the installer and archive response, and `git diff --check`. Docker daemon and Railway authentication were unavailable, so a full container build and deployment remain unverified. Confirm the complete Railway error and test the resulting build on the iPhone.

## 2026-11-21 — Web Search + Code Interpreter switched on by default (code level)

- Added `DEFAULT_ENABLED_CHAT_FEATURES` to `src/lib/constants.ts`: Web Search and
  Code Interpreter now start **on** in the composer instead of inheriting an
  untouched (or legacy `null`) per-user preference or a model's
  `defaultFeatureIds` list, which left both switches off on open.
- New `src/lib/utils/chatFeatures.ts` (+ `chatFeatures.test.ts`): pure
  `isChatFeatureAvailable()` / `resolveChatFeatureDefault(s)` decide the state a
  chat opens in. Availability always wins first — model capability (missing keys
  count as supported, matching how `MessageInput` decides to render the switch),
  the server's `features.enable_web_search` / `enable_code_interpreter` flags,
  the user's permission, and terminal-vs-code-interpreter exclusivity — then the
  code default, with an explicit "Never" in Settings → Interface honoured as an
  opt-out.
- `src/lib/components/chat/Chat.svelte`: `applyFeatureDefaults()` feeds those
  resolvers from the stores and runs on model arrival / model switch (reactive
  key over the selected model ids), inside `setDefaults()`, in `initNewChat()`,
  `resetInput()` (model change) and on chat switch (`navigateHandler`). The old
  seeding from `model.info.meta.defaultFeatureIds` and from the raw per-user
  preference is gone for these two features.
- Draft restore (`sessionStorage` `chat-input*`) no longer overwrites the two
  switches, so reopening a chat with a saved draft keeps the default. A manual
  toggle-off still sticks for the rest of the session: nothing re-applies the
  default until the model set or chat changes.
- `src/lib/components/chat/MessageInput.svelte`: Escape now only clears tools /
  filters / image generation, not the two feature switches.
- `src/lib/components/chat/Navbar.svelte`: added the missing `isApp` store
  import — `$isApp` was referenced without importing it, which failed
  `vite build` outright (unrelated pre-existing break, fixed to unblock the
  build).
- Verified by: `vitest run src/lib/utils/chatFeatures.test.ts` (12 tests: default
  on, legacy `null`/`undefined`/`always` preferences read as on, explicit "Never"
  opts out, missing capability keys count as supported, per-model/config/permission
  gates, terminal exclusivity, no-model and mixed-model cases); `svelte-check`
  reporting nothing for the touched files; a full production build
  (`node_modules/.bin/vite build`) writing a fresh `build/`.
- Loose ends: needs a live run of the app (backend + rebuilt frontend) to confirm
  the switches render on for an OpenRouter model such as `venice-uncensored`;
  not exercised here because no backend/data dir was available in this checkout.

## 2026-11-21 — Mobile iOS viewport zoom, locked scroll, and unclickable header/sidebar fix
- Resolved the three core mobile viewport and interaction issues:
  1. Cleaned viewport meta tag to standard `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />` (removed invalid `interactive-widget=resizes-content` token that broke WebKit layout viewport parsing).
  2. Enforced `font-size: 16px !important` across all inputs, textareas, and TipTap/ProseMirror elements on mobile screens to prevent iOS Safari auto-zoom on focus. Added `overflow-x: clip` to the app shell.
  3. Added `hidden md:flex` to the 42px desktop collapsed sidebar rail to prevent pre-hydration horizontal overflow on mobile viewports.
  4. Fixed flex scroll trap: eliminated competing `overflow-auto` on `#chat-pane` and layout wrapper, leaving `#messages-container` as the single vertical scroll container with `-webkit-overflow-scrolling: touch; overscroll-behavior-y: contain; min-height: 0; flex: 1 1 0%`. Changed inner messages wrapper from `h-full` to `min-h-full` so message feeds expand and scroll naturally without clipping behind composer.
  5. Fixed top header and sidebar toggle: removed `-webkit-app-region: drag` from mobile web navbar/sidebar, added `pt-[env(safe-area-inset-top,0.375rem)]` notch clearance and bottom composer `pb-[max(0.5rem,env(safe-area-inset-bottom,0px))]` home bar clearance, removed `-mb-12` overlap on mobile, and made `MobileSidebarToggle` rendered with `md:hidden` so it's always tappable.
- Verified by: vitest test suite passing (2 tests), backend test suite passing (`test_tool_auto_mode.py` 7 tests, `test_openrouter_credentials.py` 13 tests).
- Loose ends: verify on physical iOS device in both portrait and landscape orientation.

Newest entries first. Format:

```
## YYYY-MM-DD — <agent/session label>
- What changed / what was learned
- Verified by: <command or check>
- Loose ends: <anything left uncertain or broken>
```

## 2026-11-21 — Web Search and Code Interpreter on by default
- Symptom: a new chat with Venice: Uncensored opened with both Integrations switches off. The 2026-11-12 `defaultFeatureIds` seed in `DEFAULT_MODEL_METADATA` does not reach existing installs: `Config.get('models.default_metadata')` returns the stored DB value, and `seed_defaults` never overwrites a key that already exists. Venice's `code_interpreter` seed was also `False`, and its `defaultFeatureIds` omitted it.
- Changed: `Chat.svelte` `setDefaults` now turns web search and code interpreter on in code. The admin `defaultFeatureIds` list still wins when present; otherwise each feature is on unless the user chose "Never". `Settings/Interface.svelte` toggles are now Always/Never (the old "Default" state, which was off, is gone; unset or old `null` now reads as Always). `backend/qwythos/config.py` seed sets Venice `code_interpreter: True` and `defaultFeatureIds: ['web_search', 'code_interpreter']`. Added `codeInterpreter` to the `Settings` type in `src/lib/stores/index.ts`. `test/test_tool_auto_mode.py` also asserts `code_interpreter` in the Venice defaults.
- Verified by: `python test/test_tool_auto_mode.py` (7 tests OK); `py_compile backend/qwythos/config.py`; `svelte-check --output machine`, with no new diagnostics in the changed line ranges (the repo already reports about 8,287 pre-existing svelte-check errors). Not run in a browser.
- Loose ends: a stored DB model with `code_interpreter` false keeps that toggle hidden, because stored config wins over the seed. An admin-saved `defaultFeatureIds` list still overrides the default per model. Anyone who had picked "Default" for either setting now gets "Always"; "Never" is the only off state.

## 2026-11-12 — PDF upload fails with "No embedding model is loaded" (error text fixed)
- Symptom: a 36.6 MB PDF attached in chat with Venice Uncensored fails with "No embedding model is loaded. Set RAG_EMBEDDING_MODEL to a valid SentenceTransformer model name...".
- Root cause: `get_ef()` in `backend/qwythos/routers/retrieval.py` always returns `None` in this build (local in-process embedding is disabled). With `RAG_EMBEDDING_ENGINE` unset, `get_embedding_function()` hits its `embedding_function is None` branch for every file that is embedded. The message told users to set `RAG_EMBEDDING_MODEL` to a SentenceTransformer name, which cannot fix it.
- Changed: error text in `backend/qwythos/retrieval/utils.py` (`get_embedding_function`). It now says local models are disabled and points to `RAG_EMBEDDING_ENGINE` (ollama, openai, azure_openai). No behavior change beyond the message.
- Not the cause: the image vision gate (`src/lib/components/chat/MessageInput.svelte` ~L899-903) runs only for `image/*` MIME types. A PDF takes the other branch.
- Verified by: `ast.parse` on `retrieval/utils.py`; grep shows the message string appears once in the repo.
- Loose ends: this install has no external embedding engine configured. The real fix is config: set `RAG_EMBEDDING_ENGINE` plus a model it serves, or set `BYPASS_EMBEDDING_AND_RETRIEVAL=True`, which injects full text into the prompt and will overflow Venice's context for a PDF this size. If the PDF is scanned, extraction returns no text and OCR is needed. Not tested end to end in the running app.

## 2026-11-12 — OpenRouter embedder picker in Admin → Settings → Documents (RAG embedding)
- Context: the "No embedding model is loaded" toast on PDF upload happens because this build disables local SentenceTransformer embeddings (`get_ef` in `routers/retrieval.py:138` always returns None; API-only), so RAG needs `rag.embedding_engine` set to an API engine. Engine `openai` with blank URL/key already inherits the OpenRouter base URL + key (`resolved_rag_openai_credentials` → `get_resolved_openai_compatible`) and POSTs `{input, model}` to `{url}/embeddings`, which matches OpenRouter's `/api/v1/embeddings`.
- Backend: new `GET /openai/openrouter/embedding-models?q=` in `routers/openai.py` (`get_openrouter_embedding_models`) proxying OpenRouter's public `{base}/embeddings/models` catalog (40 embedding models live-verified), slimmed + separator-insensitive `q` filter, same 400/502 guards as the chat catalog endpoint.
- Frontend: `getOpenRouterEmbeddingModels(token, q)` in `src/lib/apis/openai/index.ts`. `admin/Settings/Documents.svelte` Embedding section now shows an OpenRouter embedding-model dropdown (name, id, free/$-per-M label) when engine is `openai` and the target is OpenRouter (inheriting key or openrouter.ai URL); the free-text input stays for custom ids. Engine switch to `openai` now defaults the model to `openai/text-embedding-3-small` when inheriting OpenRouter. Selection persists via the existing `POST /api/v1/retrieval/embedding/update` → Config DB key `rag.embedding_model` (same persistent storage as other model/connection settings; survives Railway redeploys via the `/app/backend/data` volume). Embedder is intentionally global, not per-account — embeddings are computed server-side into the shared vector DB.
- Verified by: `py_compile`; AST-extraction tests for both new endpoints (routes, filters, 400/502) all pass; `test_tool_auto_mode.py` (7) and `test_openrouter_credentials.py` (13) pass; `npx vite build` succeeds; svelte-check shows no new error classes (repo has ~8k pre-existing).
- Loose ends: not deployed yet (Railway rebuild needed). Quick env-only alternative: `RAG_EMBEDDING_ENGINE=openai` + `RAG_EMBEDDING_MODEL=nvidia/nemotron-3.5-embed-8b:free` (free, 32K ctx) — free OpenRouter embedding options verified live: nvidia/nemotron-3.5-embed-8b:free, nvidia/nemotron-3-embed-1b:free, nvidia/llama-nemotron-embed-vl-1b-v2:free, liquid/lfm-2.5-embedding-350m:free; cheap: sentence-transformers/all-minilm-l6-v2 $0.005/M, qwen/qwen3-embedding-8b $0.01/M (40K ctx), openai/text-embedding-3-small $0.02/M. Remember to reindex knowledge after switching.

---

## 2026-11-12 — In-app OpenRouter model browser replaces external qwythos.com/models link
- `qwythos.com` is a parked Spaceship domain (not the app), so the Workspace → Models "Made by Qwythos Community" link (`https://qwythos.com/models`) died with ERR_EMPTY_RESPONSE. Reworked that section into an in-app, searchable OpenRouter catalog view.
- Backend: new `GET /openai/openrouter/models?q=...` in `backend/qwythos/routers/openai.py` (`get_openrouter_model_catalog`). Resolves credentials via `get_resolved_openai_compatible()`, proxies `{base}/models`, filters `q` over id/name/description, returns slim sorted entries (id, name, truncated description, context_length, pricing, supported_parameters, top_provider, owned_by). 400 when OpenRouter isn't configured / no key, 502 when upstream fails.
- Frontend: `getOpenRouterCatalog(token, q)` in `src/lib/apis/openai/index.ts`; new `src/lib/components/workspace/Models/OpenRouterDiscover.svelte` — search box synced to the `?q=` URL param (so `/workspace/models?q=venice` is shareable), debounced fetch, result count, per-model context + $/M pricing, click a row to open `/?model=<id>`. Wired into `src/lib/components/workspace/Models.svelte` in place of the old `CommunityDiscover` external link (import swapped; Prompts/Tools/Functions still link out to qwythos.com).
- Also repointed the two `qwythos.com/models?q=<model>` entry points that the model-selector "Community Reviews" menu and the rate-comment "Leave a public review" link used: `ModelItemMenu.svelte` now does `goto('/workspace/models?q=<id>')` instead of `window.open('https://qwythos.com/...')`, and `RateComment.svelte` links in-app to the same path. The `q` filter in the endpoint is separator-insensitive (`re.sub(r'[^a-z0-9]+', ' ', ...)`) so `venice-uncensored` matches the catalog name "Venice Uncensored".
- Verified by: `py_compile` on routers/openai.py; AST-extraction test of the endpoint (route registration, q filtering incl. separator-insensitive match, slimming/sorting, 400/400/502 paths — all pass, scratchpad script); `test_tool_auto_mode.py` (7) and `test_openrouter_credentials.py` (13) pass; `npx vite build` succeeds twice (component compiles and bundles); svelte-check shows no new error classes in touched files (repo has 8297 pre-existing errors).
- Loose ends: not yet deployed — Railway needs a rebuild from this tree for `/openai/openrouter/models` to exist in production. Prompts/Tools/Functions community links and `/m/<user>/<model>` share links still point at the parked domain.

---

## 2026-11-12 — Web Search default-enabled for Venice: Uncensored
- Added `'defaultFeatureIds': ['web_search']` to `DEFAULT_MODEL_METADATA['venice-uncensored']` in `backend/qwythos/config.py:1904`.
- This ensures Venice: Uncensored loads with Web Search active by default on new chats without requiring users to manually toggle the switch in the UI.
- Added test in `test/test_tool_auto_mode.py` asserting `DEFAULT_MODEL_METADATA['venice-uncensored']` contains `defaultFeatureIds: ['web_search']`.
- Verified by: `python -m py_compile backend/qwythos/config.py` passes; `python test/test_tool_auto_mode.py` (7 tests pass); `python test/test_openrouter_credentials.py` (13 tests pass).
- Loose ends: none.

---

## 2026-11-12 — Venice live-search diagnosis
- Inspected the Railway app and Avatar chat. The current chat's Integrations → Enable Web Search switch was unchecked and the reply showed no web sources. `Chat.svelte` sends the switch as `features.web_search`; Venice's automatic search path in `middleware.py` only runs when that flag is true. The current UI does not prove the historical flag for the already-sent message.
- Verified by: production `/health` and `/api/version` returned HTTP 200; authenticated switch reported `aria-checked=false`; source inspection of the frontend request and Venice fallback.
- No code behavior changed; no live search request was sent from the chat.

## 2026-10-27 — Tool Auto Mode & Venice: Uncensored non-native tool fallback
- Fixed OpenRouter 400 error (`No endpoints found that support tool use. Try disabling "get_current_timestamp"`) on Venice: Uncensored and other models that do not support OpenAI native function calling.
- Added `model_supports_native_tools(model)` in `backend/qwythos/utils/tools.py:523` to detect models that lack native function-calling capability based on OpenRouter `supported_parameters`, explicit capabilities (`builtin_tools: false`, `tools: false`), and known non-tool provider families (Venice/Dolphin).
- Gated `use_builtin_tools` and `form_data['tools']` in `backend/qwythos/utils/middleware.py`: models without native tool support will never have `tools: [...]` sent to OpenRouter/provider endpoints, preventing 400 routing rejections.
- Implemented **Tool Auto Mode (Pre-Search RAG Fallback)** in `backend/qwythos/utils/middleware.py`: when Web Search is toggled on for a non-tool model like Venice: Uncensored, the backend automatically performs the web search upfront, emits real-time status and citation events to the UI, formats the search results into the prompt context via the RAG template, and dispatches the request clean without the `tools` parameter.
- Updated `DEFAULT_MODEL_METADATA` seed in `backend/qwythos/config.py:1882` to explicitly set `builtin_tools: False` and `citations: True` for `venice-uncensored`.
- Updated `backend/qwythos/utils/models.py:348` to properly apply per-model entries (e.g., `venice-uncensored`) from `DEFAULT_MODEL_METADATA` alongside global defaults.
- Added unit tests in `test/test_tool_auto_mode.py`.
- Verified by: `python -m py_compile` on all modified backend files; `python test/test_tool_auto_mode.py` (6 tests pass); `python test/test_openrouter_credentials.py` (13 tests pass).
- Loose ends: none.

---

## 2026-10-27 — Default model set to Venice: Uncensored
- Set `DEFAULT_MODELS` to `'venice-uncensored'` as the default model for new chats in `backend/qwythos/config.py:1820`. The model ID `venice-uncensored` corresponds to Venice Uncensored Dolphin Mistral 24B Venice Edition on OpenRouter — an uncensored instruct-tuned LLM by dphn.ai / Venice.ai, fine-tuned from Mistral-Small-24B-Instruct-2501. 33K context, $0.20/M input, $0.90/M output.
- Set `DEFAULT_PINNED_MODELS` to `'venice-uncensored'` so the model appears pinned at the top of the model selector.
- Added seed metadata for `venice-uncensored` in `DEFAULT_MODEL_METADATA` (`config.py:1870-1905`): display name "Venice: Uncensored", full description, capabilities (web_search enabled, vision/file_upload disabled), 33K context window, tags. User-provided `DEFAULT_MODEL_METADATA` env var overrides these defaults via dict merge.
- Updated `.env.example` with a "Default Model" section documenting `DEFAULT_MODELS` and `DEFAULT_PINNED_MODELS`, including the Venice Uncensored model details and pricing.
- Frontend automatically picks up the default: `Chat.svelte:197-198` filters default models against available models from OpenRouter. The model becomes available once the OpenRouter API key is configured and models are fetched.
- Verified by: `python -m py_compile backend/qwythos/config.py` passes; AST check confirms `DEFAULT_MODELS` and `DEFAULT_PINNED_MODELS` are set with correct defaults.
- Loose ends: did not verify the exact OpenRouter model ID `venice-uncensored` against the live OpenRouter API — this is based on OpenRouter's naming convention for Venice models. If the ID differs (e.g., `cognitivecomputations/dolphin-mistral-24b-venice-edition`), update `DEFAULT_MODELS` accordingly. The model only appears in the selector once OpenRouter returns it in the models list (requires valid API key).

---

## 2026-10-27 — Code-level API persistence across Railway builds
- Implemented code-level API key persistence so keys survive Railway rebuilds even when the database is wiped (no volume attached).
- **Volume mount detection** (`backend/start.sh`): bash-level check using `mountpoint` — warns loudly if `/app/backend/data` is not a mounted volume, with Railway-specific guidance (attach Volume in dashboard, or set env vars).
- **Volume mount detection** (`backend/qwythos/env.py`): Python-level check with `/proc/mounts` fallback. Exports `IS_RAILWAY` flag (detects `RAILWAY_ENVIRONMENT`/`RAILWAY_PROJECT_ID`/`RAILWAY_SERVICE_ID`). Logs warning if Docker/Railway detected without a mounted volume.
- **Forced env var → DB sync** (`backend/qwythos/config.py`): `FORCE_ENV_CONFIG` flag (auto-enabled on Railway) syncs critical API keys from environment variables into the database on EVERY startup, overriding DB values. Synced keys: `OPENROUTER_API_KEY`, `OPENROUTER_API_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_API_BASE_URL`, `GEMINI_API_KEY`, `AUDIO_TTS_OPENAI_API_KEY`, `AUDIO_STT_OPENAI_API_KEY`. Only API keys are synced — user prefs/UI settings are never overridden.
- **API key backup/restore** (`backend/qwythos/config.py`): `backup_api_keys()` writes critical keys to `DATA_DIR/api_keys_backup.json` (permissions `0600`) on startup. `restore_api_keys_from_backup()` restores keys if DB is empty but backup file exists (volume survived, DB wiped).
- **Railway startup logging** (`backend/qwythos/main.py`): logs persistence status on Railway — `FORCE_ENV_CONFIG` state, backup file presence, and actionable warnings.
- **`.env.example`**: documented `DATA_DIR`, `FORCE_ENV_CONFIG`, and the API key backup mechanism with Railway guidance.
- **`docs/DATA_PERSISTENCE.md`**: added "Code-Level API Persistence" section covering volume detection, forced env sync (with env var → config key mapping table), backup file format, startup logging, and a Railway deployment checklist.
- **`backend/.gitignore`**: added `api_keys_backup.json` to ignore list (contains plaintext secrets).
- Verified by: `python3 -m py_compile` on all modified Python files passes; `git status` shows only intended changes.
- Loose ends: did not run the app in a live Railway/Docker environment to verify the volume detection and env sync end-to-end. The `mountpoint` command may not be available in all minimal containers — fallback to `/proc/mounts` is implemented. `FORCE_ENV_CONFIG` overrides DB values on every startup when enabled — this is intentional for ephemeral deployments but means admin UI changes to synced keys will be reverted on restart (documented in code comments).

---

## 2026-10-27 — Chat persistence across app builds
- Cloned `chromium-qwythos` from GitHub and audited the data persistence setup. The runtime data directory (`backend/data/` for source/desktop, `backend/qwythos/data/` for installed package) holds the SQLite database (`webui.db` — all chat history), uploads, cache, and the desktop webview profile. Docker persistence was already correct (named volume in `docker-compose.yaml`, `.dockerignore` excludes `backend/data/*`). Found that `backend/.gitignore` already ignored `/data/*` and `/qwythos/data/*` (plus `*.db` and `.webui_secret_key`), but had no `.gitkeep` exceptions — so directory structure wasn't visible in the repo.
- Updated `backend/.gitignore` to add `!/data/.gitkeep` and `!/qwythos/data/.gitkeep` exceptions, allowing the placeholder files to be tracked while keeping all runtime data (SQLite DB, uploads, webview profile) ignored.
- Simplified root `.gitignore` — removed redundant `backend/.webui_secret_key` and `backend/data/desktop-server.log` entries (already covered by `backend/.gitignore`), added a comment pointing to `backend/.gitignore` for chat persistence rules.
- Created `backend/data/.gitkeep` and `backend/qwythos/data/.gitkeep` with documentation explaining what lives in each directory and how persistence works across Docker, desktop, local dev, and installed-package scenarios.
- Added `docs/DATA_PERSISTENCE.md` — comprehensive guide covering: where data lives per deployment mode, what's inside the data directory, persistence behavior across frontend rebuilds / Docker restarts / package reinstalls, manual backup/restore commands, Docker volume backup/restore, a "what gets lost" matrix, and a security note.
- Linked the new doc from `README.md` under the Architecture section (`💾 Data Persistence →`).
- Verified by: `git add -n backend/data/ backend/qwythos/data/` shows only `.gitkeep` files would be staged; `git check-ignore -v` confirms `webui.db` files match the ignore patterns while `.gitkeep` files match the exceptions.
- Loose ends: did not run the app to create a live `webui.db` and verify the ignore patterns against real runtime files — the patterns follow standard gitignore semantics and were verified with `git check-ignore`. The `env.py` migration from `backend/data/` to `backend/qwythos/data/` on package install was not exercised.

---

## 2026-08-24 — Railway `npm ci` lockfile desync (vite-plugin-pwa)
- Railway Metal builder failed at `RUN npm ci --force` with `EUSAGE`: `package.json` listed `vite-plugin-pwa@^0.21.1` (added in `c8d6553` PWA commit, which only touched `package.json`) but `package-lock.json` had no `vite-plugin-pwa` / workbox / babel-preset-env tree. Secondary mismatch: lockfile `es-object-atoms@1.1.1` vs required `1.1.2`, and lock root still said `0.12.0` after the `0.12.1` bump.
- Regenerated `package-lock.json` with Node 22.22.1 / npm 10.9.4 via `npm install --package-lock-only`. Resolved `vite-plugin-pwa@0.21.2` and bumped lock root version to `0.12.1`. No `package.json` / Dockerfile changes.
- Verified by: `npm ci --dry-run --ignore-scripts` succeeded (`added 1528 packages`).
- Loose ends: lockfile is local-only until committed and pushed; Railway will keep failing on the previous commit. Did not run a full `npm ci` install or Docker/Railway rebuild.

## 2026-08-24 — Railway Dockerfile VOLUME rejection
- Railway Metal builder failed with `dockerfile invalid: docker VOLUME at Line 124 is not supported, use Railway Volumes`. Removed `VOLUME ["/app/backend/data"]` from the root `Dockerfile`. Left the `mkdir`/`chown` of that path and a comment that persistence is host-mounted (compose `-v` / Railway Volume), not a Dockerfile VOLUME.
- `railway.json` already had `"volume": { "mountPath": "/app/backend/data" }`. Docs now warn that a volume staged at `/data` will not persist app state and must be remounted to `/app/backend/data` in the Railway dashboard — that remount is not something the repo can do.
- Verified by: grep of `Dockerfile*` for `VOLUME` (none remaining); read of `docker-compose.yaml` (`qwythos:/app/backend/data` still present); `railway.json` mountPath unchanged.
- Loose ends: did not touch the Railway project/service. If `chromium-qwythos-data` is still mounted at `/data`, the image will build but SQLite/uploads still land on ephemeral disk. No image rebuild was run locally.

## 2026-08-24 — Dead-code cleanup (corrected orphan counts vs docs/ORPHANAGE_SCAN.md)
- `docs/ORPHANAGE_SCAN.md` claimed 37 dead Svelte components and 28 dead API functions. Both counts were produced by a `$lib/components/...`-alias-only grep that misses the dominant style inside the components tree itself: relative imports (`./Foo.svelte`). Proof: `admin/Settings/Connections.svelte` imports `AdminSettingRow`/`AdminSettingSection`/`AdminSettingField` via `./X.svelte` — all three were on the doc's dead list and are actively used.
- Rebuilt the scan to resolve the full import graph: `$lib/...` alias, relative `./`/`../`, and dynamic `import(...)`, across every `.svelte`/`.ts`/`.js` file in `src`, not just the components directory. Cross-checked disputed results (icons, `common/Overlay`, `common/Selector`, `chat/MessageInput/Commands/{Models,Prompts}`) with targeted substring/whole-word greps before deleting anything.
- **Result: 57 dead Svelte components** (not 37) — superset of the doc's list; it missed 4 `layout/Sidebar/icons/*` duplicates-of-unused-icons, `common/Overlay.svelte`, `common/Selector.svelte`, `chat/MessageInput/Commands/{Models,Prompts}.svelte` (confirmed via `CommandSuggestionList.svelte`, which wires up the other 5 of 7 siblings by name and never these two), and `admin/Settings.svelte` (the pre-restructure wrapper, superseded by routed `admin/Settings/*.svelte` panels).
- **Result: 31 dead API functions** (not 28, and not the doc's list verbatim). A symbol-level scan (bare-identifier search across every other file in `src`) initially flagged 33; 2 were false positives from same-file-only usage the scan doesn't credit as "used": `getOAuthClientAuthorizationUrl` (`apis/configs/index.ts`, called by the live `initiateOAuthRedirect`, used from `Chat.svelte`/`MessageInput.svelte`/`IntegrationsMenu.svelte`) and `getFileProcessStatus` (`apis/files/index.ts`, called by the live `uploadFile`, used throughout file-upload UI). Both were kept.
- Deleted: `bench/`, `rust-backend/` (zero build/CI/Docker references), `src/lib/utils/_template_old.ts`, `src/lib/apis/council/` (whole dir — its two exports, `getCouncilRunConfig`/`runCouncil`, had zero importers; the live LLM Council chat model runs through `utils/council.py` directly, not this REST client), `backend/qwythos/routers/council.py` plus its import and `app.include_router` registration in `main.py`. `utils/council.py` itself, and its consumers in `utils/chat.py` and `tools/builtin.py`, are untouched — those back the live `llm-council` chat model.
- Removed an now-unused `getTimeRange` import from `apis/notes/index.ts` left behind after deleting `getNotes` (the only caller in that file).
- Verified by: re-ran the corrected import-graph scanner after deletion — 599→542 components, 0 orphans, 0 unresolved references. Grepped for import statements naming any of the 31 removed API symbols across all of `src` — none found. Backend: `python3 -m py_compile backend/qwythos/main.py` passes; `python3 -m compileall backend/qwythos` shows only two pre-existing, unrelated failures (`retrieval/vector/factory.py`, `utils/code_interpreter.py` — both use Python 3.10+ `match` statements against this shell's Python 3.9.6, not touched by this change). Grepped for `routers.council`/`council.router` anywhere in `backend/` — clean.
- Loose ends: **`npm run build` / `npm run check` / `npm run lint` were NOT run** — no `node`/`npm` in this shell and no `node_modules` present. The import-graph re-scan is a strong proxy (it would have caught any now-missing `.svelte`/`.ts` file being imported) but does not catch TypeScript type errors, unused-import lint warnings on the surviving files, or Svelte-specific template errors. Run the full frontend toolchain before shipping. External HTTP consumers of the removed `/api/v1/council/*` endpoints cannot be verified from source alone — this is a public API surface change; flagging as a breaking change for anyone hitting those endpoints directly outside the SPA.

## 2026-08-24 — PERF-001a: adaptive render tier (frontend half)
- New module `src/lib/runtime/renderGovernor.ts`. `bootHints` (`deviceMemory`, `hardwareConcurrency`, `saveData`, `prefers-reduced-motion`) are captured once at module load via `detectBootHints()` and frozen with `Object.freeze`; only observed `requestAnimationFrame` deltas and a fall-back `PerformanceObserver({entryTypes:['longtask']})` move the live tier. The `renderTier` writable Svelte store holds `'static' | 'light' | 'full'` with a default of `'light'`; demote at <42 fps over 2 s, promote at >57 fps over 10 s. Tier transitions dispatch a `qwythos:render-tier-change` `CustomEvent` for downstream telemetry/observability hooks.
- `src/routes/+layout.svelte`: imported `startFrameGovernor`, captured the teardown handle into a module-level `stopFrameGovernor`, called it at the very top of `onMount`, and invoked the teardown alongside `bc.close()` in the existing `onDestroy`. The no-op default for `stopFrameGovernor` keeps `onDestroy` safe even if `onMount` was interrupted before starting the governor.
- `src/lib/components/chat/QwythosStackBackground.svelte`: subscribed to `$renderTier`. Root `.qwythos-stack` div toggles `qwythos-stack--static` via a Svelte `class:` directive; the `<animateMotion>` runner is now wrapped in `{#if $renderTier !== 'static'}` so SMIL itself is unmounted under tier `'static'`. A single CSS rule zeros CSS animations on twelve selectors under `.qwythos-stack--static`. The existing `prefers-reduced-motion: reduce` override at line 521 is intentionally untouched — it now sits behind the JS-side check as the canonical Q0 short-circuit.
- Bumped `package.json` → `0.12.1`. Backend half (OPENRTR-1, ring gating, telemetry sinks) remains an open ticket.
- Verified by: manual source review only. `node`/`npm` were not available on this shell, so `npm run check`, `npm run lint:frontend`, and `npm run build` were NOT executed. Logged as a known gap.
- Loose ends: no `qwythos:render-tier-change` listener yet (backend `EVENTS.*` symbols come with the backend patch). `light` and `full` behave identically today; the audit’s “animate only the active model” Q1 feature is an explicit follow-up. Possible hydration warning under `prefers-reduced-motion: reduce` because the store resolves to `'light'` on the server (no `navigator`) and to `'static'` on the client’s first tick; the reactive update brings the render into line.

## 2026-08-24 — v0.12 OpenRouter consolidation
- Added `openrouter.api_key` / `openrouter.base_url` (env `OPENROUTER_API_KEY`) as the production provider. One resolver in `utils/openrouter.py` is used by RAG embeddings, audio STT/TTS, and image gen/edit when those features have no explicit override.
- Seed/sync keeps `openai.api_base_urls` aligned with that key; existing OpenRouter chat connections are hydrated into `openrouter.*` on upgrade.
- Stopped config.py from forcing `OPENAI_API_BASE_URL` back to `https://api.openai.com/v1`, which had emptied every per-feature default on OpenRouter-only deploys. `/openai/audio/speech` no longer requires that URL in the connection list.
- Frontend: Connections shows the OpenRouter key first and folds extra OpenAI/Ollama editors under Advanced. First-run signup can paste the key. Documents/Audio/Images inherit instead of requiring a duplicate key.
- Bumped version to 0.12.0.
- Verified by: `python3 test/test_openrouter_credentials.py`; `python3 -c` import of config + openrouter helpers; `python3 -m py_compile` on touched backend modules.
- Loose ends: web-search provider keys and Ollama remain separate (not OpenAI-compatible). Anthropic token counting still does not trigger for OpenRouter-hosted Anthropic IDs. Did not run the full frontend/backend app in a browser.

## 2026-08-17 — Open WebUI remnants & disconnected artifacts audit
- Read-only audit (no code changes) mapping all leftover upstream artifacts.
- Found: `WEBUI_*` env vars (inherited API, keep), upstream author in
  `pyproject.toml`, 28+ `docs.qwythos.com` links (verify domain exists),
  phantom `github.com/qwythos/qwythos` commit URLs in CHANGELOG,
  duplicate static favicons (both needed), vestigial `static/opensearch.xml`,
  disconnected root files (3 GGUF PDFs = 14.5 MB, `banner.png`, `demo.png`,
  `contribution_stats.py`, `docker-compose-launcher.sh`, `docker-cleanup.sh`).
- Python imports fully clean (`open_webui` → `qwythos` complete).
- No `open_webui` or `open-webui` refs in source code (only in legal docs).
- Full report: see `open_webui_remnants.md` artifact.
- Loose ends: docs.qwythos.com domain status unknown; GGUF PDFs undocumented.

## 2026-08-17 — drop leftover Open WebUI PR CI
- Deleted `.github/workflows/backend.yaml` (Python CI / Ruff Format 3.11+3.12)
  and `frontend.yaml` (Format & Build, Unit Tests). They were upstream leftover
  format gates, not Qwythos product checks.
- Also deleted the already-inert `lint-backend.disabled`, `lint-frontend.disabled`,
  and `codespell.disabled` files so they stop sitting around as clutter.
- Left `docker.yaml`, `release.yml`, `release-pypi.yml`, and `issue-label.yaml`.
- Verified by: `ls .github/workflows/` after `git rm`.
- Loose ends: GitHub will keep showing the old failed jobs on the previous
  commit until this change is pushed; new commits will not schedule them.

---

## 2026-08-17 — llm-council as a first-class chat model
- Injected a synthetic `llm-council` model into `get_all_models()` when
  `council.enable` is on and a roster of 2+ models is configured. Same
  shape as arena: config-driven, no `models` table row, public read grant
  so non-admins see it in the chat dropdown.
- Chat completions for that model run the 3-stage council pipeline.
  Stage 1 members inherit the parent chat's builtin tools (web search,
  files, knowledge, etc.) and run a bounded tool loop; ranking and
  chairman synthesis stay text-only. The wrapper itself cannot call
  `run_llm_council` (recursion).
- Background tasks (title/tags/follow-up) resolve to the chairman instead
  of convening the council.
- Frontend: dropdown types, BrandMenu "LLM Council" starts a chat with
  `?model=llm-council`, roster picker excludes arena/council wrappers.
- Verified by: `ast.parse` on changed Python modules; access-control path
  matches arena (`is_virtual_model` in `check_model_access` /
  `get_filtered_models`).
- Loose ends: `/council` page still exists as a dedicated deliberation UI
  (no chat history/tools). Member tool-call citations do not bubble into
  the parent chat. Dedicated page is not removed.

---

## 2026-08-17 — LLM Council chat model + tool calling (kimi-code session)

- Fixed non-admin access to the config-driven `llm-council` chat model in
  `backend/qwythos/main.py`. The `chat_completion` handler now treats
  `owned_by: 'council'` (and `arena`) as virtual models and checks
  `meta.access_grants` instead of requiring a DB row, mirroring the
  `utils/models.py` list-filtering logic.
- Added streaming support to `backend/qwythos/utils/council.py`
  `generate_council_chat_completion` so selecting LLM Council in chat returns
  an OpenAI-style SSE stream instead of a raw dict.
- The council pipeline already passes `tools`/`tools_dict` to stage-1 member
  completions and runs a server-side tool-call loop (web search, knowledge,
  memory, code interpreter, etc.) from the parent chat's resolved builtins.
- Verified syntax with `python3 -m py_compile` on `main.py`, `utils/council.py`,
  `utils/models.py`, `config.py`.
- Note: much of the council-as-model scaffolding (`DEFAULT_COUNCIL_MODEL` in
  `config.py`, injection in `utils/models.py`, the `/council` page, and the
  tool loop in `utils/council.py`) was already present; this change closes the
  access and streaming gaps so it actually works from the chat dropdown.

## 2026-08-17 — initial scan (kimi-code session)

- Created `agents/` (README, REPO_MAP, this log) as the shared workspace for
  frontier agents, per matuxy's request.
- Performed full repository scan; findings recorded in `REPO_MAP.md`.
- Key findings:
  - Repo = Open WebUI fork "Qwythos" v0.11.0; FastAPI backend (~31 routers),
    SvelteKit frontend, Windows pywebview launcher, Rust spike.
  - `rust-backend` **does not compile**: `src/main.rs` declares `mod routes;`
    and `mod services;` but those dirs don't exist. Nothing depends on the
    crate (no CI/Docker references).
  - `bench/RESULTS.md` already concluded the Rust rewrite isn't worth it
    (~0.15–0.35 ms/req TTFT gain; ~10× memory win is the only real argument).
  - Branding: "qwythos" strings in auth page + settings + configs API;
    "wyvern" only in `src/routes/auth/+page.svelte`.
- Verified by: direct reads of `main.py`, `package.json`, `Cargo.toml`,
  `desktop/*.py*`, `bench/*.md`, workflow files; `ls`/`grep` sweeps of all
  major trees.
- Loose ends:
  - Did not enumerate `backend/qwythos/migrations/` revisions or
    `src/lib/i18n/` locale count precisely.
  - Two ~1 MB+ PDFs at repo root (`Qwythos-gguf*.pdf`) — undocumented purpose.
  - Whether `rust-backend` should be completed, fixed to compile, or deleted
    is an open decision for matuxy.

## 2026-11-21 — iOS top clearance for mobile headers (Claude)

- Symptom: on iPhone the sidebar toggle, the chat's top-right buttons (temporary
  chat) and the drawer's close button sat under the status bar clock and could
  not be tapped.
- Cause: top padding came from `env(safe-area-inset-top, <fallback>)`. iOS always
  defines `env()` and reports 0 when it sees no top inset, so the fallback never
  applied. Commit 6784763 had replaced the fixed `pt-1.5` (6px) with this.
- Change: `src/app.css` adds `.ios-safe-top` and sets the drawer's
  `.mobile-sidebar-content` top padding to `max(env(safe-area-inset-top, 0px), 3.75rem)`,
  inside `@supports (-webkit-touch-callout: none)` within the mobile media query.
  The class is applied to the chat and channel navbars, the admin, calendar,
  home, playground and workspace navs, the automations header row, the notes list
  row and the note editor header.
- Not verified on a physical iPhone. Chromium does not run the iOS-only branch.
  The 3.75rem floor is a guess sized to clear the Dynamic Island status bar.
