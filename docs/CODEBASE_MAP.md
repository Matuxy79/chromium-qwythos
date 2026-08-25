# Qwythos Codebase Map

This is a practical navigation guide to the current repository. It complements the [Architecture](ARCHITECTURE.md), which describes runtime relationships and request flows.

## Start here

| Task                                 | First file                                                                        | Follow-on files                                                                                                                                                                                                                                                                        |
| ------------------------------------ | --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Understand application startup       | [`backend/qwythos/main.py`](../backend/qwythos/main.py)                           | [`backend/qwythos/env.py`](../backend/qwythos/env.py), [`backend/qwythos/config.py`](../backend/qwythos/config.py)                                                                                                                                                                     |
| Change global frontend boot behavior | [`src/routes/+layout.svelte`](../src/routes/+layout.svelte)                       | [`src/lib/stores/index.ts`](../src/lib/stores/index.ts), [`src/lib/runtime/renderGovernor.ts`](../src/lib/runtime/renderGovernor.ts), [`src/lib/constants.ts`](../src/lib/constants.ts)                                   |
| Change protected app initialization  | [`src/routes/(app)/+layout.svelte`](<../src/routes/(app)/+layout.svelte>)         | [`src/routes/(app)/+page.svelte`](<../src/routes/(app)/+page.svelte>)                                                                                                                                                                                                                  |
| Change chat behavior                 | [`src/lib/components/chat/Chat.svelte`](../src/lib/components/chat/Chat.svelte)   | [`src/lib/apis/openai/index.ts`](../src/lib/apis/openai/index.ts), [`backend/qwythos/main.py`](../backend/qwythos/main.py), [`backend/qwythos/utils/middleware.py`](../backend/qwythos/utils/middleware.py), [`backend/qwythos/utils/chat.py`](../backend/qwythos/utils/chat.py)       |
| Change authentication                | [`src/routes/auth/+page.svelte`](../src/routes/auth/+page.svelte)                 | [`src/routes/+layout.svelte`](../src/routes/+layout.svelte), [`src/routes/(app)/+layout.svelte`](<../src/routes/(app)/+layout.svelte>), [`backend/qwythos/routers/auths.py`](../backend/qwythos/routers/auths.py), [`backend/qwythos/utils/auth.py`](../backend/qwythos/utils/auth.py) |
| Add or change an API domain          | [`backend/qwythos/routers/`](../backend/qwythos/routers/)                         | router registration in [`backend/qwythos/main.py`](../backend/qwythos/main.py), matching client under [`src/lib/apis/`](../src/lib/apis/)                                                                                                                                              |
| Change persistence                   | [`backend/qwythos/models/`](../backend/qwythos/models/)                           | [`backend/qwythos/internal/db.py`](../backend/qwythos/internal/db.py), [`backend/qwythos/migrations/`](../backend/qwythos/migrations/)                                                                                                                                                 |
| Change retrieval or RAG              | [`backend/qwythos/routers/retrieval.py`](../backend/qwythos/routers/retrieval.py) | [`backend/qwythos/retrieval/`](../backend/qwythos/retrieval/)                                                                                                                                                                                                                          |
| Change real-time behavior            | [`backend/qwythos/socket/main.py`](../backend/qwythos/socket/main.py)             | [`backend/qwythos/socket/utils.py`](../backend/qwythos/socket/utils.py), socket setup in [`src/routes/+layout.svelte`](../src/routes/+layout.svelte)                                                                                                                                   |
| Change Windows desktop startup       | [`desktop/launcher.pyw`](../desktop/launcher.pyw)                                 | [`desktop/app.py`](../desktop/app.py), readiness/version endpoints in [`backend/qwythos/main.py`](../backend/qwythos/main.py)                                                                                                                                                          |
| Change builds or packaging           | [`package.json`](../package.json)                                                 | [`svelte.config.js`](../svelte.config.js), [`vite.config.ts`](../vite.config.ts), [`Dockerfile`](../Dockerfile), [`pyproject.toml`](../pyproject.toml), [`hatch_build.py`](../hatch_build.py)                                                                                          |

