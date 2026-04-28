import { describe, expect, it } from "vitest";
import { Game } from "../../src/engine";

describe("Game.toState / fromState round-trip", () => {
  it("preserves turn, history, and bitboards across save/load", () => {
    const g = new Game(8, 8, 2);
    g.makeMove(g.getLegalMoves()[0]!); // any legal first move
    g.makeMove(g.getLegalMoves()[0]!);
    const state = g.toState();
    const json = JSON.stringify(state);
    const restored = Game.fromState(JSON.parse(json));
    expect(restored.turn).toBe(g.turn);
    expect(restored.positionIndex).toBe(g.positionIndex);
    expect(restored.positionCount).toBe(g.positionCount);
    expect(restored.board.bb.w.K.toString()).toBe(g.board.bb.w.K.toString());
    expect(restored.board.bb.b.P.toString()).toBe(g.board.bb.b.P.toString());
  });
});
