# Publish Qwythos to a Private Git Repository

This repository is prepared as a source-only baseline. The local Git history should already contain
the verified initial commit before these instructions are used. No remote is created by the setup
process.

## 1. Create an empty private repository

In GitHub, GitLab, or another Git host:

1. Create a new repository for Qwythos.
2. Set its visibility to **Private**.
3. Do not initialize it with a README, license, or `.gitignore`; those files already exist here.
4. Copy the repository's HTTPS or SSH URL.

Before distribution or deployment, read [`../FORK_NOTICE.md`](../FORK_NOTICE.md) and confirm that the
intended Qwythos branding is permitted by the inherited Open WebUI License for your use case.

## 2. Verify the local baseline

Run these commands from the repository root:

```powershell
git status --short --branch
git log -1 --oneline
git remote -v
```

The working tree should be clean and `git remote -v` should produce no output until you add the
private destination. Local runtime material is intentionally excluded, including `.env` files,
`backend/data`, `.venv`, `node_modules`, build output, logs, `.claude`, and `work`.

## 3. Add the private remote and push

Replace the example URL with the URL copied from your private repository:

```powershell
git branch -M main
git remote add origin https://github.com/YOUR_ACCOUNT/YOUR_PRIVATE_REPOSITORY.git
git remote -v
git push -u origin main
```

SSH is equally valid:

```powershell
git remote add origin git@github.com:YOUR_ACCOUNT/YOUR_PRIVATE_REPOSITORY.git
git push -u origin main
```

If `origin` already exists but points to the wrong destination, inspect it first and then use:

```powershell
git remote set-url origin YOUR_PRIVATE_REPOSITORY_URL
```

## 4. Private-repository settings

After the first push:

- Add only the collaborators or teams that should have access.
- Enable secret scanning and dependency alerts if the host supports them for private repositories.
- Protect `main` once a review workflow is in place.
- Store deployment credentials in repository or environment secrets, never in tracked `.env` files.
- Review Actions permissions before enabling workflows inherited from the codebase.

## 5. Build and launch from a fresh clone

The generated `build/` directory is deliberately not committed. On a new machine, install the pinned
Node dependencies and create the frontend before launching the desktop application:

```powershell
npm ci
npm run build
powershell -ExecutionPolicy Bypass -File '.\desktop\Create Desktop Shortcut.ps1'
```

The shortcut bootstrapper creates the Python virtual environment on first launch. Python 3.12 is the
verified Windows runtime for this workspace.

## 6. Pre-push check for later changes

```powershell
git status --short
git diff --check
git diff --stat origin/main...HEAD
git push
```

Review the diff before every push, especially configuration, logs, database files, generated assets,
and anything containing credentials.

## Repository documentation

- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — system boundaries and runtime flows
- [`CODEBASE_MAP.md`](./CODEBASE_MAP.md) — source navigation and ownership map
- [`../AUTHOR.md`](../AUTHOR.md) — maintainer note and verified contribution scope
- [`../FORK_NOTICE.md`](../FORK_NOTICE.md) — upstream provenance and branding obligations
- [`SECURITY.md`](./SECURITY.md) — security policy inherited with the codebase
