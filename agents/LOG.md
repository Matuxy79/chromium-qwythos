# Agent activity log

Newest entries first. Format:

```
## YYYY-MM-DD — <agent/session label>
- What changed / what was learned
- Verified by: <command or check>
- Loose ends: <anything left uncertain or broken>
```

---

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
