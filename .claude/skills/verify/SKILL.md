---
name: verify
description: Build, run, and drive this app end-to-end to verify changes at runtime.
---

# Verifying changes in this repo

## Launch

Kill stale servers, then start both (must run OUTSIDE the command sandbox —
sandboxed runs fail with EPERM binding ports 3000/8001):

```bash
lsof -ti:3000,8001 | xargs kill -9 2>/dev/null || true
cd server && uv run python main.py       # background; FastAPI on :8001
cd client && npm run dev                 # background; Vite on :3000
```

Ready check: `curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/docs`
and `http://localhost:3000` both return 200 within ~5s. The `/start` and
`/stop` project skills wrap the same commands.

## Drive

- API surface: curl `http://localhost:8001/api/...` directly. FastAPI/Pydantic
  gives clean 422s for bad query params; endpoint handlers raise 400 with
  `detail` for domain errors.
- UI surface: Playwright MCP tools against `http://localhost:3000` (per
  CLAUDE.md, use `mcp__playwright__*`, not claude-in-chrome). Full-page
  snapshots of Orders (250 rows) exceed the tool result limit — the result is
  saved to a file; grep it for headings/rows instead of re-fetching.

## Gotchas

- All data is in-memory (loaded from `server/data/*.json` at import). POSTs
  (e.g. restock orders) mutate only process memory — restart the backend to
  reset; nothing is written to disk, so git stays clean.
- Every page load logs a pre-existing 404 for `GET /api/tasks` (client calls
  it; backend has no such route) — not caused by your change.
- Month/quarter filters only cover 2025; anything dated by `datetime.now()`
  (2026+) is invisible under any Time Period filter.
