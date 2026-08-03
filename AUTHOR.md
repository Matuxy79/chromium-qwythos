# Maintainer Profile

## John Matukutire

John Matukutire maintains this Qwythos workspace and its Chromium Wyvern desktop experience.
Qwythos includes a substantial Open WebUI-derived codebase; its provenance, copyright, and license
history remain documented in [`FORK_NOTICE.md`](./FORK_NOTICE.md), [`LICENSE`](./LICENSE),
[`LICENSE_HISTORY`](./LICENSE_HISTORY), and [`LICENSE_NOTICE`](./LICENSE_NOTICE).

## Work represented in this repository

- Chromium Wyvern authentication and onboarding presentation
- A responsive, reduced-motion-aware Qwythos model-stack background for the empty chat state
- A Windows native-window launcher built with Python and pywebview
- Launcher safeguards for stale local servers, deterministic frontend build identity, and persistent
  webview storage
- Source-verified architecture and codebase navigation documentation
- Qwythos browser, PWA, application, and Windows shortcut branding

## Repository-verified technical footprint

The current tree contains the following implementation areas. These figures describe the repository;
they are not an authorship claim.

| Area             | Verified inventory                                                  |
| ---------------- | ------------------------------------------------------------------- |
| Backend API      | 31 FastAPI router modules                                           |
| Data layer       | 26 model modules and Alembic migrations                             |
| Processing layer | 46 backend utility modules                                          |
| Retrieval        | 15 vector-backend modules, 33 web-search modules, 10 loader modules |
| Frontend API     | 29 feature client directories                                       |
| Interface        | SvelteKit, TypeScript, Vite, and 63 locale directories              |
| Desktop          | Python 3.12-compatible bootstrapper and pywebview host              |

For the execution paths behind those numbers, see
[`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) and
[`docs/CODEBASE_MAP.md`](./docs/CODEBASE_MAP.md).

## Stewardship

Changes in this fork should keep upstream notices intact, avoid committing local credentials or
runtime data, and document the difference between implemented behavior and future direction. Contact
and professional-profile links can be added when the private repository has its final owner and URL.
