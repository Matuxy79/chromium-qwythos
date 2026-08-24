# Codebase Orphanage Scan Report

**Date:** 2026-08-24
**Scope:** Dead frontend components, dead backend components, orphaned directories, unused API surface
**Method:** Automated reference scanning (import graph analysis) + manual verification of dynamic-import edge cases (`svelte:component`, `import()`, bracket-access, route params)

---

## Summary

| Category | Count | Risk |
|----------|-------|------|
| Orphaned directories (entire subsystems) | 2 | Safe to delete |
| Dead Svelte components | 37 | Safe to delete |
| Dead TS modules | 1 | Safe to delete |
| Dead frontend API modules | 1 | Safe to delete |
| Dead exported API functions | 28 | Safe to delete |
| Dead backend router (unused endpoints) | 1 | Verify external API consumers first |

---

## 1. Orphaned Directories (User-Confirmed Dead)

### `bench/` — Benchmarking spike
Standalone benchmark harness built to evaluate a Rust (Axum) rewrite of the Python backend. Contains mock upstream server, Python/Rust proxy implementations, and load-driver scripts. **The question it investigated has been answered** (Rust offered only ~0.15–0.35 ms TTFT improvement — negligible vs. LLM inference latency, per `bench/RESULTS.md`). Not referenced by Dockerfile, `pyproject.toml`, CI, or the desktop app. **Safe to delete.**

### `rust-backend/` — Early Rust rewrite spike
Part of the same exploration as `bench/`. Does not compile in its current state and is unreferenced by any production build path. **Safe to delete.**

---

## 2. Dead Frontend Components (37 Svelte files)

Verified: no dynamic imports (`import()`), no `svelte:component this={...}` string-based resolution, no bracket-access patterns reference these files.

### Non-icon components (8)

| File | Notes |
|------|-------|
| `src/lib/components/chat/Messages/Citations/CitationsModal.svelte` | Superseded modal; citations render inline |
| `src/lib/components/chat/TagChatModal.svelte` | Zero references anywhere |
| `src/lib/components/workspace/Tools/AddToolMenu.svelte` | Zero references |
| `src/lib/components/admin/Functions/AddFunctionMenu.svelte` | Zero references |
| `src/lib/components/common/SlideShow.svelte` | Zero references |
| `src/lib/components/common/Marquee.svelte` | Zero references |
| `src/lib/components/notes/AIMenu.svelte` | Zero references |
| `src/lib/components/automations/TerminalDropdown.svelte` | Zero references |

### Dead icon components (29)

`src/lib/components/icons/`:
`UserBadgeCheck`, `PhotoSolid`, `DocumentCheck`, `BookmarkSlash`, `FaceId`, `DocumentChartBar`, `Cog6Solid`, `Lifebuoy`, `UsersSolid`, `ArrowDownTray`, `Github`, `MenuLines`, `Bookmark`, `CalendarSolid`, `Headphone`, `KeyframePlus`, `QuestionMarkCircle`, `PagePlus`, `SparklesSolid`, `AdjustmentsHorizontalOutline`, `CommandLineSolid`, `Bars3BottomLeft`, `UserCircleSolid`, `PeopleTag`, `ArrowTurnDownRight`, `Glasses`, `FloppyDisk`, `BookOpen`, `ChartBar`

---

## 3. Dead Frontend Modules

| File | Notes |
|------|-------|
| `src/lib/utils/_template_old.ts` | Explicitly named "old" template; zero references |
| `src/lib/apis/council/index.ts` | **Entire module dead.** The LLM Council feature was reworked to route through the normal chat pipeline (`utils/council.py` backend-side) and reads config via `getCouncilConfig`/`setCouncilConfig` from the `configs` API. No file imports `apis/council`. |

---

## 4. Dead Exported API Functions (28)

Each function below is exported but never imported by any component, route, or module:

| Module | Dead functions |
|--------|---------------|
| `apis/auths` | `deleteAPIKey` |
| `apis/calendar` | `setDefaultCalendar`, `getCalendarEventById`, `rsvpCalendarEvent`, `searchCalendarEvents` |
| `apis/configs` | `getOAuthClientAuthorizationUrl` |
| `apis/council` | `getCouncilRunConfig`, `runCouncil` *(whole module dead)* |
| `apis/files` | `getFileProcessStatus`, `getFiles` |
| `apis/knowledge` | `createExternalKnowledgeConnection`, `deleteExternalKnowledgeConnection`, `testExternalKnowledgeConnection`, `streamPendingKnowledgeFiles` |
| `apis/memories` | `queryMemory` |
| `apis/notes` | `getNotes` |
| `apis/ollama` | `generatePrompt`, `generateEmbeddings`, `generateTextCompletion`, `generateChatCompletion` |
| `apis/prompts` | `getPromptHistoryEntry`, `getPromptDiff` |
| `apis/retrieval` | `queryDoc`, `queryCollection`, `resetUploadDir` |
| `apis/skills` | `getSkillList` |
| `apis/users` | `updateUserRole` |

---

## 5. Dead Backend Components

### `routers/council.py` — Registered but unused endpoints ⚠️
Registered in `main.py` at `/api/v1/council` with two endpoints:
- `GET /config`
- `POST /run`

**No frontend code calls `/api/v1/council/*`.** The council feature executes via `utils/council.py` (invoked from `utils/chat.py` and `tools/builtin.py`) and its configuration is managed through the `configs` router. The router is dead from the UI's perspective — but since it is a public HTTP API surface, confirm no external scripts/API consumers depend on it before removal.

### Python modules: **none dead**
Every module under `backend/qwythos/` (routers, models, utils, retrieval, socket, storage, tools, internal) is imported by at least one live file. The backend import graph is clean.

---

## 6. Verified ALIVE (Previously Suspected — Cleared)

| Item | Verdict | Evidence |
|------|---------|----------|
| `desktop/` | **Alive** | Documented Windows pywebview launcher (`docs/ARCHITECTURE.md` §Windows desktop launcher); wraps the same web build |
| `routers/pipelines.py` | **Alive** | All pipeline API functions consumed by `admin/Settings/Pipelines.svelte`, registered in admin Settings tabs |
| `routes/watch/` | **Alive** | Redirects `?v=<id>` → `/?youtube=<id>`, consumed by `Chat.svelte:1844` for YouTube ingestion |
| `routes/(app)/council/` | **Alive (stub)** | Intentional redirect stub → `/?model=llm-council`; documented in-file |
| `routers/scim.py` | **Alive** | System-to-system SCIM 2.0 identity protocol; no frontend expected |
| Static assets | **All alive** | `welcome.mp4/webp`, `greeting.mp3`, `notification.mp3`, `user.png`, `opensearch.xml`, etc. all referenced |
| `lib/pyodide`, `lib/runtime`, `lib/workers` | **Alive** | Imported by CodeBlock, ResponseMessage, CallOverlay, PyodideFileNav, layout, etc. |

---

## 7. Low-Priority Observations

- `test/test_openrouter_credentials.py` — manual utility script, not wired into any test runner config.
- `contribution_stats.py` — not referenced by CI configs; appears to be a manually-run utility.
- Root-level PDFs (`Qwythos-gguf*.pdf`) — documentation artifacts, not code.
- `src/lib/apis/streaming/index.ts` — not an orphan, but misnamed: it targets `/api/chat/completions` and chats endpoints rather than a "streaming" router.

---

## 8. Recommended Cleanup Order

1. **Delete `bench/` and `rust-backend/`** — zero production impact (user-verified).
2. **Delete the 37 dead Svelte components** — zero references, zero dynamic-load risk.
3. **Delete `src/lib/utils/_template_old.ts` and `src/lib/apis/council/`** — zero references.
4. **Prune the 28 dead API functions** — reduces bundle surface and maintenance noise.
5. **Hold on `routers/council.py`** — verify no external API consumers, then remove router + its `main.py` registration.
6. Re-run `npm run build` (or `vite build`) and backend import smoke test after cleanup to confirm nothing breaks.