## Repository layout

```text
qwythos-bot/
|-- backend/
|   |-- qwythos/          FastAPI application package
|   |-- requirements.txt  Container and desktop dependency input
|   |-- dev.sh            Reloading development server on port 8080
|   |-- start.sh          Container/server entry point
|   `-- start_windows.bat Windows backend entry point
|-- desktop/              Python, Tk, and pywebview desktop wrapper
|-- docs/                 Project documentation
|-- scripts/              Build helpers and generators
|-- src/                  SvelteKit frontend source
|-- static/               Frontend static source and generated Pyodide payload
|-- bench/                Proxy benchmark harness and results
|-- test/                 Test fixture data; not a full automated test suite
|-- Dockerfile            Multi-stage frontend/backend image
|-- docker-compose*.yaml  Deployment variants
|-- package.json          Frontend scripts and dependencies
|-- pyproject.toml        Python package metadata and wheel definition
|-- svelte.config.js      Static SPA output configuration
`-- vite.config.ts        Frontend bundler configuration
```

## Frontend map

### Application entry and state

| Path                                                                      | Role                                                                                                             |
| ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| [`src/routes/+layout.js`](../src/routes/+layout.js)                       | Declares client-only rendering with `ssr = false`                                                                |
| [`src/routes/+layout.svelte`](../src/routes/+layout.svelte)               | Global config, localization, socket, session restore, notifications, version reload, desktop compatibility hooks |
| [`src/routes/(app)/+layout.svelte`](<../src/routes/(app)/+layout.svelte>) | Auth gate and protected-shell preload of settings, models, tools, and banners                                    |
| [`src/routes/(app)/+page.svelte`](<../src/routes/(app)/+page.svelte>)     | Root protected page; mounts `Chat`                                                                               |
| [`src/lib/stores/index.ts`](../src/lib/stores/index.ts)                   | Shared application stores                                                                                        |
| [`src/lib/stores/chatList.ts`](../src/lib/stores/chatList.ts)             | Chat-list state and ordering                                                                                     |
| [`src/lib/constants.ts`](../src/lib/constants.ts)                         | Backend base URLs, build identifiers, and feature/file constants                                                 |

### Feature directories

[`src/lib/components/`](../src/lib/components/) has 12 direct feature directories: `admin`, `app`, `automations`, `calendar`, `channel`, `chat`, `common`, `icons`, `layout`, `notes`, `playground`, and `workspace`.

The 47 route pages live mainly under the protected `(app)` group. The main page families are:

- `admin/` for analytics, evaluations, functions, settings, and users;
- `workspace/` for knowledge, models, prompts, skills, and tools;
- `c/[id]/`, `channels/[id]/`, and `folders/[folderId]/` for conversations;
- `notes/`, `calendar/`, `automations/`, and `playground/` for workspace features;
- top-level `auth/`, `error/`, `s/[id]/`, and `watch/` pages.

### API clients

[`src/lib/apis/index.ts`](../src/lib/apis/index.ts) contains shared and root-level API calls. The 29 API subdirectories group domain clients. They largely track backend router domains, but the mapping is intentionally not exact: frontend-only groupings such as `streaming` exist, and several backend routers have no dedicated client directory.

## Backend map

### Application assembly

| Path                                                              | Role                                                                                                        |
| ----------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| [`backend/qwythos/main.py`](../backend/qwythos/main.py)           | FastAPI creation, lifespan, middleware, router mounts, chat endpoints, health/readiness, static SPA serving |
| [`backend/qwythos/env.py`](../backend/qwythos/env.py)             | Environment parsing, paths, database URL, deployment/build identity                                         |
| [`backend/qwythos/config.py`](../backend/qwythos/config.py)       | Runtime setting declarations, defaults, migrations from legacy config, startup static-asset preparation     |
| [`backend/qwythos/constants.py`](../backend/qwythos/constants.py) | Shared constants and error messages                                                                         |
| [`backend/qwythos/events.py`](../backend/qwythos/events.py)       | Typed event definitions, publication, and webhooks                                                          |
| [`backend/qwythos/tasks.py`](../backend/qwythos/tasks.py)         | Active task tracking and optional Redis coordination                                                        |

