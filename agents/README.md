# agents/ — shared workspace for frontier agents

This folder is the running knowledge base every AI agent working on this repo
should read **before touching code**, and update **after** finishing work.

## Protocol

1. **Read first:** `REPO_MAP.md` for the lay of the land, then the latest entry
   in `LOG.md` to see what other agents changed recently.
2. **Work:** keep diffs minimal and consistent with the conventions noted in
   `REPO_MAP.md`.
3. **Log:** append a dated entry to `LOG.md` — what you changed, why, what you
   verified, and anything you left broken or uncertain.
4. **Update the map:** if your change moves/renames/adds a module, a route, a
   router, or a build step, update `REPO_MAP.md` in the same change. Stale maps
   are worse than no maps.

## Files

- `REPO_MAP.md` — architecture, layout, entry points, conventions, known traps.
- `LOG.md` — reverse-chronological agent activity log.

Deeper (human-written) docs live in `../docs/` — notably `ARCHITECTURE.md`,
`CODEBASE_MAP.md`, `PUBLISHING_GUIDE.md`, and `SECURITY.md`. The file you're
reading tracks what agents *did*; those docs describe what the fork *is*.
