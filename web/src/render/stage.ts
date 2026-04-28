import Konva from "konva";
import type { Move, Piece } from "../engine";
import { KINDS } from "../engine";
import type { PieceKey } from "../assets/pieces";
import { pieceKey } from "../assets/pieces";
import { boardGeometry, type Geometry, squareToPixel } from "./geometry";
import { themeAt, type Theme } from "./themes";

export interface RenderInputs {
  rows: number;
  cols: number;
  width: number;
  height: number;
  showCoords: boolean;
  themeIndex: number;
  pieces: ReadonlyMap<PieceKey, HTMLImageElement>;
  bb: import("../engine").Bitboards;
  selected: [number, number] | null;
  cursor: [number, number] | null;
  lastMove: Move | null;
  currentTurn: "w" | "b";
  kingInCheck: [number, number] | null;
  legalTargetsForSelected: [number, number][];
}

export class BoardRenderer {
  stage: Konva.Stage;
  private boardLayer: Konva.Layer;
  private highlightLayer: Konva.Layer;
  private pieceLayer: Konva.Layer;
  private overlayLayer: Konva.Layer;
  private geometry!: Geometry;
  private theme!: Theme;
  private pieceNodes = new Map<string, Konva.Image>();

  constructor(container: HTMLDivElement) {
    this.stage = new Konva.Stage({
      container,
      width: container.clientWidth,
      height: container.clientHeight,
    });
    this.boardLayer = new Konva.Layer({ listening: false });
    this.highlightLayer = new Konva.Layer({ listening: false });
    this.pieceLayer = new Konva.Layer();
    this.overlayLayer = new Konva.Layer({ listening: false });
    this.stage.add(this.boardLayer);
    this.stage.add(this.highlightLayer);
    this.stage.add(this.pieceLayer);
    this.stage.add(this.overlayLayer);
  }

  resize(width: number, height: number): void {
    this.stage.size({ width, height });
  }

  getGeometry(): Geometry {
    return this.geometry;
  }

  getStage(): Konva.Stage {
    return this.stage;
  }

  getPieceLayer(): Konva.Layer {
    return this.pieceLayer;
  }

  render(input: RenderInputs): void {
    this.theme = themeAt(input.themeIndex);
    this.geometry = boardGeometry({
      rows: input.rows,
      cols: input.cols,
      width: input.width,
      height: input.height,
      showCoords: input.showCoords,
    });
    this.stage.container().style.background = this.theme.background;
    this.drawBoard(input);
    this.drawHighlights(input);
    this.drawPieces(input);
  }

  private drawBoard(input: RenderInputs): void {
    this.boardLayer.destroyChildren();
    const g = this.geometry;
    const colors = [this.theme.lightSquare, this.theme.darkSquare];
    for (let r = 0; r < input.rows; r++) {
      for (let c = 0; c < input.cols; c++) {
        const { x, y } = squareToPixel(g, r, c);
        this.boardLayer.add(
          new Konva.Rect({
            x,
            y,
            width: g.cell,
            height: g.cell,
            fill: colors[(r + c) % 2],
            listening: false,
          }),
        );
      }
    }
    if (input.showCoords && g.border > 0) this.drawCoordLabels(input);
    this.boardLayer.batchDraw();
  }

  private drawCoordLabels(input: RenderInputs): void {
    const g = this.geometry;
    const fontSize = Math.max(12, Math.floor(g.border * 0.7));
    for (let c = 0; c < input.cols; c++) {
      const letter = String.fromCharCode("a".charCodeAt(0) + c);
      const cx = g.originX + c * g.cell + g.cell / 2;
      const topY = Math.max(0, g.originY - g.border / 2);
      const botY = g.originY + input.rows * g.cell + g.border / 2;
      for (const cy of [topY, botY]) {
        this.boardLayer.add(this.textLabel(letter, cx, cy, fontSize));
      }
    }
    for (let r = 0; r < input.rows; r++) {
      const number = String(input.rows - r);
      const cy = g.originY + r * g.cell + g.cell / 2;
      const leftX = Math.max(0, g.originX - g.border / 2);
      const rightX = g.originX + input.cols * g.cell + g.border / 2;
      for (const cx of [leftX, rightX]) {
        this.boardLayer.add(this.textLabel(number, cx, cy, fontSize));
      }
    }
  }

