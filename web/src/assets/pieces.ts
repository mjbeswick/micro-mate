import type { Color, Kind } from "../engine";

export type PieceKey = `${Color}_${Lowercase<Kind>}`;

export const PIECE_KEYS: readonly PieceKey[] = [
  "w_p", "w_n", "w_b", "w_r", "w_q", "w_k",
  "b_p", "b_n", "b_b", "b_r", "b_q", "b_k",
];

export function pieceKey(color: Color, kind: Kind): PieceKey {
  return `${color}_${kind.toLowerCase() as Lowercase<Kind>}`;
}

export async function loadPieceImages(): Promise<Map<PieceKey, HTMLImageElement>> {
  const map = new Map<PieceKey, HTMLImageElement>();
  await Promise.all(
    PIECE_KEYS.map(async (k) => {
      const img = new Image();
      img.src = `/pieces/${k}.svg`;
      await img.decode().catch(() => undefined);
      map.set(k, img);
    }),
  );
  return map;
}
