export type Color = "w" | "b";
export type Kind = "P" | "N" | "B" | "R" | "Q" | "K";

export const KINDS: readonly Kind[] = ["P", "N", "B", "R", "Q", "K"] as const;

export interface Piece {
  kind: Kind;
  color: Color;
}

export interface Move {
  from: readonly [number, number];
  to: readonly [number, number];
  promotion?: Kind | null;
}

export type Bitboards = Record<Color, Record<Kind, bigint>>;

export interface GameSnapshot {
  bb: Bitboards;
  turn: Color;
}