### Domain layers

| Directory                                                       | Role                                                                                                       |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| [`backend/qwythos/routers/`](../backend/qwythos/routers/)       | 31 HTTP router modules; analytics and SCIM registration are feature-gated                                  |
| [`backend/qwythos/models/`](../backend/qwythos/models/)         | 26 model modules containing 38 SQLAlchemy table declarations plus request/response models                  |
| [`backend/qwythos/internal/`](../backend/qwythos/internal/)     | SQLAlchemy engines/session helpers and internal infrastructure                                             |
| [`backend/qwythos/migrations/`](../backend/qwythos/migrations/) | Alembic migrations                                                                                         |
| [`backend/qwythos/utils/`](../backend/qwythos/utils/)           | Cross-domain auth, chat, middleware, plugins, tools, OAuth, Redis, scheduling, telemetry, and support code |
| [`backend/qwythos/retrieval/`](../backend/qwythos/retrieval/)   | Loaders, embeddings/retrieval logic, vector adapters, and web adapters                                     |
| [`backend/qwythos/socket/`](../backend/qwythos/socket/)         | Socket.IO server, rooms, collaboration, and event helpers                                                  |
| [`backend/qwythos/storage/`](../backend/qwythos/storage/)       | Local, S3, GCS, and Azure file provider abstraction                                                        |
| [`backend/qwythos/tools/`](../backend/qwythos/tools/)           | Built-in model-callable tools and knowledge filesystem                                                     |

### Chat pipeline path

Read these files in order for end-to-end chat work:

1. [`src/lib/components/chat/Chat.svelte`](../src/lib/components/chat/Chat.svelte) prepares UI state and submission.
2. [`src/lib/apis/openai/index.ts`](../src/lib/apis/openai/index.ts) sends `POST /api/chat/completions`.
3. [`backend/qwythos/main.py`](../backend/qwythos/main.py) validates model access, normalizes metadata, and creates UI background tasks or returns a direct response.
4. [`backend/qwythos/utils/middleware.py`](../backend/qwythos/utils/middleware.py) enriches payloads and processes streaming/non-streaming responses, tool loops, persistence, and events.
5. [`backend/qwythos/utils/chat.py`](../backend/qwythos/utils/chat.py) dispatches to direct, function/pipe, Ollama, OpenAI-compatible, or (when `model.council` is set) LLM Council execution.
6. [`backend/qwythos/routers/ollama.py`](../backend/qwythos/routers/ollama.py) and [`backend/qwythos/routers/openai.py`](../backend/qwythos/routers/openai.py) communicate with upstream providers; [`backend/qwythos/utils/council.py`](../backend/qwythos/utils/council.py) instead runs a 3-stage parallel-answer / peer-ranking / chairman-synthesis pipeline across several models for a single request.

### Provider credentials (OpenRouter, v0.12)

Production deployments are meant to use one OpenRouter key. Do not reintroduce per-feature URL+key pairs as the default path.

| Piece | Path |
| ----- | ---- |
| Env + defaults | [`backend/qwythos/config.py`](../backend/qwythos/config.py) (`OPENROUTER_API_KEY`, `openrouter.api_key` / `openrouter.base_url`) |
| Resolver and connection sync | [`backend/qwythos/utils/openrouter.py`](../backend/qwythos/utils/openrouter.py) |
| Chat connections + OpenRouter admin API | [`backend/qwythos/routers/openai.py`](../backend/qwythos/routers/openai.py) `GET/POST /openai/config` |
| RAG / audio / images inherit | [`backend/qwythos/routers/retrieval.py`](../backend/qwythos/routers/retrieval.py), [`backend/qwythos/routers/audio.py`](../backend/qwythos/routers/audio.py), [`backend/qwythos/routers/images.py`](../backend/qwythos/routers/images.py) |
| Admin UI | [`src/lib/components/admin/Settings/Connections.svelte`](../src/lib/components/admin/Settings/Connections.svelte) |
| First-run key | [`src/routes/auth/+page.svelte`](../src/routes/auth/+page.svelte) + `SignupForm.openrouter_api_key` |

