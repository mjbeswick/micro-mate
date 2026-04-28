/**
 * Board: bitboard backend for an arbitrary rectangular chess variant.
 *
 * Coordinates are (row, col) with (0, 0) at the top-left (rank 8 / file a in
 * standard chess). Bitboards are bigint because a 16x16 board needs 256 bits.
 *
 * INVARIANT: makeUnsafe / undoUnsafe are a strict pair. makeUnsafe returns the
 * captured Piece (or null). undoUnsafe REQUIRES that piece to restore state.
 * AI search depends on this round-trip — do NOT drop the captured argument.
 *
 * No castling, no en passant. Pawn promotion auto-queens.
 */
import type { Bitboards, Color, Kind, Move, Piece } from "./types";
import { KINDS } from "./types";
import {
  bit,
  bitLength,
  cloneBB,
  emptyBB,
  occAll,
  occColor,
  popcount,
} from "./bitboard";

const MATERIAL: Record<Kind, number> = {
  P: 100,
  N: 300,
  B: 300,
  R: 500,
  Q: 900,
  K: 0,
};

export class Board {
  rows: number;
  cols: number;
  bb: Bitboards;

  constructor(rows = 5, cols = 6) {
    this.rows = rows;
    this.cols = cols;
    this.bb = emptyBB();
    this.setupStartpos();
  }

  bit(r: number, c: number): bigint {
    return bit(r, c, this.cols);
  }

  pieceAt(r: number, c: number): Piece | null {
    const b = this.bit(r, c);
    for (const color of ["w", "b"] as const) {
      const cbb = this.bb[color];
      for (const kind of KINDS) {
        if (cbb[kind] & b) return { kind, color };
      }
    }
    return null;
  }

  setPiece(r: number, c: number, piece: Piece): void {
    this.bb[piece.color][piece.kind] |= this.bit(r, c);
  }

  evaluate(pseudoLegal = false): number {
    const kingVal = pseudoLegal ? 100_000 : 0;
    const vals = { ...MATERIAL, K: kingVal };
    let score = 0;
    for (const k of KINDS) {
      score += vals[k] * popcount(this.bb.w[k]);
      score -= vals[k] * popcount(this.bb.b[k]);
    }
    return score;
  }

  setupStartpos(): void {
    this.bb = emptyBB();
    if (this.rows < 2) return;

    if (this.rows === 3 && this.cols === 3) {
      for (let c = 0; c < 3; c++) {
        this.setPiece(0, c, { kind: "P", color: "b" });
        this.setPiece(2, c, { kind: "P", color: "w" });
      }
      return;
    }

    let backRank: (Kind | null)[];
    if (this.cols >= 16) {
      backRank = ["R", "N", "B", "Q", "K", "Q", "B", "N", "R", "N", "B", "Q", "Q", "B", "N", "R"];
    } else if (this.cols >= 10) {
      backRank = ["R", "N", "B", "Q", "K", "Q", "B", "N", "R", "R"];
    } else if (this.cols >= 8) {
      backRank = ["R", "N", "B", "Q", "K", "B", "N", "R"];
    } else if (this.cols >= 6) {
      backRank = ["R", "N", "B", "Q", "K", "B"];
    } else if (this.cols >= 4) {
      backRank = ["R", "K", "Q", "R"];
    } else {
      backRank = this.cols >= 2 ? ["K", "Q"] : ["K"];
    }

    const padded: (Kind | null)[] = [];
    for (let i = 0; i < this.cols; i++) padded.push(backRank[i] ?? null);
    const reversedPadded = [...padded].reverse();

    for (let c = 0; c < this.cols; c++) {
      const k = padded[c];
      if (k) this.setPiece(0, c, { kind: k, color: "b" });
    }
    for (let c = 0; c < this.cols; c++) {
      this.setPiece(1, c, { kind: "P", color: "b" });
      this.setPiece(this.rows - 2, c, { kind: "P", color: "w" });
    }
    for (let c = 0; c < this.cols; c++) {
      const k = reversedPadded[c];
      if (k) this.setPiece(this.rows - 1, c, { kind: k, color: "w" });
    }
  }

  /** Iterate set bits in a bigint, yielding (row, col). Order: low bit first
   *  — matches Python's `lsb = tmp & -tmp` loop, which is critical for AI
   *  determinism (alpha-beta tie-breaking depends on move-gen order). */
  private *iterSquares(b: bigint): Generator<[number, number]> {
    let tmp = b;
    while (tmp) {
      const lsb = tmp & -tmp;
      const sq = bitLength(lsb) - 1;
      const r = Math.floor(sq / this.cols);
      const c = sq % this.cols;
      yield [r, c];
      tmp ^= lsb;
    }
  }

  legalMoves(color: Color): Move[] {
    const moves = this.pseudoLegalMoves(color);
    return moves.filter((m) => this.isLegalMove(m, color));
  }

  pseudoLegalMoves(color: Color): Move[] {
    const moves: Move[] = [];
    for (const kind of KINDS) {
      for (const [r, c] of this.iterSquares(this.bb[color][kind])) {
        this.appendPieceMoves(moves, r, c, kind, color);
      }
    }
    return moves;
  }

