# Data Persistence — Chat History Across Builds

Qwythos stores **all persistent data** (chat history, users, settings, uploads, browser auth) in a single data directory. This document explains where that data lives, how it survives app rebuilds, and how to back it up.

## Where data lives

| Scenario | Data directory | Resolved by |
|---|---|---|
| **Docker** | `/app/backend/data` | Container path, mount a volume here |
| **Desktop (pywebview)** | `backend/data/` | `desktop/app.py:26` |
| **Local dev (source)** | `backend/data/` | `backend/qwythos/env.py:222` |
| **Installed package** | `backend/qwythos/data/` | `backend/qwythos/env.py:225` (auto-migrated from `backend/data/`) |

Set the `DATA_DIR` environment variable to override the default location.

## What's inside the data directory

```
backend/data/
├── webui.db              # SQLite database — ALL chat history, users, settings
├── uploads/              # User-uploaded files (documents, images, audio)
├── cache/                # Application cache (tiktoken encodings, etc.)
│   └── tiktoken/
├── vector_db/            # Local vector databases (Chroma, Milvus, Qdrant)
├── desktop-webview/      # Browser profile for desktop launcher (auth tokens, localStorage)
├── api_keys_backup.json  # Auto-backup of critical API keys (restore on DB wipe)
├── desktop-server.log    # Server log (ignored in .gitignore)
└── .webui_secret_key     # JWT secret key (persisted across restarts)
```

The `webui.db` file is the critical one — it contains every conversation, user account, API key, and configuration setting.

## Persistence across builds

### Docker (`docker-compose.yaml`)

```yaml
volumes:
  - qwythos:/app/backend/data
```

The named volume `qwythos` persists across `docker compose down`, rebuilds, and image updates. **Do not** use `docker compose down -v` — that deletes the volume and all chat data.

**Railway:** Attach a Railway Volume at `/app/backend/data` in the dashboard. See [RAILWAY_DEPLOYMENT.md](./RAILWAY_DEPLOYMENT.md). Do not add a `VOLUME` instruction to the Dockerfile — Railway's builder rejects it.

### Desktop app (`desktop/app.py`)

The pywebview launcher uses `backend/data/` directly on disk. Data persists across:
- Frontend rebuilds (`npm run build`) — the `build/` directory is separate from `backend/data/`
- App restarts — the browser profile (`desktop-webview/`) keeps auth tokens, so you stay logged in
- Backend code changes — the SQLite database is untouched by code updates

The secret key is stored at `backend/.webui_secret_key` (also persisted).

### Local development

Running `backend/dev.sh` or `python -m uvicorn qwythos.main:app` from the `backend/` directory uses `backend/data/`. This directory:
- Is **excluded from git** (see `.gitignore` — `backend/data/*` with `!backend/data/.gitkeep`)
- Survives `git clean`, `npm run build`, and code rebuilds
- Is **not** deleted by the Docker build (`.dockerignore` excludes `backend/data/*`)

### Installed package (`pip install qwythos`)

When installed as a package, data moves to `backend/qwythos/data/` (inside the package directory). The migration in `env.py`:
1. Copies all files from `backend/data/` to `backend/qwythos/data/`
2. Creates a zip backup at `backend/qwythos_data.zip`
3. Removes the old `backend/data/` directory

## Backup and restore

### Manual backup

```bash
# Stop the app first (SQLite doesn't like concurrent writes)
# Then copy the entire data directory:
cp -r backend/data backend/data-backup-$(date +%Y%m%d)
```

Or just the database (most important):
```bash
cp backend/data/webui.db backend/webui-backup-$(date +%Y%m%d).db
```

### Restore

```bash
# Stop the app, then:
cp backend/data-backup-20260127/webui.db backend/data/webui.db
# Restart the app
```

### Docker volume backup

```bash
# Backup
 docker run --rm -v qwythos:/data -v $(pwd):/backup alpine \
   tar czf /backup/qwythos-data-$(date +%Y%m%d).tar.gz -C /data .

# Restore
 docker run --rm -v qwythos:/data -v $(pwd):/backup alpine \
   tar xzf /backup/qwythos-data-20260127.tar.gz -C /data
```

## What gets lost (and what doesn't)

| Action | Chat data | Auth tokens | Uploaded files | Settings |
|---|---|---|---|---|
| `npm run build` (frontend rebuild) | ✅ Persists | ✅ Persists (desktop: `desktop-webview/`) | ✅ Persists | ✅ Persists |
| `docker compose restart` | ✅ Persists (volume) | ✅ Persists | ✅ Persists | ✅ Persists |
| `docker compose down` (no `-v`) | ✅ Persists (volume) | ✅ Persists | ✅ Persists | ✅ Persists |
| `docker compose down -v` | ❌ **DELETED** | ❌ Deleted | ❌ Deleted | ❌ Deleted |
| `git clean -fdx` | ⚠️ Deleted if not ignored | ⚠️ Deleted | ⚠️ Deleted | ⚠️ Deleted |
| `pip install --force-reinstall qwythos` | ✅ Migrated to package dir | ✅ Migrated | ✅ Migrated | ✅ Migrated |
| Delete `backend/data/` manually | ❌ **DELETED** | ❌ Deleted | ❌ Deleted | ❌ Deleted |

