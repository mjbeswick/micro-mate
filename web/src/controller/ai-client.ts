/** Main-thread client for the AI worker. */
import type { Game, Move } from "../engine";
import { KINDS } from "../engine";
import AIWorker from "../workers/ai.worker?worker";
import type { RequestMsg, ResponseMsg } from "../workers/ai.worker";

let nextId = 1;
let worker: Worker | null = null;

function getWorker(): Worker {
  if (!worker) worker = new AIWorker();
  return worker;
}

export function computeAIMove(game: Game, pseudoLegal = false): Promise<Move | null> {
  const id = nextId++;
  const w = getWorker();
  const bb = {
    w: serializeColor(game.board.bb.w),
    b: serializeColor(game.board.bb.b),
  };
  const req: RequestMsg = {
    id,
    rows: game.board.rows,
    cols: game.board.cols,
    bb,
    turn: game.turn,
    depth: game.aiDepth,
    pseudoLegal,
  };
  return new Promise((resolve) => {
    const onMsg = (e: MessageEvent<ResponseMsg>) => {
      if (e.data.id !== id) return;
      w.removeEventListener("message", onMsg);
      const m = e.data.move;
      resolve(
        m
          ? { from: m.from, to: m.to, promotion: (m.promotion as Move["promotion"]) ?? null }
          : null,
      );
    };
    w.addEventListener("message", onMsg);
    w.postMessage(req);
  });
}

function serializeColor(c: Record<string, bigint>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const k of KINDS) out[k] = c[k]!.toString();
  return out;
}