  private appendPieceMoves(out: Move[], r: number, c: number, kind: Kind, color: Color): void {
    switch (kind) {
      case "P":
        this.pawnMoves(out, r, c, color);
        break;
      case "N":
        this.knightMoves(out, r, c, color);
        break;
      case "B":
        this.slidingMoves(out, r, c, color, BISHOP_DIRS);
        break;
      case "R":
        this.slidingMoves(out, r, c, color, ROOK_DIRS);
        break;
      case "Q":
        this.slidingMoves(out, r, c, color, QUEEN_DIRS);
        break;
      case "K":
        this.kingMoves(out, r, c, color);
        break;
    }
  }

  private pawnMoves(out: Move[], r: number, c: number, color: Color): void {
    const direction = color === "w" ? -1 : 1;
    const newR = r + direction;
    const promoRank = color === "w" ? 0 : this.rows - 1;
    const cols = this.cols;
    const occ = occAll(this.bb);
    const enemy: Color = color === "w" ? "b" : "w";
    const occEnemy = occColor(this.bb, enemy);

    if (newR >= 0 && newR < this.rows) {
      const promo: Kind | null = newR === promoRank ? "Q" : null;
      const destB = 1n << BigInt(newR * cols + c);
      if (!(occ & destB)) {
        out.push({ from: [r, c], to: [newR, c], promotion: promo });
        if (promo === null) {
          if ((color === "w" && r === this.rows - 2) || (color === "b" && r === 1)) {
            const twoR = newR + direction;
            if (
              twoR >= 0 &&
              twoR < this.rows &&
              !(occ & (1n << BigInt(twoR * cols + c)))
            ) {
              out.push({ from: [r, c], to: [twoR, c], promotion: null });
            }
          }
        }
      }
      for (const dc of [-1, 1]) {
        const newC = c + dc;
        if (newC >= 0 && newC < cols) {
          if (occEnemy & (1n << BigInt(newR * cols + newC))) {
            out.push({ from: [r, c], to: [newR, newC], promotion: promo });
          }
        }
      }
    }
  }

  private knightMoves(out: Move[], r: number, c: number, color: Color): void {
    const occOwn = occColor(this.bb, color);
    const cols = this.cols;
    for (const [dr, dc] of KNIGHT_DELTAS) {
      const nr = r + dr;
      const nc = c + dc;
      if (nr >= 0 && nr < this.rows && nc >= 0 && nc < cols) {
        if (!(occOwn & (1n << BigInt(nr * cols + nc)))) {
          out.push({ from: [r, c], to: [nr, nc], promotion: null });
        }
      }
    }
  }

  private slidingMoves(
    out: Move[],
    r: number,
    c: number,
    color: Color,
    deltas: readonly (readonly [number, number])[],
  ): void {
    const occOwn = occColor(this.bb, color);
    const occ = occOwn | occColor(this.bb, color === "w" ? "b" : "w");
    const cols = this.cols;
    for (const [dr, dc] of deltas) {
      let nr = r + dr;
      let nc = c + dc;
      while (nr >= 0 && nr < this.rows && nc >= 0 && nc < cols) {
        const b = 1n << BigInt(nr * cols + nc);
        if (occOwn & b) break;
        out.push({ from: [r, c], to: [nr, nc], promotion: null });
        if (occ & b) break;
        nr += dr;
        nc += dc;
      }
    }
  }

  private kingMoves(out: Move[], r: number, c: number, color: Color): void {
    const occOwn = occColor(this.bb, color);
    const cols = this.cols;
    for (let dr = -1; dr <= 1; dr++) {
      for (let dc = -1; dc <= 1; dc++) {
        if (dr === 0 && dc === 0) continue;
        const nr = r + dr;
        const nc = c + dc;
        if (nr >= 0 && nr < this.rows && nc >= 0 && nc < cols) {
          if (!(occOwn & (1n << BigInt(nr * cols + nc)))) {
            out.push({ from: [r, c], to: [nr, nc], promotion: null });
          }
        }
      }
    }
  }

  // --- Legality / check detection ---

  private isLegalMove(move: Move, color: Color): boolean {
    const captured = this.makeUnsafe(move);
    const legal = !this.isInCheck(color);
    this.undoUnsafe(move, captured);
    return legal;
  }

  isInCheck(color: Color): boolean {
    const kingBB = this.bb[color].K;
    if (!kingBB) return false;
    const sq = bitLength(kingBB) - 1;
    const kingR = Math.floor(sq / this.cols);
    const kingC = sq % this.cols;
    const enemy: Color = color === "w" ? "b" : "w";
    for (const kind of KINDS) {
      for (const [er, ec] of this.iterSquares(this.bb[enemy][kind])) {
        if (this.canPieceAttack(er, ec, kingR, kingC, kind, enemy)) return true;
      }
    }
    return false;
  }

