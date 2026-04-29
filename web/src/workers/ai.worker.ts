/// <reference lib="webworker" />
/** Web Worker: runs the engine search off the main thread. */
import { AI, Board, type Bitboards, type Color, type Move } from "../engine";

interface BBSerialized {
  w: Record<string, string>;
  b: Record<string, string>;
}

interface RequestMsg {
  id: number;
  rows: number;
  cols: number;
  bb: BBSerialized;
  turn: Color;
  depth: number;
  pseudoLegal?: boolean;
}

interface ResponseMsg {
  id: number;
  move: { from: [number, number]; to: [number, number]; promotion: string | null } | null;
}

function deserializeBB(s: BBSerialized): Bitboards {
  const make = (g: Record<string, string>) => ({
    P: BigInt(g.P!),
    N: BigInt(g.N!),
    B: BigInt(g.B!),
    R: BigInt(g.R!),
    Q: BigInt(g.Q!),
    K: BigInt(g.K!),
  });
  return { w: make(s.w) as any, b: make(s.b) as any };
}

self.addEventListener("message", (e: MessageEvent<RequestMsg>) => {
  const { id, rows, cols, bb, turn, depth, pseudoLegal } = e.data;
  const board = new Board(rows, cols);
  board.bb = deserializeBB(bb);
  const ai = new AI(depth);
  const mv = ai.bestMove(board, turn, pseudoLegal === true);
  const out: ResponseMsg = {
    id,
    move: mv
      ? {
          from: [mv.from[0], mv.from[1]],
          to: [mv.to[0], mv.to[1]],
          promotion: mv.promotion ?? null,
        }
      : null,
  };
  (self as unknown as Worker).postMessage(out);
});

export type { RequestMsg, ResponseMsg };
