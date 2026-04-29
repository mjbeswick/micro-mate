/** PGN bridge — supports any board size via a custom `[BoardSize "RxC"]`
 *  header. 8×8 games go through chess.js for standard SAN. Other sizes use
 *  a hand-rolled long-algebraic move list (e.g. `e2-e4`), since chess.js only
 *  models 8×8 boards. Mirrors src/micromate/pgn.py.
 */
import { Chess, type Move as ChessJSMove } from "chess.js";
import { Game, type Kind, type Move } from "../engine";

const VARIANT_TAG = "Micro-Mate";
const HEADER_RE = /\[(\w+)\s+"([^"]*)"\]/;
// File + rank + '-' + file + rank, optional =Q/R/B/N. Multi-digit ranks for
// boards with >9 rows.
const MOVE_TOKEN_RE = /[a-z]\d+-[a-z]\d+(?:=[QRBN])?/gi;

/** Retained for API compatibility — PGN now supports every size. */
export function isPGNCompatible(_game: Game): boolean {
  return true;
}

// --- 8x8 helpers (chess.js bridge) ---

function chessJsToOur(m: ChessJSMove): Move {
  return {
    from: squareToRC8x8(m.from),
    to: squareToRC8x8(m.to),
    promotion: m.promotion ? (m.promotion.toUpperCase() as Kind) : null,
  };
}

function ourToChessJS(m: Move): { from: string; to: string; promotion?: string } {
  return {
    from: rcToSquare8x8(m.from[0], m.from[1]),
    to: rcToSquare8x8(m.to[0], m.to[1]),
    promotion: m.promotion ? m.promotion.toLowerCase() : undefined,
  };
}

function rcToSquare8x8(r: number, c: number): string {
  return `${String.fromCharCode("a".charCodeAt(0) + c)}${8 - r}`;
}
function squareToRC8x8(s: string): [number, number] {
  return [8 - Number(s.slice(1)), s.charCodeAt(0) - "a".charCodeAt(0)];
}

// --- Long-algebraic helpers (any size) ---

function squareToAlg(r: number, c: number, rows: number): string {
  return `${String.fromCharCode("a".charCodeAt(0) + c)}${rows - r}`;
}

function algToSquare(text: string, rows: number): [number, number] {
  const fileCh = text[0]!.toLowerCase();
  const rank = Number(text.slice(1));
  return [rows - rank, fileCh.charCodeAt(0) - "a".charCodeAt(0)];
}

function moveToLongAlg(m: Move, rows: number): string {
  const f = squareToAlg(m.from[0], m.from[1], rows);
  const t = squareToAlg(m.to[0], m.to[1], rows);
  const promo = m.promotion ? `=${m.promotion.toUpperCase()}` : "";
  return `${f}-${t}${promo}`;
}

function longAlgToMove(token: string, rows: number): Move {
  let body = token;
  let promo: Kind | null = null;
  if (body.includes("=")) {
    const [head, promoPart] = body.split("=", 2);
    body = head!;
    const ch = promoPart?.trim().toUpperCase().slice(0, 1) ?? "";
    promo = ch ? (ch as Kind) : null;
  }
  const parts = body.split("-");
  if (parts.length !== 2) throw new Error(`Bad move token: ${token}`);
  return { from: algToSquare(parts[0]!, rows), to: algToSquare(parts[1]!, rows), promotion: promo };
}

// --- Header parsing ---

function readHeaders(text: string): Record<string, string> {
  const headers: Record<string, string> = {};
  for (const line of text.split(/\r?\n/)) {
    const s = line.trim();
    if (!s.startsWith("[")) {
      if (s === "") {
        if (Object.keys(headers).length > 0) break;
        continue;
      }
      break;
    }
    const m = HEADER_RE.exec(s);
    if (m) headers[m[1]!] = m[2]!;
  }
  return headers;
}

