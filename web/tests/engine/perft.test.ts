import { describe, expect, it } from "vitest";
import { Board, type Color } from "../../src/engine";
import fixtures from "../fixtures/engine.json";

function perft(board: Board, depth: number, color: Color): number {
  if (depth === 0) return 1;
  const moves = board.legalMoves(color);
  if (depth === 1) return moves.length;
  const next: Color = color === "w" ? "b" : "w";
  let total = 0;
  for (const m of moves) {
    const cap = board.makeUnsafe(m);
    total += perft(board, depth - 1, next);
    board.undoUnsafe(m, cap);
  }
  return total;
}

const PERFT = fixtures.perft as Record<string, Record<string, number>>;

describe("perft counts match Python fixtures", () => {
  for (const [size, depths] of Object.entries(PERFT)) {
    const [rs, cs] = size.split("x").map(Number);
    for (const [dkey, expected] of Object.entries(depths)) {
      const depth = Number(dkey.replace("depth", ""));
      it(`${size} depth ${depth} = ${expected}`, () => {
        const b = new Board(rs!, cs!);
        expect(perft(b, depth, "w")).toBe(expected);
      });
    }
  }
});
