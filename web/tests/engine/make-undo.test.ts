import { describe, expect, it } from "vitest";
import { Board, KINDS, type Color } from "../../src/engine";

const SIZES: [number, number][] = [[4, 4], [6, 6], [8, 8], [10, 10]];

function bbHash(board: Board): string {
  const parts: string[] = [];
  for (const c of ["w", "b"] as const) {
    for (const k of KINDS) parts.push(`${c}${k}:${board.bb[c][k].toString()}`);
  }
  return parts.join("|");
}

describe("makeUnsafe / undoUnsafe round-trip restores state exactly", () => {
  for (const [rows, cols] of SIZES) {
    it(`${rows}x${cols} startpos, all legal moves for both colours`, () => {
      const b = new Board(rows, cols);
      for (const color of ["w", "b"] as Color[]) {
        const before = bbHash(b);
        for (const m of b.legalMoves(color)) {
          const cap = b.makeUnsafe(m);
          b.undoUnsafe(m, cap);
          expect(bbHash(b)).toBe(before);
        }
      }
    });
  }

  it("two-ply round-trip on 8x8 (sample)", () => {
    const b = new Board(8, 8);
    const before = bbHash(b);
    const w1 = b.legalMoves("w");
    for (const m1 of w1.slice(0, 5)) {
      const c1 = b.makeUnsafe(m1);
      const after1 = bbHash(b);
      const b2 = b.legalMoves("b");
      for (const m2 of b2.slice(0, 5)) {
        const c2 = b.makeUnsafe(m2);
        b.undoUnsafe(m2, c2);
        expect(bbHash(b)).toBe(after1);
      }
      b.undoUnsafe(m1, c1);
      expect(bbHash(b)).toBe(before);
    }
  });
});
