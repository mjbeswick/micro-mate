/** Drives the AI side of the game. Mirrors apply_ai_move_if_needed in run_game.py. */
import type { Game, Move } from "../engine";
import type { Store } from "../state/store";

export const HUMAN_COLOR = "w" as const;

export interface AIDriver {
  /** Call after every human move and at startup. */
  applyAIIfNeeded: () => Promise<void>;
}

export function createAIDriver(store: Store, computeAIMove: (g: Game) => Promise<Move | null>): AIDriver {
  return {
    async applyAIIfNeeded() {
      const s = store.get();
      if (!s.options.aiEnabled) return;
      if (s.game.turn === HUMAN_COLOR) return;
      // Check terminal: no legal moves
      if (s.game.getLegalMoves().length === 0) return;
      store.set({ thinking: true });
      try {
        // Yield to the event loop so the spinner/UI repaints before search.
        await new Promise((r) => setTimeout(r, 16));
        const mv = await computeAIMove(s.game);
        if (mv) {
          s.game.makeMove(mv);
          store.set({ lastMove: mv });
        }
      } finally {
        store.set({ thinking: false });
      }
      // If AI plays both sides (ai_enabled but human turn), recurse — we don't support that mode.
    },
  };
}
