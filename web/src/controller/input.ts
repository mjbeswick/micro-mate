/** Input controller — click & drag share one state machine. */
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
  const pieceLayer = renderer.getPieceLayer();

  let dragNode: Konva.Image | null = null;
  let dragStartXY: { x: number; y: number } | null = null;
  let dragOrigin: [number, number] | null = null;
  let dragActive = false;

  const onPointerDown = (e: Konva.KonvaEventObject<PointerEvent | MouseEvent | TouchEvent>) => {
    const target = e.target;
    const pos = stage.getPointerPosition();
    if (!pos) return;
    const g = renderer.getGeometry();
    const sq = pixelToSquare(g, pos.x, pos.y);
    if (!sq) return;
    const state = store.get();
    const piece = pieceColorAt(state, sq);
    if (piece && piece === state.game.turn) {
      dragNode = target instanceof window.Konva!.Image ? (target as Konva.Image) : renderer.pieceAt(sq[0], sq[1]) ?? null;
      dragStartXY = { ...pos };
      dragOrigin = sq;
      dragActive = false;
    } else {
      dragNode = null;
      dragOrigin = null;
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
      // Mark selected on first drag movement
      store.set({ selected: dragOrigin });
    }
    // Konva will move the node automatically since draggable=true now
  };

  const onPointerUp = async () => {
    if (!dragNode || !dragOrigin) {
      dragNode = null;
      dragOrigin = null;
      dragActive = false;
      return;
    }
    if (!dragActive) {
      // It was a click, not a drag — handle click selection.
      handleClick(dragOrigin);
      cleanup();
      return;
    }
    const pos = stage.getPointerPosition();
    const g = renderer.getGeometry();
    const sq = pos ? pixelToSquare(g, pos.x, pos.y) : null;
    const node = dragNode;
    const origin = dragOrigin;
    cleanup();
    if (sq && (sq[0] !== origin[0] || sq[1] !== origin[1])) {
      const move = pickPromotion(legalFrom(origin), origin, sq);
      const applied = move ? await tryMove(move) : false;
      if (!applied) snapBack(node, g, origin);
    } else {
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
      const m = pickPromotion(moves, state.selected, sq);
      if (m) {
        const ok = await tryMove(m);
        if (ok) store.set({ selected: null });
        return;
      }
      // Re-select if clicking own piece
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

  pieceLayer.on("pointerdown mousedown touchstart", onPointerDown as any);
  stage.on("pointermove mousemove touchmove", onPointerMove as any);
  stage.on("pointerup mouseup touchend", onPointerUp as any);

  // Bare click on empty square (no piece under pointer) deselects.
  stage.on("click tap", (e) => {
    if (e.target === stage) {
      const pos = stage.getPointerPosition();
      if (!pos) return;
      const sq = pixelToSquare(renderer.getGeometry(), pos.x, pos.y);
      if (sq) handleClick(sq);
    }
  });

  return () => {
    pieceLayer.off("pointerdown mousedown touchstart");
    stage.off("pointermove mousemove touchmove");
    stage.off("pointerup mouseup touchend");
    stage.off("click tap");
  };
}

function pieceColorAt(state: ReturnType<Store["get"]>, sq: [number, number]): "w" | "b" | null {
  const p = state.game.board.pieceAt(sq[0], sq[1]);
  return p ? p.color : null;
}

function pickPromotion(moves: Move[], from: [number, number], to: [number, number]): Move | null {
  // Engine auto-promotes to Q; just match from/to.
  return (
    moves.find(
      (m) => m.from[0] === from[0] && m.from[1] === from[1] && m.to[0] === to[0] && m.to[1] === to[1],
    ) ?? null
  );
}