  private textLabel(text: string, cx: number, cy: number, fontSize: number): Konva.Text {
    const t = new Konva.Text({
      text,
      fontSize,
      fontStyle: "bold",
      fill: this.theme.subtext,
      listening: false,
    });
    t.x(cx - t.width() / 2);
    t.y(cy - t.height() / 2);
    return t;
  }

  private drawHighlights(input: RenderInputs): void {
    this.highlightLayer.destroyChildren();
    const g = this.geometry;
    const lineWidth = Math.max(3, Math.floor(g.cell / 16));

    if (input.lastMove) {
      const base = input.currentTurn === "b" ? this.theme.fromHighlight : this.theme.toHighlight;
      const [fr, fc] = input.lastMove.from;
      const [tr, tc] = input.lastMove.to;
      this.highlightLayer.add(this.borderRect(fr, fc, base, lineWidth, 0.65));
      this.highlightLayer.add(this.borderRect(tr, tc, base, lineWidth, 1.05));
    }

    if (input.kingInCheck) {
      const [r, c] = input.kingInCheck;
      this.highlightLayer.add(
        this.borderRect(r, c, this.theme.checkHighlight, Math.max(4, Math.floor(g.cell / 12))),
      );
    }
    if (input.selected) {
      const [r, c] = input.selected;
      this.highlightLayer.add(
        this.borderRect(r, c, this.theme.selectedHighlight, Math.max(4, Math.floor(g.cell / 12))),
      );
    }
    if (input.cursor && (!input.selected || input.cursor[0] !== input.selected[0] || input.cursor[1] !== input.selected[1])) {
      const [r, c] = input.cursor;
      this.highlightLayer.add(
        this.borderRect(r, c, this.theme.cursorHighlight, Math.max(3, Math.floor(g.cell / 16))),
      );
    }

    // Legal target dots
    for (const [r, c] of input.legalTargetsForSelected) {
      const { x, y } = squareToPixel(g, r, c);
      this.highlightLayer.add(
        new Konva.Circle({
          x: x + g.cell / 2,
          y: y + g.cell / 2,
          radius: Math.max(4, Math.floor(g.cell / 8)),
          fill: this.theme.selectedHighlight,
          opacity: 0.55,
          listening: false,
        }),
      );
    }
    this.highlightLayer.batchDraw();
  }

  private borderRect(r: number, c: number, stroke: string, strokeWidth: number, brightness = 1): Konva.Rect {
    const { x, y } = squareToPixel(this.geometry, r, c);
    return new Konva.Rect({
      x,
      y,
      width: this.geometry.cell,
      height: this.geometry.cell,
      stroke,
      strokeWidth,
      opacity: brightness > 1 ? 1 : 0.85 * brightness + 0.1,
      listening: false,
    });
  }

  private drawPieces(input: RenderInputs): void {
    this.pieceLayer.destroyChildren();
    this.pieceNodes.clear();
    const g = this.geometry;
    const padding = Math.max(2, Math.floor(g.cell * 0.05));
    const size = g.cell - 2 * padding;
    for (const color of ["w", "b"] as const) {
      for (const kind of KINDS) {
        let bb = input.bb[color][kind];
        while (bb) {
          const lsb = bb & -bb;
          const sq = bitLength(lsb) - 1;
          const r = Math.floor(sq / input.cols);
          const c = sq % input.cols;
          const { x, y } = squareToPixel(g, r, c);
          const img = input.pieces.get(pieceKey(color, kind));
          if (img) {
            const node = new Konva.Image({
              image: img,
              x: x + padding,
              y: y + padding,
              width: size,
              height: size,
              draggable: false,
            });
            node.setAttr("piece", { color, kind } as Piece);
            node.setAttr("square", [r, c] as [number, number]);
            this.pieceLayer.add(node);
            this.pieceNodes.set(`${r},${c}`, node);
          }
          bb ^= lsb;
        }
      }
    }
    this.pieceLayer.batchDraw();
  }

  pieceAt(r: number, c: number): Konva.Image | undefined {
    return this.pieceNodes.get(`${r},${c}`);
  }
}

function bitLength(b: bigint): number {
  if (b === 0n) return 0;
  let v = b < 0n ? -b : b;
  let n = 0;
  while (v >= 0x100000000n) {
    v >>= 32n;
    n += 32;
  }
  let v32 = Number(v);
  while (v32 > 0) {
    v32 >>>= 1;
    n++;
  }
  return n;
}
