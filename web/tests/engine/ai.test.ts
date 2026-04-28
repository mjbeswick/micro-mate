import { describe, expect, it } from "vitest";
import { Game } from "../../src/engine";
import fixtures from "../fixtures/engine.json";

const TRACES = fixtures.ai_traces_depth2 as unknown as Record<
  string,
  { from: [number, number]; to: [number, number]; promotion: string | null; turn_before: "w" | "b" }[]
>;

describe("AI move trace at depth 2 matches Python", () => {
  for (const [size, expected] of Object.entries(TRACES)) {
    const [rs, cs] = size.split("x").map(Number);
    it(size, () => {
      const g = new Game(rs!, cs!, 2);
      for (const ex of expected) {
        expect(g.turn).toBe(ex.turn_before);
        const mv = g.getAIMove();
        expect(mv).not.toBeNull();
        expect([mv!.from[0], mv!.from[1]]).toEqual(ex.from);
        expect([mv!.to[0], mv!.to[1]]).toEqual(ex.to);
        expect(mv!.promotion ?? null).toBe(ex.promotion);
        g.makeMove(mv!);
      }
    });
  }
});
