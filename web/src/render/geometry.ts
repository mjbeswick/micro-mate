/** Single source of truth for board layout. Both render and input must
 *  consume the SAME geometry object — that's the recurring bug class the
 *  Python CLAUDE.md flags (the coord border eats real pixels). */

export interface GeometryInput {
  rows: number;
  cols: number;
  width: number;
  height: number;
  showCoords: boolean;
}

export interface Geometry {
  cell: number;
  originX: number;
  originY: number;
  border: number;
  rows: number;
  cols: number;
  width: number;
  height: number;
  showCoords: boolean;
}

export function coordBorder(width: number, height: number, showCoords: boolean): number {
  if (!showCoords) return 0;
  return Math.max(18, Math.floor(Math.min(width, height) / 28));
}

export function boardGeometry({
  rows,
  cols,
  width,
  height,
  showCoords,
}: GeometryInput): Geometry {
  const border = coordBorder(width, height, showCoords);
  const innerW = Math.max(1, width - 2 * border);
  const innerH = Math.max(1, height - 2 * border);
  const cell = Math.max(1, Math.min(Math.floor(innerW / cols), Math.floor(innerH / rows)));
  const boardW = cell * cols;
  const boardH = cell * rows;
  const originX = border + Math.floor((innerW - boardW) / 2);
  const originY = Math.floor((height - boardH) / 2);
  return { cell, originX, originY, border, rows, cols, width, height, showCoords };
}

export function squareToPixel(g: Geometry, r: number, c: number): { x: number; y: number } {
  return { x: g.originX + c * g.cell, y: g.originY + r * g.cell };
}

export function pixelToSquare(g: Geometry, x: number, y: number): [number, number] | null {
  const c = Math.floor((x - g.originX) / g.cell);
  const r = Math.floor((y - g.originY) / g.cell);
  if (r >= 0 && r < g.rows && c >= 0 && c < g.cols) return [r, c];
  return null;
}