Feature-specific `rag.openai.*`, `audio.*.openai.*`, and `image_generation.openai.*` keys remain as optional overrides. Empty / `https://api.openai.com/v1` with no key is treated as unset and inherits OpenRouter (or the first OpenAI-compatible chat connection). Extra providers and Ollama live under Connections → Advanced. Direct user connections are unchanged.

**Trap:** do not restore the old config.py block that rebound `OPENAI_API_KEY` / `OPENAI_API_BASE_URL` to whichever list index held `https://api.openai.com/v1`. That emptied every downstream feature default on OpenRouter-only installs.

### Model context: current date + default-on tools (v0.12.2)

Every chat completion — any provider, plus each stage of LLM Council — is given the current date unconditionally, and capable models get the web-search and code-interpreter tools without a manual per-message toggle, subject to existing admin gating.

| Piece | Path |
| ----- | ---- |
| Date-context helper | [`backend/qwythos/utils/task.py`](../backend/qwythos/utils/task.py) `get_current_date_context()` (shares `_current_date_parts()` with `prompt_template()`'s `{{CURRENT_DATE}}`/`{{CURRENT_TIME}}`/`{{CURRENT_WEEKDAY}}` substitution) |
| Injection: direct chat + Council stage 1 | [`backend/qwythos/utils/middleware.py`](../backend/qwythos/utils/middleware.py) `process_chat_payload()`, right after `metadata['system_prompt']` is set |
| Injection: Council stage 2/3 | [`backend/qwythos/utils/council.py`](../backend/qwythos/utils/council.py) — these stages build fresh message lists that bypass `process_chat_payload()`, so they inject their own system message |
| Web-search tool gating (unchanged) | [`backend/qwythos/utils/tools.py`](../backend/qwythos/utils/tools.py) `get_builtin_tools()` — still requires admin `ENABLE_WEB_SEARCH` + a configured search engine, per-model capability, and user permission |
| Web-search / code-interpreter default toggles | [`src/lib/components/chat/Chat.svelte`](../src/lib/components/chat/Chat.svelte) `setDefaults()` — seeds the real `webSearchEnabled`/`codeInterpreterEnabled` toggle state (not a separate overlay) each time the selected model changes, from `$settings.webSearch`/`$settings.codeInterpreter` defaulting to `'always'` when a user has never touched the corresponding row in Settings → Interface → "Web Search in Chat" / "Code Interpreter in Chat" (an explicit `null`, from turning it back to "Default", is still respected) |

**Trap:** seed the *actual* `webSearchEnabled`/`codeInterpreterEnabled` toggle state in `setDefaults()`, not a separate `raw || defaultOn` overlay value used only for the request payload. An OR-based overlay was tried first and reverted: the message-input switch is bound to the raw toggle, so it would show "off" while the feature was actually active, and — worse — toggling it off manually would have no effect, since the OR would keep forcing it active. Seeding the raw toggle directly keeps the visible switch, the request payload, and manual opt-out all in sync through one value.

**Trap:** do not fold the date line into `metadata['system_prompt']` itself — that value is replayed verbatim into native tool-call-loop restores and into subagent/timer runs that may fire on a later day. The date is injected straight into `form_data['messages']` instead.

### Retrieval path

| Path                                                                                                      | Role                                                                     |
| --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| [`backend/qwythos/routers/retrieval.py`](../backend/qwythos/routers/retrieval.py)                         | Retrieval API, runtime configuration, ingestion, and web-search dispatch |
| [`backend/qwythos/retrieval/loaders/`](../backend/qwythos/retrieval/loaders/)                             | 10 loader modules                                                        |
| [`backend/qwythos/retrieval/utils.py`](../backend/qwythos/retrieval/utils.py)                             | Vector, BM25, hybrid, rerank, and result merge logic                     |
| [`backend/qwythos/retrieval/vector/factory.py`](../backend/qwythos/retrieval/vector/factory.py)           | Selects one of 13 vector database families                               |
| [`backend/qwythos/retrieval/vector/async_client.py`](../backend/qwythos/retrieval/vector/async_client.py) | Async facade over synchronous vector clients                             |
| [`backend/qwythos/retrieval/vector/dbs/`](../backend/qwythos/retrieval/vector/dbs/)                       | 15 concrete adapter modules                                              |
| [`backend/qwythos/retrieval/web/`](../backend/qwythos/retrieval/web/)                                     | 31 provider adapters plus shared `main.py` and `utils.py`                |

## Desktop and runtime flows

The current Windows desktop implementation has two layers:

1. [`desktop/launcher.pyw`](../desktop/launcher.pyw) runs with system `pythonw`, creates `.venv` on first use, installs `backend/requirements.txt` plus pywebview, and starts the app with the virtual environment.
2. [`desktop/app.py`](../desktop/app.py) validates the frontend build, matches or starts a local backend on ports 8080-8099, waits for readiness, and opens a persistent pywebview profile.

[`desktop/Create Desktop Shortcut.ps1`](../desktop/Create%20Desktop%20Shortcut.ps1) creates the Windows shortcut. No Tauri configuration or Tauri launcher exists in this directory. Conditional `window.electronAPI` code remains in the frontend root layout as compatibility code, not as the current desktop host.

## Build and packaging map

| Path                                                          | Role                                                                             |
| ------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| [`package.json`](../package.json)                             | `dev`, `build`, `check`, lint, format, and frontend-test commands                |
| [`scripts/prepare-pyodide.js`](../scripts/prepare-pyodide.js) | Prepares offline browser Python assets before dev/build                          |
| [`svelte.config.js`](../svelte.config.js)                     | Static adapter, `build/` output, SPA fallback, version polling                   |
| [`vite.config.ts`](../vite.config.ts)                         | SvelteKit/Vite plugins, build identifiers, source maps, WASM copy, worker format |
| [`Dockerfile`](../Dockerfile)                                 | Node frontend stage plus Python 3.11 backend stage                               |
| [`backend/start.sh`](../backend/start.sh)                     | Container/server secret setup and Uvicorn launch                                 |
| [`docker-compose.yaml`](../docker-compose.yaml)               | Qwythos plus Ollama with named volumes                                           |
| [`railway.json`](../railway.json)                             | Dockerfile build and `/health` deployment check                                  |
| [`pyproject.toml`](../pyproject.toml)                         | Python dependencies, Hatchling build, packaged frontend mapping                  |
| [`hatch_build.py`](../hatch_build.py)                         | Runs npm install/build during Python wheel creation                              |

The frontend build has four consumers: FastAPI static serving, Docker, the Hatch wheel, and the pywebview desktop host. A build-path or deployment-identity change should be checked across all four.

## Change-sensitive files

These files are high-risk because they combine several runtime responsibilities or define contracts used across layers.

| File                                                                                            | Why changes have broad impact                                                                        |
| ----------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| [`backend/qwythos/main.py`](../backend/qwythos/main.py)                                         | Central ASGI assembly plus chat, static serving, health, and feature-gated router registration       |
| [`backend/qwythos/utils/middleware.py`](../backend/qwythos/utils/middleware.py)                 | Shared request enrichment and response/tool/event processing for nearly every chat mode              |
| [`backend/qwythos/config.py`](../backend/qwythos/config.py)                                     | Large registered configuration surface, database-backed defaults, import/startup side effects        |
| [`backend/qwythos/env.py`](../backend/qwythos/env.py)                                           | Low-level path, database, deployment, and process-environment contract                               |
| [`backend/qwythos/internal/db.py`](../backend/qwythos/internal/db.py)                           | Sync and async engine/session behavior shared by models, migrations, and health checks               |
| [`backend/qwythos/socket/main.py`](../backend/qwythos/socket/main.py)                           | Authentication, room membership, shared pools, collaboration, and Redis/non-Redis behavior           |
| [`src/routes/+layout.svelte`](../src/routes/+layout.svelte)                                     | Global client bootstrap, socket lifecycle, auth restoration, version reload, and browser integration |
| [`src/routes/(app)/+layout.svelte`](<../src/routes/(app)/+layout.svelte>)                       | Protected route gate and parallel initialization of user-scoped application state                    |
| [`src/routes/auth/+page.svelte`](../src/routes/auth/+page.svelte)                               | Local/LDAP/OAuth completion, token storage, onboarding, and redirect safety                          |
| [`src/lib/components/chat/Chat.svelte`](../src/lib/components/chat/Chat.svelte)                 | Main frontend conversation state and submission orchestration                                        |
| [`backend/qwythos/storage/provider.py`](../backend/qwythos/storage/provider.py)                 | Import-time provider selection and local/cloud file lifecycle                                        |
| [`backend/qwythos/retrieval/vector/factory.py`](../backend/qwythos/retrieval/vector/factory.py) | Import-time vector-client selection used throughout retrieval                                        |
| [`desktop/app.py`](../desktop/app.py)                                                           | Couples build identity, port ownership, server readiness, browser persistence, and shutdown          |

When editing one of these, verify its immediate callers and both configured branches where relevant, especially Redis/non-Redis, SQLite/PostgreSQL, UI-session/direct API, local/cloud storage, and repository/package frontend paths.

## Generated and runtime directories

Do not treat these as primary source locations.

| Path                                              | Produced or owned by               | Notes                                                                                 |
| ------------------------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------- |
| `build/`                                          | SvelteKit/Vite                     | Static SPA output; ignored by Git and rebuilt by `npm run build`                      |
| `.svelte-kit/`                                    | SvelteKit                          | Generated types and intermediate build state                                          |
| `node_modules/`                                   | npm                                | Frontend dependencies                                                                 |
| `.venv/`                                          | Python tooling or desktop launcher | Local Python environment                                                              |
| `backend/data/`                                   | Running backend                    | Default database, uploads, caches, vectors, logs, and desktop webview profile         |
| `backend/.webui_secret_key`                       | Desktop or server bootstrap        | Local signing secret; ignored and never suitable for source control                   |
| `.env` and local `.env.*` files                   | Developer or deployment tooling    | Local runtime configuration; ignored except for the committed `.env.example` template |
| `backend/qwythos/static/`                         | Backend startup                    | Runtime-populated mirror of build-time static assets                                  |
| `static/pyodide/`                                 | `scripts/prepare-pyodide.js`       | Downloaded Pyodide distribution and wheel payload                                     |
| `desktop/setup.log`                               | Desktop bootstrap                  | First-run dependency installation log                                                 |
| `frontend-build.log`                              | Local build workflow               | Build log, not source                                                                 |
| `__pycache__/`, `.pytest_cache/`, coverage output | Python/test tools                  | Disposable generated artifacts                                                        |
| `work/`                                           | Local agent/developer scratch work | Ignored workspace, not product source                                                 |

The root `test/` directory currently contains fixture data plus [`test/test_openrouter_credentials.py`](../test/test_openrouter_credentials.py) for the OpenRouter credential resolver. The visible frontend unit test is [`src/lib/shortcuts.test.ts`](../src/lib/shortcuts.test.ts); benchmark code lives under [`bench/`](../bench/). Do not infer full subsystem coverage from the directory name.

## Common verification commands

Run from the repository root:

```powershell
npm run check
npm run test:frontend
npm run build
```

For backend startup in a development shell, [`backend/dev.sh`](../backend/dev.sh) runs Uvicorn with reload on port 8080. Container behavior should be checked through the Dockerfile and `backend/start.sh`, because it includes additional secret, Playwright, Ollama, CUDA, and worker setup.
