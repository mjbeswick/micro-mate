import "./styles.css";
import Konva from "konva";
import { Game, type Move } from "./engine";
import { loadPieceImages } from "./assets/pieces";
import { BoardRenderer } from "./render/stage";
import { themeAt } from "./render/themes";
import { DEFAULT_OPTIONS, Store, initialState, type State } from "./state/store";
import { attachInput } from "./controller/input";
import { computeAIMove } from "./controller/ai-client";
import { createAIDriver, HUMAN_COLOR } from "./controller/ai-loop";
import { mountTopbar } from "./ui/topbar";
import { mountToast, showToast } from "./ui/toast";
import {
  openConfirmModal,
  openEndgameModal,
  openHelpModal,
  openNewGameModal,
  openPGNModal,
} from "./ui/modals";
import { debouncedSave, loadState, clearState } from "./persistence/save";
import { exportPGN, importPGN, isPGNCompatible } from "./pgn";
import { registerPWA, setThemeColor, setupInstallPrompt } from "./pwa/register";

declare global {
  interface Window {
    Konva: typeof Konva;
  }
}
window.Konva = Konva;

function computeLegalTargets(s: State): [number, number][] {
  if (!s.selected) return [];
  const [r, c] = s.selected;
  return s.game
    .getLegalMoves()
    .filter((m) => m.from[0] === r && m.from[1] === c)
    .map((m) => [m.to[0], m.to[1]] as [number, number]);
}

