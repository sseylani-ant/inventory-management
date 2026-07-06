---
name: vue-audit
description: Analyze Vue component structure and suggest performance and code-reuse optimizations. Use when asked to audit, review, or optimize Vue components, find duplicated component logic, or diagnose rendering performance. Analysis-only — reports findings, does not edit code.
---

# Vue Component Audit

Analyze the Vue components in `client/src` and report ranked optimization
suggestions. This skill **only reports** — apply fixes in a separate step,
delegating any `.vue` edits to the **vue-expert** subagent per CLAUDE.md.

## Scope

If an argument names a component, view, or directory, audit only that;
otherwise audit all of `client/src/views/` and `client/src/components/`.
Read `client/src/composables/` and `client/src/App.vue` (shared styles)
either way — they are the reuse targets findings should point at.

## Analysis dimensions

Run these as parallel finder subagents (read-only: Read/Grep/Glob), one per
dimension, each returning up to 8 candidates with `file`, `line`, a one-line
issue, and a concrete cost/fix.

### 1. Rendering performance

- **Methods called in template interpolations/bindings** — uncached, re-run
  on every render. If the call is pure derivation from reactive state,
  suggest a `computed` (e.g. status counts derived once from a single pass
  instead of N template calls that each filter the whole array).
- **Repeated full-array `.filter()`/`.find()` computeds** over the same
  source — suggest one computed that partitions/indexes in a single pass.
- **`v-for` keys**: missing, or `:key="index"`/`:key="idx"` — CLAUDE.md
  requires unique keys (`sku`, `month`, `id`). Flag every occurrence.
- **Deep or unkeyed watchers** (`{ deep: true }`, watching whole arrays)
  where a narrower source or computed would do.
- **Inline object/array literals in template bindings** passed as props —
  new identity every render, defeats child memoization.
- **Large static data in `ref()`** — never mutated after load → suggest
  `shallowRef` or a plain module constant.
- **`v-if` vs `v-show`** on frequently toggled heavy subtrees.

### 2. Code reuse

- **Duplicated computeds/functions across components** — Grep for repeated
  bodies (formatting helpers, currency/locale logic, status maps). The fix
  is almost always an export from `client/src/composables/` (e.g.
  `useI18n.js` already owns locale state — symbol/format helpers belong
  there) or a shared util module.
- **Duplicated template blocks** — near-identical tables/cards/lists within
  or across components. Suggest extracting a component in
  `client/src/components/` with props/slots, or a conditional column/section
  in one copy. Quantify the overlap (lines duplicated).
- **Copy-paste with slight variation** — same markup differing by one column
  or one class; suggest the parameterized form.
- **Local re-implementations of an existing helper** defined lines away in
  the same file (e.g. a computed that could call an existing
  `getXByY(...)` function).

### 3. Component structure

- **Oversized single-file components** (script > ~200 lines or template
  > ~150 lines) mixing fetching, derivation, and presentation — suggest the
  split (composable for data flow, child components for repeated sections).
- **Views bypassing shared mechanisms** — e.g. a view that ignores the
  global `FilterBar`/filter query params every sibling view honors, or
  hand-rolls fetch state instead of the established pattern (raw data in
  refs, derived data in computeds).
- **Prop drilling** through ≥2 intermediate components → provide/inject or
  a composable.
- **Unregistered/unresolved components** referenced in templates (Vue warns
  "Failed to resolve component" at runtime) — Grep template component tags
  against imports.

## Verification pass

Findings from finders are candidates, not conclusions. Before reporting,
verify each: Read the actual file at the cited line and confirm the pattern
is really there and really costs something. Drop anything refuted. When the
dev server is running (see `/start`), spot-check runtime claims in the
browser console (Vue warnings appear on page load).

## Report

Rank by impact (user-visible perf > correctness-adjacent > maintenance).
For each finding:

- `file:line` — issue (one sentence)
- **Cost**: what it wastes or risks, concretely
- **Fix**: the specific change, naming the target (which composable, which
  new/existing component, which computed)

End with a short "quick wins" list (fixes under ~10 lines each) and note
that applying `.vue` changes must go through the vue-expert subagent.
