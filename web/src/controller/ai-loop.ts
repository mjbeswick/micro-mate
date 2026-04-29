/** Drives the AI side of the game. Mirrors apply_ai_move_if_needed in run_game.py. */
import type { Game, Move } from "../engine";
import type { Store } from "../state/store";

export const HUMAN_COLOR = "w" as const;

export interface AIDriver {
  /** Call after every human move and at startup. */
  applyAIIfNeeded: () => Promise<void>;
}

export function createAIDriver(
  store: Store,
  computeAIMove: (g: Game, pseudoLegal: boolean) => Promise<Move | null>,
  /** Resolves an AI capture in dice mode. Returns true if the move should be
   *  applied normally (attacker won), false if it was already resolved
   *  via combat (block / attacker loss). */
  resolveDiceCombat?: (g: Game, m: Move) => Promise<boolean>,
): AIDriver {
  return {
    async applyAIIfNeeded() {
      const s = store.get();
      if (!s.options.aiEnabled) return;
      if (s.game.turn === HUMAN_COLOR) return;
      const dice = s.options.diceMode;
      if (s.game.getLegalMoves(dice).length === 0) return;
      store.set({ thinking: true });
      try {
        await new Promise((r) => setTimeout(r, 16));
        const mv = await computeAIMove(s.game, dice);
        if (mv) {
          if (dice && s.game.board.pieceAt(mv.to[0], mv.to[1]) !== null && resolveDiceCombat) {
            const wins = await resolveDiceCombat(s.game, mv);
            if (wins) s.game.makeMove(mv, true);
          } else {
            s.game.makeMove(mv, dice);
          }
          store.set({ lastMove: mv });
        }
      } finally {
        store.set({ thinking: false });
      }
    },
  };
}