async function main() {
  const container = document.getElementById("board-container") as HTMLDivElement;
  const topbar = document.getElementById("topbar") as HTMLElement;
  const toastRoot = document.getElementById("toast-root") as HTMLElement;

  const persisted = loadState();
  let opts = persisted?.options ?? DEFAULT_OPTIONS;
  let initialGame: Game;
  if (persisted) {
    try {
      initialGame = Game.fromState(persisted.game);
      initialGame.aiDepth = opts.aiDepth;
    } catch {
      initialGame = new Game(8, 8, opts.aiDepth);
    }
  } else {
    initialGame = new Game(8, 8, opts.aiDepth);
  }

  const initial: State = { ...initialState(initialGame.board.rows, initialGame.board.cols, opts), game: initialGame };
  const store = new Store(initial);
  const pieces = await loadPieceImages();
  const renderer = new BoardRenderer(container);

  const installPrompt = setupInstallPrompt();
  void registerPWA(store);

  const driver = createAIDriver(store, computeAIMove);

  function renderAll() {
    const s = store.get();
    const targets = computeLegalTargets(s);
    const kingCheck = s.game.getKingCheckSquare();
    renderer.render({
      rows: s.game.board.rows,
      cols: s.game.board.cols,
      width: container.clientWidth,
      height: container.clientHeight,
      showCoords: s.options.showCoords,
      themeIndex: s.options.themeIndex,
      pieces,
      bb: s.game.board.bb,
      selected: s.selected,
      cursor: s.cursor,
      lastMove: s.lastMove,
      currentTurn: s.game.turn,
      kingInCheck: kingCheck,
      legalTargetsForSelected: targets,
    });
    setThemeColor(themeAt(s.options.themeIndex).background);
    debouncedSave(s.game, s.options);
  }

  const tryMove = async (m: Move): Promise<boolean> => {
    const s = store.get();
    if (!s.game.makeMove(m)) return false;
    store.set({ lastMove: m, selected: null });
    renderAll();
    await driver.applyAIIfNeeded();
    renderAll();
    await maybeAnnounceEndgame();
    return true;
  };

  const legalFrom = (from: [number, number]): Move[] => {
    const s = store.get();
    return s.game.getLegalMoves().filter((m) => m.from[0] === from[0] && m.from[1] === from[1]);
  };

  attachInput({ store, renderer, tryMove, legalFrom });

  // ---- Topbar handlers ----

  const onChangeDepth = (delta: number) => {
    const s = store.get();
    const next = Math.max(1, Math.min(5, s.options.aiDepth + delta));
    if (next === s.options.aiDepth) return;
    s.game.aiDepth = next;
    store.set({ options: { ...s.options, aiDepth: next } });
    showToast(store, `AI depth: ${next}`);
  };

  const onCycleTheme = () => {
    const s = store.get();
    store.set({ options: { ...s.options, themeIndex: (s.options.themeIndex + 1) % 5 } });
  };
  const onToggleCoords = () =>
    store.set({ options: { ...store.get().options, showCoords: !store.get().options.showCoords } });
  const onToggleAI = () =>
    store.set({ options: { ...store.get().options, aiEnabled: !store.get().options.aiEnabled } });

  const onUndo = () => {
    if (store.get().game.stepBackward()) {
      store.set({ selected: null, lastMove: store.get().game.currentMove });
    }
  };
  const onRedo = () => {
    if (store.get().game.stepForward()) {
      store.set({ selected: null, lastMove: store.get().game.currentMove });
    }
  };

  const onNewGame = async () => {
    const s = store.get();
    if (s.game.moveHistory.length > 0) {
      const confirm = await openConfirmModal("Discard current game?");
      if (!confirm) return;
    }
    const result = await openNewGameModal({
      rows: s.game.board.rows,
      cols: s.game.board.cols,
      aiEnabled: s.options.aiEnabled,
      aiDepth: s.options.aiDepth,
      themeIndex: s.options.themeIndex,
    });
    if (!result) return;
    clearState();
    const game = new Game(result.rows, result.cols, result.aiDepth);
    store.set({
      game,
      selected: null,
      cursor: null,
      lastMove: null,
      options: {
        themeIndex: result.themeIndex,
        showCoords: s.options.showCoords,
        aiEnabled: result.aiEnabled,
        aiDepth: result.aiDepth,
      },
    });
    renderAll();
    await driver.applyAIIfNeeded();
    renderAll();
  };

  const onHelp = () => openHelpModal(installPrompt);

  const onPGN = async () => {
    const s = store.get();
    if (!isPGNCompatible(s.game)) {
      showToast(store, "PGN is 8×8 only");
      return;
    }
    const current = exportPGN(s.game) ?? "";
    const result = await openPGNModal(current);
    if (result.action === "import" && result.text) {
      const { moves, truncatedAt } = importPGN(result.text);
      const game = new Game(8, 8, s.options.aiDepth);
      for (const m of moves) game.makeMove(m);
      store.set({ game, selected: null, lastMove: game.currentMove });
      renderAll();
      if (truncatedAt !== null) {
        showToast(store, `Imported ${moves.length} moves (truncated at ${truncatedAt + 1}: castling/en passant)`);
      } else {
        showToast(store, `Imported ${moves.length} moves`);
      }
      await driver.applyAIIfNeeded();
      renderAll();
    } else if (result.action === "export") {
      showToast(store, "PGN copied");
    }
  };

  mountTopbar(topbar, store, {
    onNewGame, onHelp, onPGN, onUndo, onRedo,
    onToggleAI, onCycleTheme, onToggleCoords, onChangeDepth,
  });
  mountToast(toastRoot, store);

  // ---- Keyboard shortcuts ----

  document.addEventListener("keydown", (e) => {
    if (document.querySelector(".modal-scrim")) return;
    const tag = (e.target as HTMLElement | null)?.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    switch (e.key) {
      case "Escape": store.set({ selected: null }); break;
      case "[": onUndo(); break;
      case "]": onRedo(); break;
      case "t": case "T": onCycleTheme(); break;
      case "c": case "C": onToggleCoords(); break;
      case "+": case "=": onChangeDepth(+1); break;
      case "-": case "_": onChangeDepth(-1); break;
      case "n": case "N": case "r": case "R": void onNewGame(); break;
      case "p": case "P": void onPGN(); break;
      case "?": void onHelp(); break;
      case " ":
      case "Enter": {
        const s = store.get();
        const cur = s.cursor;
        if (!cur) break;
        if (s.selected) {
          const moves = legalFrom(s.selected);
          const m = moves.find((mm) => mm.to[0] === cur[0] && mm.to[1] === cur[1]);
          if (m) void tryMove(m);
          else {
            const owner = s.game.board.pieceAt(cur[0], cur[1]);
            if (owner && owner.color === s.game.turn) store.set({ selected: cur });
          }
        } else {
          const owner = s.game.board.pieceAt(cur[0], cur[1]);
          if (owner && owner.color === s.game.turn) store.set({ selected: cur });
        }
        break;
      }
      case "ArrowUp": case "ArrowDown": case "ArrowLeft": case "ArrowRight": {
        e.preventDefault();
        const s = store.get();
        const cur = s.cursor ?? [Math.floor(s.game.board.rows / 2), Math.floor(s.game.board.cols / 2)];
        const dr = e.key === "ArrowUp" ? -1 : e.key === "ArrowDown" ? 1 : 0;
        const dc = e.key === "ArrowLeft" ? -1 : e.key === "ArrowRight" ? 1 : 0;
        const nr = Math.max(0, Math.min(s.game.board.rows - 1, cur[0] + dr));
        const nc = Math.max(0, Math.min(s.game.board.cols - 1, cur[1] + dc));
        store.set({ cursor: [nr, nc] });
        break;
      }
    }
  });

  // ---- Resize ----

  const onResize = () => {
    renderer.resize(container.clientWidth, container.clientHeight);
    renderAll();
  };
  window.addEventListener("resize", onResize);

  // Subscribe rerender to any state change
  store.subscribe(renderAll);

  async function maybeAnnounceEndgame() {
    const s = store.get();
    if (s.game.getLegalMoves().length === 0) {
      const inCheck = s.game.board.isInCheck(s.game.turn);
      const msg = inCheck
        ? `Checkmate — ${s.game.turn === "w" ? "Black" : "White"} wins`
        : "Stalemate";
      const choice = await openEndgameModal(msg);
      if (choice === "newGame") void onNewGame();
    }
  }

  // ---- Boot ----

  if (!persisted || initialGame.moveHistory.length === 0) {
    // Fresh boot: open the new-game modal so the user picks size/depth
    void onNewGame();
  } else {
    renderAll();
    if (initialGame.turn !== HUMAN_COLOR) {
      await driver.applyAIIfNeeded();
      renderAll();
    }
  }
  renderAll();
}

void main();