## Code-Level API Persistence (Railway / Ephemeral Deployments)

Beyond volume mounts, Qwythos includes code-level mechanisms to preserve API keys across deployments — even when the database is wiped.

### 1. Volume Mount Detection

At startup, the app checks if the data directory is a mounted volume:

- **`backend/start.sh`** — bash-level check using `mountpoint` (Linux containers)
- **`backend/qwythos/env.py`** — Python-level check with `/proc/mounts` fallback

If no volume is detected, a loud warning is logged:

```
⚠️  WARNING: Data directory is NOT a mounted volume!
   Path: /app/backend/data
   Railway detected. Attach a Volume at /app/backend/data in the Railway dashboard...
```

### 2. Forced Environment Variable Sync (`FORCE_ENV_CONFIG`)

When `FORCE_ENV_CONFIG=true` (auto-enabled on Railway), critical API keys are synced from environment variables into the database **on every startup**:

| Environment Variable | Config Key | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | `openrouter.api_key` | OpenRouter API key |
| `OPENROUTER_API_BASE_URL` | `openrouter.base_url` | OpenRouter base URL |
| `OPENAI_API_KEY` | `openai.api_keys` | OpenAI-compatible API keys (semicolon-separated) |
| `OPENAI_API_BASE_URL` | `openai.api_base_urls` | OpenAI-compatible base URLs (semicolon-separated) |
| `GEMINI_API_KEY` | `image_generation.gemini.api_key` | Gemini API key |
| `AUDIO_TTS_OPENAI_API_KEY` | `audio.tts.openai.api_key` | TTS API key |
| `AUDIO_STT_OPENAI_API_KEY` | `audio.stt.openai.api_key` | STT API key |

**How it works:**
1. On startup, `sync_env_to_config()` reads the environment variables
2. Values are upserted into the database, **overriding** any existing DB values
3. Only API keys are synced — user preferences, UI settings, and other config are never overridden

**Railway setup without a volume:**
```bash
# In Railway dashboard → Variables:
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_API_BASE_URL=https://openrouter.ai/api/v1
```

On every deploy, the app re-seeds these keys into the fresh database.

### 3. API Key Backup File

Critical API keys are automatically backed up to `DATA_DIR/api_keys_backup.json`:

```json
{
  "_meta": {
    "created_at": "2026-10-27T14:00:00",
    "version": "1.0"
  },
  "keys": {
    "openrouter.api_key": "sk-or-v1-...",
    "openrouter.base_url": "https://openrouter.ai/api/v1",
    "openai.api_keys": ["sk-or-v1-..."],
    "openai.api_base_urls": ["https://openrouter.ai/api/v1"]
  }
}
```

**Restore behavior:** If the database is empty (wiped) but the backup file exists (volume survived), the app automatically restores API keys from the backup on startup and logs a warning.

**File permissions:** `0600` (owner read/write only) — the file contains secrets.

### 4. Startup Persistence Status (Railway)

On Railway, the app logs its persistence configuration at startup:

```
🚂 Railway environment detected
   FORCE_ENV_CONFIG enabled — API keys will be synced from environment variables on every startup
   API key backup file found: /app/backend/data/api_keys_backup.json
```

### 5. Railway Deployment Checklist

| Step | Action | Result |
|---|---|---|
| 1 | Attach a Volume at `/app/backend/data` in Railway dashboard | **Best:** All data persists (chats, keys, users, files) |
| 2 | Set `OPENROUTER_API_KEY` as a Railway environment variable | API keys survive DB wipes (with `FORCE_ENV_CONFIG` auto-enabled) |
| 3 | Set `WEBUI_SECRET_KEY_FILE=/app/backend/data/.webui_secret_key` | Secret key persists (prevents session invalidation) |
| 4 | (Optional) Set `ADMIN_USER_EMAIL` + `ADMIN_USER_PASSWORD` | Admin account auto-created on fresh deploys |

**Without a volume:** Steps 2–4 keep API keys and admin access working, but **chat history and user data are still lost** on every deploy.

## Security note

The data directory contains:
- **Chat history** — private conversations
- **API keys** — stored in the database and `backend/.webui_secret_key`
- **User credentials** — hashed passwords
- **Uploaded files** — potentially sensitive documents
- **`api_keys_backup.json`** — plaintext API keys (permissions: `0600`)

**Never commit `backend/data/` or `backend/qwythos/data/` to git.** The `.gitignore` excludes these directories; the `.gitkeep` files only preserve the directory structure.
