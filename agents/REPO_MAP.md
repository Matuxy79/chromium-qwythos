# Repository Map — Qwythos (chromium-qwythos)

_Last scan: 2026-08-17 · version 0.11.0 · Python 3.11–3.12 · Svelte 5 / SvelteKit 2_

## What this repo is

Private fork of **Open WebUI**, rebranded **Qwythos**, maintained by John
Matukutire. Fork-specific additions on top of upstream:

- **Chromium Wyvern** interface/branding (auth screen + model-stack animation)
- **Windows pywebview desktop launcher** (`desktop/`)
- **Rust backend spike** (`rust-backend/` + `bench/`) evaluating a gateway rewrite
- **LLM Council** (`routers/council.py`, `utils/council.py`, `utils/subagents.py`,
  frontend `lib/apis/council`, route `(app)/council`). Also a first-class
  chat model `llm-council` injected in `utils/models.py` (arena-shaped,
  config-driven) when a roster is configured.
- Skills, terminals, automations, calendar, notes, channels (some fork-added,
  some newer upstream features — check git blame before assuming)

License situation is layered (Open WebUI License branding condition + history) —
see `LICENSE`, `LICENSE_HISTORY`, `LICENSE_NOTICE`, `FORK_NOTICE.md` before any
redistribution.

## Top-level layout

| Path | What it is |
|---|---|
| `backend/qwythos/` | FastAPI backend package (the bulk of the app, ~109k LOC) |
| `src/` | SvelteKit frontend (built to `build/`, adapter-static) |
| `rust-backend/` | Early axum rewrite spike — **does not compile** (see Known Traps) |
| `desktop/` | Windows pywebview launcher (`launcher.pyw` → `app.py`) |
| `bench/` | Rust-vs-Python gateway benchmark (answered: not worth it) |
| `docs/` | Human docs: ARCHITECTURE, CODEBASE_MAP, PUBLISHING_GUIDE, SECURITY + screenshots |
| `scripts/` | `prepare-pyodide.js` (build step), `generate-brand-icons.py`, `generate-sbom.sh` |
| `static/` | Public assets incl. `pyodide/` (fetched at build time) and `static/static/` brand icons |
| `test/test_files/` | Sample documents for manual RAG testing |
| `.github/workflows/` | CI: backend.yaml, frontend.yaml, docker.yaml, release.yml, release-pypi.yml |

## Backend — `backend/qwythos/`

Entry point: `main.py` (uvicorn `qwythos.main:app`, port 8080). Mounts Socket.IO
at `/ws`, plus routers (all from `routers/`):

- Model/provider: `ollama` `/ollama`, `openai` `/openai`, `pipelines`, `models`
- Core: `auths`, `users`, `groups`, `chats`, `folders`, `files`, `configs`, `utils`
- Fork-era features: `council`, `channels`, `notes`, `memories`, `automations`,
  `calendar`, `terminals`, `skills`, `analytics`, `notifications`
- Knowledge/RAG: `knowledge`, `retrieval`
- Extensibility: `tools`, `functions`, `prompts`, `evaluations`
- Misc: `tasks`, `images`, `audio`, `scim` (conditional), `webhooks via utils`

Middleware stack (order matters, `main.py:870-907`): CORS → Compress →
Redirect → SecurityHeaders → CommitSession → AuthToken → WebsocketUpgradeGuard.

Other key modules:

- `config.py` / `env.py` — persistent config + env var loading (AppConfig pattern)
- `models/` — 26 SQLAlchemy model modules; sessions via `internal/db.py`
- `utils/` — ~50 modules: `auth.py`, `oauth.py`, `chat.py`, `middleware.py`,
  `plugin.py`, `filter.py`, `tools.py`, `mcp/`, `telemetry/`, `images/`,
  `council.py`, `subagents.py`, `context_compaction.py`
- `retrieval/` — RAG: `loaders/` (10 engines), `vector/dbs/` (15 vector backends),
  `web/` (33 search providers), `models/` (rerankers)
- `socket/main.py` — Socket.IO server; `storage/provider.py` — local/S3/GCS/Azure
- `migrations/` — alembic (`alembic.ini` in package root)
- `tools/builtin.py`, `tools/knowledge_fs.py` — built-in tool implementations

