# Micro-Mate Web (TS / Konva / PWA)

A TypeScript port of the Python `micro-mate` chess engine + UI, rendered with
[Konva.js](https://konvajs.org/) and shipped as an installable PWA.

## Quick start

```bash
cd web
npm install
npm run dev          # http://localhost:5173
npm test             # engine tests against Python fixtures
npm run build        # production build (also runs sync-assets + gen-icons)
npm run preview      # preview the production build
```

## What's here

- `src/engine/` — pure-TS chess engine port of `src/micromate/engine.py`. Uses
  `bigint` bitboards (a 16×16 board needs 256 bits). The unsafe `makeUnsafe` /
  `undoUnsafe(move, captured)` pair is preserved verbatim — the AI search
  depends on it.
- `src/render/` — Konva renderer. Four layers (board / highlight / piece /
  overlay). All pixel↔square arithmetic goes through `geometry.ts`.
- `src/controller/` — input state machine (click + drag + keyboard) and the
  AI driver. The AI search itself runs in `src/workers/ai.worker.ts` so the
  UI thread stays responsive.
- `src/ui/` — HTML overlay modals and the topbar. Modals use `await new
  Promise(...)` to mimic the pygame nested-event-loop blocking feel.
- `src/pgn/` — `chess.js` bridge, **8×8 only**. Mirrors `src/micromate/pgn.py`.
- `src/persistence/save.ts` — `localStorage` autosave (debounced).
- `src/pwa/register.ts` — service worker registration via `vite-plugin-pwa`.

## Tests

The test suite verifies the TS engine against a JSON fixture dumped from the
Python engine (`../tools/dump_engine_fixtures.py`):

- Starting bitboards per board size (3×3, 4×4, 6×6, 8×8, 10×10, 16×16).
- `legal_moves` iteration order at startpos for each size — locks the move
  ordering so AI tie-breaking matches Python exactly.
- `makeUnsafe`/`undoUnsafe` round-trip restores state for every legal move.
- Perft counts at small depths.
- AI traces (depth 2, 6 plies) match Python move-for-move.
- `Game.toState`/`fromState` JSON round-trip.

If the Python engine changes, re-run:

```bash
cd ..
uv run python tools/dump_engine_fixtures.py
```

## Asset pipeline

The 12 SVG pieces live in the Python project at
`../src/micromate/assets/svg/`. `npm run sync-assets` copies them into
`public/pieces/` (run automatically before `build`). Icons are generated
from `w_k.svg` via `npm run gen-icons` (also run before `build`).

## Notes

- Coordinates are `(row, col)` with `(0, 0)` at the top-left, matching the
  Python engine. Do not flip to `(file, rank)` — it would diverge from the
  PGN bridge.
- Engine semantics live in two places now (Python and TS). When changing
  either, update both and re-dump fixtures.
