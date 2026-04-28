import { describe, expect, it } from "vitest";
import { Board } from "../../src/engine";
import fixtures from "../fixtures/engine.json";

const ORDERS = fixtures.legal_moves_startpos_white as unknown as Record<
  string,
  { from: [number, number]; to: [number, number]; promotion: string | null }[]
>;

describe("legal_moves iteration order matches Python (startpos, white)", () => {
  for (const [size, expected] of Object.entries(ORDERS)) {
    const [rs, cs] = size.split("x").map(Number);
    it(size, () => {
      const b = new Board(rs!, cs!);
      const got = b.legalMoves("w").map((m) => ({
        from: [m.from[0], m.from[1]],
        to: [m.to[0], m.to[1]],
        promotion: m.promotion ?? null,
      }));
      expect(got).toEqual(expected);
    });
  }
});
