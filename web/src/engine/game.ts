/** Game: holds Board + turn + history snapshots, drives AI via the search. */
import { AI } from "./ai";
import { Board } from "./board";
import { bitLength, cloneBB, emptyBB } from "./bitboard";
import type { Bitboards, Color, GameSnapshot, Kind, Move, Piece } from "./types";
import { KINDS } from "./types";

export class Game {
  board: Board;
  turn: Color = "w";
  moveHistory: Move[] = [];
  history: GameSnapshot[];
  historyIndex = 0;
  aiDepth: number;
  ai: AI;
  private kingCheckSq: [number, number] | null = null;
  private kingCheckValid = false;

  constructor(rows = 5, cols = 6, aiDepth = 3) {
    this.board = new Board(rows, cols);
    this.aiDepth = aiDepth;
    this.ai = new AI(aiDepth);
    this.history = [this.snapshot()];
  }

  private snapshot(): GameSnapshot {
    return { bb: cloneBB(this.board.bb), turn: this.turn };
  }

  private restoreSnapshot(s: GameSnapshot): void {
    this.board.bb = cloneBB(s.bb);
    this.turn = s.turn;
    this.kingCheckValid = false;
  }

  recordPosition(): void {
    if (this.historyIndex < this.history.length - 1) {
      this.history = this.history.slice(0, this.historyIndex + 1);
    }
    this.history.push(this.snapshot());
    this.historyIndex = this.history.length - 1;
  }

  get positionIndex(): number {
    return this.historyIndex;
  }
  get positionCount(): number {
    return this.history.length;
  }
  get currentMove(): Move | null {
    if (this.historyIndex === 0) return null;
    const i = this.historyIndex - 1;
    return this.moveHistory[i] ?? null;
  }

  canStepBackward(): boolean {
    return this.historyIndex > 0;
  }
  canStepForward(): boolean {
    return this.historyIndex < this.history.length - 1;
  }
  stepBackward(): boolean {
    if (!this.canStepBackward()) return false;
    this.historyIndex -= 1;
    this.restoreSnapshot(this.history[this.historyIndex]!);
    return true;
  }
  stepForward(): boolean {
    if (!this.canStepForward()) return false;
    this.historyIndex += 1;
    this.restoreSnapshot(this.history[this.historyIndex]!);
    return true;
  }

  reset(): void {
    this.board = new Board(this.board.rows, this.board.cols);
    this.turn = "w";
    this.moveHistory = [];
    this.history = [this.snapshot()];
    this.historyIndex = 0;
    this.ai = new AI(this.aiDepth);
    this.kingCheckValid = false;
  }

  getLegalMoves(pseudoLegal = false): Move[] {
    return pseudoLegal ? this.board.pseudoLegalMoves(this.turn) : this.board.legalMoves(this.turn);
  }

  getKingCheckSquare(): [number, number] | null {
    if (!this.kingCheckValid) {
      this.kingCheckSq = null;
      if (this.board.isInCheck(this.turn)) {
        const kbb = this.board.bb[this.turn].K;
        if (kbb) {
          const sq = bitLength(kbb) - 1;
          this.kingCheckSq = [Math.floor(sq / this.board.cols), sq % this.board.cols];
        }
      }
      this.kingCheckValid = true;
    }
    return this.kingCheckSq;
  }

  getAIMove(pseudoLegal = false): Move | null {
    const scratch = new Board(this.board.rows, this.board.cols);
    scratch.bb = cloneBB(this.board.bb);
    return this.ai.bestMove(scratch, this.turn, pseudoLegal);
  }

  makeMove(move: Move, pseudoLegal = false): boolean {
    const moves = pseudoLegal
      ? this.board.pseudoLegalMoves(this.turn)
      : this.board.legalMoves(this.turn);
    const found = moves.find(
      (m) => m.from[0] === move.from[0] && m.from[1] === move.from[1] && m.to[0] === move.to[0] && m.to[1] === move.to[1],
    );
    if (!found) return false;
    if (this.historyIndex < this.history.length - 1) {
      this.moveHistory = this.moveHistory.slice(0, this.historyIndex);
    }
    this.moveHistory.push(found);
    this.board.makeUnsafe(found);
    this.turn = this.turn === "w" ? "b" : "w";
    this.kingCheckValid = false;
    this.recordPosition();
    return true;
  }

  // --- Serialisation ---

  toState(): GameStateJSON {
    const { rows, cols } = this.board;
    return {
      rows,
      cols,
      turn: this.turn,
      position_index: this.historyIndex,
      move_history: this.moveHistory.map(serializeMove),
      history: this.history.map((snap) => ({
        turn: snap.turn,
        grid: snapshotGrid(snap, rows, cols),
      })),
    };
  }

  static fromState(state: GameStateJSON): Game {
    const game = new Game(state.rows, state.cols);
    game.turn = state.turn;
    game.moveHistory = state.move_history.map(deserializeMove);
    game.history = state.history.map((snap) => ({
      turn: snap.turn,
      bb: bbFromGrid(snap.grid, state.rows, state.cols),
    }));
    game.historyIndex = state.position_index;
    game.restoreSnapshot(game.history[game.historyIndex]!);
    return game;
  }
}

// --- helpers ---

export interface GameStateJSON {
  rows: number;
  cols: number;
  turn: Color;
  position_index: number;
  move_history: SerializedMove[];
  history: { turn: Color; grid: (PieceJSON | null)[][] }[];
}

interface PieceJSON {
  kind: Kind;
  color: Color;
}
interface SerializedMove {
  from_sq: [number, number];
  to_sq: [number, number];
  promotion: Kind | null;
}

function serializeMove(m: Move): SerializedMove {
  return {
    from_sq: [m.from[0], m.from[1]],
    to_sq: [m.to[0], m.to[1]],
    promotion: m.promotion ?? null,
  };
}
function deserializeMove(s: SerializedMove): Move {
  return { from: s.from_sq, to: s.to_sq, promotion: s.promotion };
}

function snapshotGrid(snap: GameSnapshot, rows: number, cols: number): (PieceJSON | null)[][] {
  const grid: (PieceJSON | null)[][] = Array.from({ length: rows }, () => Array(cols).fill(null));
  for (const color of ["w", "b"] as const) {
    for (const kind of KINDS) {
      let bb = snap.bb[color][kind];
      while (bb) {
        const lsb = bb & -bb;
        const sq = bitLength(lsb) - 1;
        const r = Math.floor(sq / cols);
        const c = sq % cols;
        grid[r]![c] = { kind, color };
        bb ^= lsb;
      }
    }
  }
  return grid;
}

function bbFromGrid(grid: (PieceJSON | null)[][], rows: number, cols: number): Bitboards {
  const bb = emptyBB();
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const p = grid[r]?.[c];
      if (p) bb[p.color][p.kind] |= 1n << BigInt(r * cols + c);
    }
  }
  return bb;
}

export function pieceFromJSON(p: PieceJSON | null): Piece | null {
  return p ? { kind: p.kind, color: p.color } : null;
}
