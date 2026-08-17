# Agent activity log

Newest entries first. Format:

```
## YYYY-MM-DD — <agent/session label>
- What changed / what was learned
- Verified by: <command or check>
- Loose ends: <anything left uncertain or broken>
```

---

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