Run scripts: `backend/dev.sh` (reload, CORS for 5173/8080), `backend/start.sh`
(container entrypoint: secret key, Ollama/CUDA/Playwright handling).
Deps: `requirements.txt` (full), `requirements-min.txt` (slim).

## Frontend — `src/`

SvelteKit 2 + Svelte 5 + Vite 5 + TS + Tailwind 4. Build runs
`node scripts/prepare-pyodide.js` first (every `dev`/`build` script).

- `src/routes/` — `(app)/` is the main shell: `home`, `c` (chats), `admin`,
  `workspace`, `playground`, `channels`, `notes`, `calendar`, `automations`,
  `council`, `folders`. Plus `auth/`, `s/` (shared), `watch/`, `error/`.
- `src/lib/apis/` — one directory per backend feature (~30), mirrors the router
  list above, plus `streaming/`.
- `src/lib/components/` — `chat/` (the beast: MessageInput, Messages/, Settings/,
  ModelSelector/), `admin/`, `workspace/`, `layout/`, `common/`, `icons/`, etc.
- `src/lib/stores/`, `src/lib/utils/`, `src/lib/i18n/` (60+ locales),
  `src/lib/pyodide/`, `src/lib/workers/`.
- Config: `svelte.config.js` (adapter-static), `vite.config.ts`,
  `i18next-parser.config.ts` (`npm run i18n:parse` regenerates locales).

Brand strings ("qwythos") live in auth page, settings About/General, config API
defaults. Only "wyvern" hit in code: `src/routes/auth/+page.svelte`.

## rust-backend/ — spike status

axum 0.8 + sqlx (sqlite/postgres) + JWT(HS*/argon2) + reqwest streaming proxy.
Present: `main.rs`, `config.rs`, `error.rs`, `db/{mod,models}.rs`,
`middleware/{auth,cors}.rs` (645 LOC total).

**Trap: `main.rs` declares `mod routes; mod services;` but those directories
do not exist — the crate does not build.** Nothing references it from the Python
app, Docker, or CI. Treat as design sketch until routes/services land.

## bench/ — already answered question

"Should the backend be rewritten in Rust?" Verdict (see `bench/RESULTS.md`):
Rust proxy saves only ~0.15–0.35 ms/request (TTFT) vs Python — under 0.1% of
real LLM latency; the one material win is ~10× memory (6 MB vs 64 MB RSS).
Benchmark harness: `run_bench.py` / `bench.py` driving `py_proxy.py` (FastAPI)
and `rs_proxy/` (axum) against `mock_upstream.py`.

## desktop/ — Windows launcher

`launcher.pyw` (stdlib only, tkinter progress UI): creates `.venv`, installs
`backend/requirements.txt` + pywebview, hands off to `app.py`.
`app.py`: starts/reuses uvicorn on 127.0.0.1:8080 (scans 20 ports), verifies the
production build in `build/` incl. brand assets, opens pywebview window; kills
the server on close only if it started it. `Create Desktop Shortcut.ps1` makes
the shortcut.

## Build / dev / CI

- Frontend: `npm ci && npm run build` (or `npm run dev`, port 5173).
- Backend dev: `cd backend && ./dev.sh` (needs venv with requirements).
- Lint/test: `npm run lint` (eslint + svelte-check + pylint),
  `npm run test:frontend` (vitest), pre-commit hooks configured.
- Python packaging: `pyproject.toml` (hatch, `hatch_build.py`), package `qwythos`,
  Python >=3.11 <3.13.
- Docker: root `Dockerfile` + many `docker-compose.*.yaml` variants (gpu, amd,
  api, data, otel, playwright, a1111-test). Makefile wraps compose.
- Workflows: `backend.yaml` (Python CI), `frontend.yaml` (build), `docker.yaml`
  (image publish), `release.yml`, `release-pypi.yml`. `codespell.disabled`,
  `lint-backend.disabled`, `lint-frontend.disabled` are turned off on purpose.

## Conventions for agents

- Indent with **tabs** in JS/TS/Svelte (prettier config); Python follows ruff.
- Backend package is `qwythos`, import as `from qwythos...` (renamed from
  `open_webui` — don't reintroduce the old name).
- New backend feature = router in `routers/` + model in `models/` +
  `include_router` in `main.py` + API dir in `src/lib/apis/` + i18n strings.
- Don't commit secrets; `.env.example` lists the supported env vars.
- Update `agents/LOG.md` and this map when you change structure.