function parseBoardSize(headers: Record<string, string>): [number, number] {
  const spec = headers.BoardSize ?? "8x8";
  const m = /^(\d+)x(\d+)$/i.exec(spec);
  if (!m) return [8, 8];
  return [Number(m[1]), Number(m[2])];
}

// --- Public API ---

export function exportPGN(game: Game, event = "Micro-Mate"): string {
  const { rows, cols } = game.board;
  if (rows === 8 && cols === 8) return exportPGN8x8(game, event);
  return exportPGNCustom(game, event, rows, cols);
}

function exportPGN8x8(game: Game, event: string): string {
  const c = new Chess();
  for (const m of game.moveHistory) {
    const sq = ourToChessJS(m);
    c.move({ from: sq.from, to: sq.to, promotion: sq.promotion ?? undefined });
  }
  // chess.js .pgn() output without our extra headers — splice them in.
  c.header("Event", event);
  c.header("Site", "Micro-Mate");
  c.header("BoardSize", "8x8");
  return c.pgn();
}

function exportPGNCustom(game: Game, event: string, rows: number, cols: number): string {
  const headers = [
    `[Event "${event}"]`,
    `[Site "Micro-Mate"]`,
    `[Variant "${VARIANT_TAG}"]`,
    `[BoardSize "${rows}x${cols}"]`,
    `[Result "*"]`,
  ];
  const tokens: string[] = [];
  game.moveHistory.forEach((m, i) => {
    if (i % 2 === 0) tokens.push(`${i / 2 + 1}.`);
    tokens.push(moveToLongAlg(m, rows));
  });
  const body = tokens.length ? [...tokens, "*"].join(" ") : "*";
  return `${headers.join("\n")}\n\n${body}\n`;
}

export interface ImportResult {
  game: Game;
  /** Index of the first source move that couldn't be replayed (castling/EP on 8x8). */
  truncatedAt: number | null;
}

export function importPGN(text: string, aiDepth = 3): ImportResult {
  const headers = readHeaders(text);
  const [rows, cols] = parseBoardSize(headers);
  if (rows === 8 && cols === 8) return importPGN8x8(text, aiDepth);
  return importPGNCustom(text, rows, cols, aiDepth);
}

function importPGN8x8(text: string, aiDepth: number): ImportResult {
  const game = new Game(8, 8, aiDepth);
  const c = new Chess();
  try {
    c.loadPgn(text, { strict: false } as any);
  } catch {
    return { game, truncatedAt: 0 };
  }
  const history = c.history({ verbose: true }) as ChessJSMove[];
  let truncatedAt: number | null = null;
  for (let i = 0; i < history.length; i++) {
    const m = history[i]!;
    if (m.flags.includes("k") || m.flags.includes("q") || m.flags.includes("e")) {
      truncatedAt = i;
      break;
    }
    if (!game.makeMove(chessJsToOur(m))) {
      truncatedAt = i;
      break;
    }
  }
  return { game, truncatedAt };
}

function importPGNCustom(text: string, rows: number, cols: number, aiDepth: number): ImportResult {
  // Drop comments and variations, then collect move tokens.
  let body = text.replace(/\{[^}]*\}/g, " ").replace(/\([^)]*\)/g, " ");
  // Strip header lines so move-shaped strings inside tag values can't leak.
  body = body
    .split(/\r?\n/)
    .filter((line) => !line.trim().startsWith("["))
    .join("\n");
  const game = new Game(rows, cols, aiDepth);
  let truncatedAt: number | null = null;
  const tokens = body.match(MOVE_TOKEN_RE) ?? [];
  for (let i = 0; i < tokens.length; i++) {
    let mv: Move;
    try {
      mv = longAlgToMove(tokens[i]!, rows);
    } catch {
      truncatedAt = i;
      break;
    }
    if (!game.makeMove(mv)) {
      truncatedAt = i;
      break;
    }
  }
  return { game, truncatedAt };
}
