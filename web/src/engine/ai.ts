/** Minimax with alpha-beta pruning. Eval is from white's POV (positive = white). */
import { Board } from "./board";
import type { Color, Kind, Move } from "./types";
import { KINDS } from "./types";
import { popcount } from "./bitboard";

const MAT: Record<Kind, number> = { P: 100, N: 300, B: 300, R: 500, Q: 900, K: 0 };

export class AI {
  depth: number;
  constructor(depth = 3) {
    this.depth = depth;
  }

  bestMove(board: Board, color: Color, pseudoLegal = false): Move | null {
    const moves = pseudoLegal ? board.pseudoLegalMoves(color) : board.legalMoves(color);
    if (moves.length === 0) return null;
    // Stable sort: captures first. Mirrors Python's `sort(..., reverse=True)`
    // on a captures-only key.
    const ordered = stableSortCapturesFirst(board, moves);

    let best = ordered[0]!;
    if (color === "w") {
      let bestScore = -Infinity;
      for (const move of ordered) {
        const captured = board.makeUnsafe(move);
        const score = this.minimax(board, this.depth - 1, -Infinity, Infinity, false, pseudoLegal);
        board.undoUnsafe(move, captured);
        if (score > bestScore) {
          bestScore = score;
          best = move;
        }
      }
    } else {
      let bestScore = Infinity;
      for (const move of ordered) {
        const captured = board.makeUnsafe(move);
        const score = this.minimax(board, this.depth - 1, -Infinity, Infinity, true, pseudoLegal);
        board.undoUnsafe(move, captured);
        if (score < bestScore) {
          bestScore = score;
          best = move;
        }
      }
    }
    return best;
  }

  private minimax(
    board: Board,
    depth: number,
    alpha: number,
    beta: number,
    isMax: boolean,
    pseudoLegal: boolean,
  ): number {
    if (pseudoLegal) {
      if (board.bb.b.K === 0n) return Infinity;
      if (board.bb.w.K === 0n) return -Infinity;
    }
    if (depth === 0) return evaluate(board, pseudoLegal);
    const color: Color = isMax ? "w" : "b";
    const moves = pseudoLegal ? board.pseudoLegalMoves(color) : board.legalMoves(color);
    const ordered = stableSortCapturesFirst(board, moves);
    if (ordered.length === 0) {
      if (pseudoLegal) return 0;
      return board.isInCheck(color) ? (isMax ? -Infinity : Infinity) : 0;
    }

    if (isMax) {
      let maxScore = -Infinity;
      let a = alpha;
      for (const move of ordered) {
        const captured = board.makeUnsafe(move);
        const score = this.minimax(board, depth - 1, a, beta, false, pseudoLegal);
        board.undoUnsafe(move, captured);
        if (score > maxScore) maxScore = score;
        if (score > a) a = score;
        if (beta <= a) break;
      }
      return maxScore;
    } else {
      let minScore = Infinity;
      let b = beta;
      for (const move of ordered) {
        const captured = board.makeUnsafe(move);
        const score = this.minimax(board, depth - 1, alpha, b, true, pseudoLegal);
        board.undoUnsafe(move, captured);
        if (score < minScore) minScore = score;
        if (score < b) b = score;
        if (b <= alpha) break;
      }
      return minScore;
    }
  }
}

export function evaluate(board: Board, pseudoLegal = false): number {
  const kingVal = pseudoLegal ? 100_000 : 0;
  const vals = { ...MAT, K: kingVal };
  let score = 0;
  for (const k of KINDS) {
    score += vals[k] * popcount(board.bb.w[k]);
    score -= vals[k] * popcount(board.bb.b[k]);
  }
  return score;
}

/** Stable sort: captures (target square occupied) before non-captures.
 *  Python's `sort(..., reverse=True)` is stable, and bool True > False, so the
 *  effect is "captures first, otherwise original order". Replicate exactly. */
function stableSortCapturesFirst(board: Board, moves: Move[]): Move[] {
  const indexed = moves.map((m, i) => ({ m, i, cap: board.pieceAt(m.to[0], m.to[1]) !== null }));
  indexed.sort((a, b) => {
    if (a.cap !== b.cap) return a.cap ? -1 : 1;
    return a.i - b.i;
  });
  return indexed.map((x) => x.m);
}
