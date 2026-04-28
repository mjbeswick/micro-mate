/** PGN bridge — 8×8 only, mirroring src/micromate/pgn.py.
 *  Uses chess.js. Replay stops at the first move our engine can't model
 *  (castling / en passant). */
import { Chess, type Move as ChessJSMove } from "chess.js";
import { Game, type Move } from "../engine";

export function isPGNCompatible(game: Game): boolean {
  return game.board.rows === 8 && game.board.cols === 8;
}

/** Parse PGN string into a sequence of (row,col) Moves our engine can replay.
 *  Returns the moves we successfully replayed (may be a prefix). */
export function importPGN(pgn: string): { moves: Move[]; truncatedAt: number | null } {
  const c = new Chess();
  // chess.js loadPgn returns boolean in v0.x and throws in v1; handle both.
  try {
    c.loadPgn(pgn, { strict: false } as any);
  } catch {
    return { moves: [], truncatedAt: 0 };
  }
  const history: ChessJSMove[] = c.history({ verbose: true }) as ChessJSMove[];
  const moves: Move[] = [];
  let truncatedAt: number | null = null;
  for (let i = 0; i < history.length; i++) {
    const m = history[i]!;
    // Castling and en passant are not modelled — stop here.
    if (m.flags.includes("k") || m.flags.includes("q") || m.flags.includes("e")) {
      truncatedAt = i;
      break;
    }
    moves.push(chessJsToOur(m));
  }
  return { moves, truncatedAt };
}

/** Serialize the engine's move history as PGN. Requires 8×8.
 *  Returns null if any move can't be expressed in standard chess. */
export function exportPGN(game: Game): string | null {
  if (!isPGNCompatible(game)) return null;
  const c = new Chess();
  for (const m of game.moveHistory) {
    const sq = ourToChessJS(m);
    const res = c.move({ from: sq.from, to: sq.to, promotion: sq.promotion ?? undefined });
    if (!res) return null;
  }
  return c.pgn();
}

function chessJsToOur(m: ChessJSMove): Move {
  return {
    from: squareToRC(m.from),
    to: squareToRC(m.to),
    promotion: m.promotion ? (m.promotion.toUpperCase() as Move["promotion"]) : null,
  };
}

function ourToChessJS(m: Move): { from: string; to: string; promotion?: string } {
  return {
    from: rcToSquare(m.from[0], m.from[1]),
    to: rcToSquare(m.to[0], m.to[1]),
    promotion: m.promotion ? m.promotion.toLowerCase() : undefined,
  };
}

function rcToSquare(r: number, c: number): string {
  // (row, col) with row 0 at top → standard chess square
  const file = String.fromCharCode("a".charCodeAt(0) + c);
  const rank = String(8 - r);
  return `${file}${rank}`;
}

function squareToRC(s: string): [number, number] {
  const file = s.charCodeAt(0) - "a".charCodeAt(0);
  const rank = Number(s[1]);
  return [8 - rank, file];
}
