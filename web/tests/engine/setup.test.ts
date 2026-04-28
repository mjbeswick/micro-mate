import { describe, expect, it } from "vitest";
import { Board, KINDS } from "../../src/engine";
import fixtures from "../fixtures/engine.json";

const SIZES: [number, number][] = [
  [3, 3],
  [4, 4],
  [6, 6],
  [8, 8],
  [10, 10],
  [16, 16],
];

describe("starting positions match Python", () => {
  for (const [rows, cols] of SIZES) {
    it(`${rows}x${cols}`, () => {
      const b = new Board(rows, cols);
      const expected = (fixtures.starting_positions as Record<string, Record<"w" | "b", Record<string, string>>>)[
        `${rows}x${cols}`
      ]!;
      for (const color of ["w", "b"] as const) {
        for (const k of KINDS) {
          expect(b.bb[color][k].toString()).toBe(expected[color][k]);
        }
      }
    });
  }
});