  private rayAttacks(
    r: number,
    c: number,
    dr: number,
    dc: number,
    targetR: number,
    targetC: number,
  ): boolean {
    const occ = occAll(this.bb);
    const cols = this.cols;
    let nr = r + dr;
    let nc = c + dc;
    while (nr >= 0 && nr < this.rows && nc >= 0 && nc < cols) {
      if (nr === targetR && nc === targetC) return true;
      if (occ & (1n << BigInt(nr * cols + nc))) return false;
      nr += dr;
      nc += dc;
    }
    return false;
  }

  private canPieceAttack(
    r: number,
    c: number,
    targetR: number,
    targetC: number,
    kind: Kind,
    color: Color,
  ): boolean {
    const dr = targetR - r;
    const dc = targetC - c;

    if (kind === "P") {
      const direction = color === "w" ? -1 : 1;
      return dr === direction && Math.abs(dc) === 1;
    }
    if (kind === "N") {
      const ar = Math.abs(dr);
      const ac = Math.abs(dc);
      return (ar === 2 && ac === 1) || (ar === 1 && ac === 2);
    }
    if (kind === "K") {
      return Math.max(Math.abs(dr), Math.abs(dc)) === 1;
    }
    if ((kind === "B" || kind === "Q") && dr !== 0 && Math.abs(dr) === Math.abs(dc)) {
      if (this.rayAttacks(r, c, dr > 0 ? 1 : -1, dc > 0 ? 1 : -1, targetR, targetC)) return true;
    }
    if ((kind === "R" || kind === "Q") && (dr === 0 || dc === 0)) {
      const stepR = dr === 0 ? 0 : dr > 0 ? 1 : -1;
      const stepC = dc === 0 ? 0 : dc > 0 ? 1 : -1;
      if (this.rayAttacks(r, c, stepR, stepC, targetR, targetC)) return true;
    }
    return false;
  }

  // --- Make / undo (for AI search and legality checking) ---

  makeUnsafe(move: Move): Piece | null {
    const [rF, cF] = move.from;
    const [rT, cT] = move.to;
    const cols = this.cols;
    const fb = 1n << BigInt(rF * cols + cF);
    const tb = 1n << BigInt(rT * cols + cT);
    const bbW = this.bb.w;
    const bbB = this.bb.b;

    const occW = bbW.P | bbW.N | bbW.B | bbW.R | bbW.Q | bbW.K;
    const movingBB = occW & fb ? bbW : bbB;
    let movingKind!: Kind;
    for (const k of KINDS) {
      if (movingBB[k] & fb) {
        movingKind = k;
        break;
      }
    }

    let captured: Piece | null = null;
    const occAllBits = occW | (bbB.P | bbB.N | bbB.B | bbB.R | bbB.Q | bbB.K);
    if (occAllBits & tb) {
      const capBB = occW & tb ? bbW : bbB;
      const capColor: Color = capBB === bbW ? "w" : "b";
      let capKind!: Kind;
      for (const k of KINDS) {
        if (capBB[k] & tb) {
          capKind = k;
          break;
        }
      }
      captured = { kind: capKind, color: capColor };
      capBB[capKind] ^= tb;
    }

    movingBB[movingKind] ^= fb;
    const placeKind: Kind =
      movingKind === "P" && move.promotion ? move.promotion : movingKind;
    movingBB[placeKind] |= tb;

    return captured;
  }

  undoUnsafe(move: Move, captured: Piece | null): void {
    const [rF, cF] = move.from;
    const [rT, cT] = move.to;
    const cols = this.cols;
    const fb = 1n << BigInt(rF * cols + cF);
    const tb = 1n << BigInt(rT * cols + cT);
    const bbW = this.bb.w;
    const bbB = this.bb.b;

    const occW = bbW.P | bbW.N | bbW.B | bbW.R | bbW.Q | bbW.K;
    const destBB = occW & tb ? bbW : bbB;
    let destKind!: Kind;
    for (const k of KINDS) {
      if (destBB[k] & tb) {
        destKind = k;
        break;
      }
    }

    destBB[destKind] ^= tb;
    const restoreKind: Kind = move.promotion ? "P" : destKind;
    destBB[restoreKind] |= fb;

    if (captured) {
      this.bb[captured.color][captured.kind] |= tb;
    }
  }

  cloneBB(): Bitboards {
    return cloneBB(this.bb);
  }
}

const KNIGHT_DELTAS: readonly (readonly [number, number])[] = [
  [-2, -1], [-2, 1], [-1, -2], [-1, 2], [1, -2], [1, 2], [2, -1], [2, 1],
];
const BISHOP_DIRS: readonly (readonly [number, number])[] = [[-1, -1], [-1, 1], [1, -1], [1, 1]];
const ROOK_DIRS: readonly (readonly [number, number])[] = [[-1, 0], [1, 0], [0, -1], [0, 1]];
const QUEEN_DIRS: readonly (readonly [number, number])[] = [
  [-1, -1], [-1, 0], [-1, 1], [0, -1], [0, 1], [1, -1], [1, 0], [1, 1],
];
