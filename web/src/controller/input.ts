/** Input controller — click & drag share one state machine.
 *
 *  Click flow (always evaluated on pointer-up if no drag occurred):
 *    nothing selected → clicking own piece selects it.
 *    something selected → clicking a legal target square commits the move.
 *                         clicking the same square deselects.
 *                         clicking another own piece re-selects.
 *                         anything else deselects.
 *
 *  Drag flow (only after pointer moves > DRAG_THRESHOLD_PX from down):
 *    own piece becomes draggable; release on legal target commits, else snap back.
 */
import type Konva from "konva";
import type { Move } from "../engine";
import type { Store } from "../state/store";
import { pixelToSquare, squareToPixel, type Geometry } from "../render/geometry";
import type { BoardRenderer } from "../render/stage";

const DRAG_THRESHOLD_PX = 4;

export interface InputDeps {
  store: Store;
  renderer: BoardRenderer;
  /** Attempt a move; returns true if applied. Triggers AI loop on success. */
  tryMove: (m: Move) => Promise<boolean> | boolean;
  /** Returns legal moves from the given square for the current side. */
  legalFrom: (from: [number, number]) => Move[];
}

export function attachInput({ store, renderer, tryMove, legalFrom }: InputDeps): () => void {
  const stage = renderer.getStage();

  let dragNode: Konva.Image | null = null;
  let dragStartXY: { x: number; y: number } | null = null;
  let dragOrigin: [number, number] | null = null;
  let dragActive = false;

  const onPointerDown = () => {
    const pos = stage.getPointerPosition();
    if (!pos) return;
    const g = renderer.getGeometry();
    const sq = pixelToSquare(g, pos.x, pos.y);
    if (!sq) {
      dragNode = null;
      dragOrigin = null;
      return;
    }
    dragStartXY = { ...pos };
    const state = store.get();
    const piece = pieceColorAt(state, sq);
    if (piece && piece === state.game.turn) {
      // Could become a drag, or could remain a click if the pointer doesn't move.
      dragNode = renderer.pieceAt(sq[0], sq[1]) ?? null;
      dragOrigin = sq;
      dragActive = false;
    } else {
      // Not own piece — clicks are still routed in onPointerUp via dragOrigin=sq.
      dragNode = null;
      dragOrigin = sq;
      dragActive = false;
    }
  };

  const onPointerMove = () => {
    if (!dragNode || !dragOrigin || !dragStartXY) return;
    const pos = stage.getPointerPosition();
    if (!pos) return;
    if (!dragActive) {
      const dx = pos.x - dragStartXY.x;
      const dy = pos.y - dragStartXY.y;
      if (dx * dx + dy * dy < DRAG_THRESHOLD_PX * DRAG_THRESHOLD_PX) return;
      dragActive = true;
      dragNode.draggable(true);
      dragNode.moveToTop();
      store.set({ selected: dragOrigin });
    }
  };

  const onPointerUp = async () => {
    const origin = dragOrigin;
    const node = dragNode;
    const wasDrag = dragActive;
    cleanup();
    if (!origin) return;

    if (!wasDrag) {
      await handleClick(origin);
      return;
    }

    // Drag release: locate the destination square at pointer-up location.
    const pos = stage.getPointerPosition();
    const g = renderer.getGeometry();
    const sq = pos ? pixelToSquare(g, pos.x, pos.y) : null;
    if (sq && (sq[0] !== origin[0] || sq[1] !== origin[1])) {
      const move = pickMove(legalFrom(origin), origin, sq);
      const applied = move ? await tryMove(move) : false;
      if (!applied && node) snapBack(node, g, origin);
    } else if (node) {
      snapBack(node, g, origin);
    }
  };

  function cleanup() {
    if (dragNode) dragNode.draggable(false);
    dragNode = null;
    dragOrigin = null;
    dragStartXY = null;
    dragActive = false;
  }

  async function handleClick(sq: [number, number]) {
    const state = store.get();
    if (state.selected) {
      if (state.selected[0] === sq[0] && state.selected[1] === sq[1]) {
        store.set({ selected: null });
        return;
      }
      const moves = legalFrom(state.selected);
      const m = pickMove(moves, state.selected, sq);
      if (m) {
        await tryMove(m);
        return;
      }
      // No legal move to this square. Re-select if clicking own piece, else deselect.
      const owner = pieceColorAt(state, sq);
      if (owner && owner === state.game.turn) {
        store.set({ selected: sq });
        return;
      }
      store.set({ selected: null });
    } else {
      const owner = pieceColorAt(state, sq);
      if (owner && owner === state.game.turn) store.set({ selected: sq });
    }
  }

  function snapBack(node: Konva.Image, g: Geometry, origin: [number, number]) {
    const { x, y } = squareToPixel(g, origin[0], origin[1]);
    const padding = Math.max(2, Math.floor(g.cell * 0.05));
    node.to({ x: x + padding, y: y + padding, duration: 0.12 });
  }

  // Listen on the whole stage so empty squares and enemy pieces both fire.
  stage.on("pointerdown mousedown touchstart", onPointerDown as any);
  stage.on("pointermove mousemove touchmove", onPointerMove as any);
  stage.on("pointerup mouseup touchend", onPointerUp as any);

  return () => {
    stage.off("pointerdown mousedown touchstart");
    stage.off("pointermove mousemove touchmove");
    stage.off("pointerup mouseup touchend");
  };
}

function pieceColorAt(state: ReturnType<Store["get"]>, sq: [number, number]): "w" | "b" | null {
  const p = state.game.board.pieceAt(sq[0], sq[1]);
  return p ? p.color : null;
}

function pickMove(moves: Move[], from: [number, number], to: [number, number]): Move | null {
  return (
    moves.find(
      (m) =>
        m.from[0] === from[0] &&
        m.from[1] === from[1] &&
        m.to[0] === to[0] &&
        m.to[1] === to[1],
    ) ?? null
  );
}
