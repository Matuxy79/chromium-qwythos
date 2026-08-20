# Railway Deployment Guide

## Critical: Persistent Storage Configuration

**⚠️ IMPORTANT:** Railway uses ephemeral storage by default. Without configuring a persistent volume, **all data will be lost on every deployment or restart**, including:

- API keys (OpenRouter, OpenAI, etc.)
- User accounts and authentication tokens
- Chat history
- Uploaded files
- Configuration settings
- Vector database data

This is the root cause of the "ephemeral API key" behavior where saved OpenRouter keys disappear after redeployment.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Qwythos Container                             │
├─────────────────────────────────────────────────────────────────┤
│  /app/backend/data/                                             │
│  ├── webui.db          ← SQLite database (users, API keys,     │
│  │                        chats, config - ALL persistent data)   │
│  ├── uploads/          ← User uploaded files                    │
│  ├── cache/            ← Tiktoken and other caches              │
│  ├── vector_db/        ← Chroma/vector database data            │
│  └── .webui_secret_key ← JWT secret key                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              MUST be mounted to persistent volume
```

The application stores ALL persistent data in `/app/backend/data/`. The SQLite database (`webui.db`) contains:
- User accounts and credentials
- API keys (stored via the Config model)
- Chat history
- Model configurations
- All application settings

---

## Solution 1: Railway Volume (Recommended for Simple Deployments)

### Step-by-Step Setup

1. **Open Railway Dashboard**
   - Go to your project at [railway.com](https://railway.com)
   - Select your Qwythos service

2. **Add a Volume**
   - Click on your service
   - Go to **Settings** tab
   - Scroll to **Volumes** section
   - Click **Add Volume**
   - Set **Mount Path**: `/app/backend/data`
   - Click **Add**

3. **Redeploy**
   - Railway will automatically redeploy with the volume attached
   - Your data will now persist across deployments

### railway.json Configuration

The `railway.json` in this repository includes the volume configuration:

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  },
  "volume": {
    "mountPath": "/app/backend/data"
  }
}
```

> **Note:** The `volume` field in railway.json documents the requirement. You must still configure the volume in the Railway dashboard for it to take effect.

---

## Solution 2: External Database (Recommended for Production)

For production deployments with higher reliability requirements, use an external PostgreSQL database instead of SQLite.

### Benefits

- Data persists independently of container lifecycle
- Better performance under concurrent load
- Easier backups and point-in-time recovery
- Supports horizontal scaling (multiple app instances)

### Setup with Railway PostgreSQL

1. **Add PostgreSQL Plugin**
   - In Railway dashboard, click **New**
   - Select **Database** → **PostgreSQL**
   - Railway will create a PostgreSQL instance

2. **Configure Environment Variables**
   - Copy the `DATABASE_URL` from the PostgreSQL service
   - Add it to your Qwythos service environment variables:
   ```
   DATABASE_URL=postgresql://user:password@host:5432/railway
   ```

3. **Redeploy**
   - The application will automatically run migrations on startup
   - All data will now be stored in PostgreSQL

### Setup with External Providers

You can also use external database providers:

| Provider | Connection String Format |
|----------|-------------------------|
| Supabase | `postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres` |
| Neon | `postgresql://[USER]:[PASSWORD]@[HOST]/[DB]?sslmode=require` |
| PlanetScale | `postgresql://[USER]:[PASSWORD]@[HOST]/[DB]?sslmode=require` |
| Railway | Auto-configured via plugin |

---

## Solution 3: S3-Compatible Storage (For File Uploads)

If you need to persist uploaded files separately from the database, configure S3 storage:

```bash
STORAGE_PROVIDER=s3
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET_NAME=qwythos-uploads
S3_REGION_NAME=us-east-1
# For S3-compatible providers (Cloudflare R2, MinIO, etc.):
S3_ENDPOINT_URL=https://your-endpoint-url
```

---

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `DATA_DIR` | Path to data directory | `/app/backend/data` |
| `DATABASE_URL` | Database connection string | `sqlite:///app/backend/data/webui.db` |
| `WEBUI_SECRET_KEY` | JWT secret (auto-generated if using volume) | Required if no volume |
| `WEBUI_SECRET_KEY_FILE` | Path to persist secret key | `/app/backend/data/.webui_secret_key` |

---

## Troubleshooting

### API Keys Disappearing After Redeploy

**Symptom:** OpenRouter/OpenAI API keys work initially but disappear after redeployment.

**Cause:** No persistent volume configured. The SQLite database is recreated empty on each deployment.

**Fix:** Add a volume at `/app/backend/data` in Railway dashboard.

### "Permission denied" Errors on Data Directory

**Symptom:** Logs show `[Errno 13] Permission denied` for `/app/backend/data`.

**Cause:** Volume mounted with incorrect permissions.

**Fix:** The Dockerfile includes permission hardening for OpenShift-style arbitrary UIDs. If issues persist, ensure the volume is writable by the container user.

### Health Check Failing

**Symptom:** Service marked unhealthy, restarts frequently.

**Cause:** Startup takes longer than health check timeout.

**Fix:** Increase `healthcheckTimeout` in railway.json (currently 100 seconds).

---

## Verification

After configuring persistent storage:

1. **Add an API key** in Settings → Connections
2. **Trigger a redeployment** (push a commit or manually redeploy)
3. **Verify the API key persists** after the service restarts

If the key persists, your volume is correctly configured.

---

## Comparison: docker-compose vs Railway

| Feature | docker-compose | Railway |
|---------|---------------|---------|
| Volume config | `volumes:` in YAML | Dashboard → Settings → Volumes |
| Default persistence | Named volume `qwythos` | **None (ephemeral)** |
| Database | SQLite in volume | SQLite (needs volume) or PostgreSQL |
| Secret key | Auto-generated in volume | Auto-generated (needs volume) |

The docker-compose.yaml correctly mounts the volume:

```yaml
services:
  qwythos:
    volumes:
      - qwythos:/app/backend/data
```

**Railway requires manual volume configuration** to achieve the same persistence.

---

## Related Documentation

- [Architecture](ARCHITECTURE.md) - System architecture overview
- [Codebase Map](CODEBASE_MAP.md) - File organization reference
- [Security](SECURITY.md) - Security considerations