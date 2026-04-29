/** Dice-mode combat modal. Rolls two d6, animates briefly, then shows the
 *  outcome and resolves. Resolution rules (mirror src/run_game.py):
 *    equal           → blocked         (skipTurn)
 *    atk > def       → attacker_wins   (caller commits the move)
 *    def > atk       → defender_wins   (makeAttackerLoss) */
import type { Game, Move, Piece } from "../engine";

export type CombatOutcome = "blocked" | "attacker_wins" | "defender_wins";

export function combatOutcome(atk: number, def: number): CombatOutcome {
  if (atk === def) return "blocked";
  return atk > def ? "attacker_wins" : "defender_wins";
}

const PIECE_NAMES: Record<string, string> = {
  P: "Pawn", N: "Knight", B: "Bishop", R: "Rook", Q: "Queen", K: "King",
};

const ROOT_ID = "modal-root";

function root(): HTMLElement {
  const el = document.getElementById(ROOT_ID);
  if (!el) throw new Error("modal-root missing");
  return el;
}

const DOTS: Record<number, [number, number][]> = {
  1: [[0.5, 0.5]],
  2: [[0.25, 0.25], [0.75, 0.75]],
  3: [[0.25, 0.25], [0.5, 0.5], [0.75, 0.75]],
  4: [[0.25, 0.25], [0.75, 0.25], [0.25, 0.75], [0.75, 0.75]],
  5: [[0.25, 0.25], [0.75, 0.25], [0.5, 0.5], [0.25, 0.75], [0.75, 0.75]],
  6: [[0.25, 0.25], [0.75, 0.25], [0.25, 0.5], [0.75, 0.5], [0.25, 0.75], [0.75, 0.75]],
};

function dieSVG(value: number, size = 64): string {
  const r = Math.max(3, Math.floor(size / 10));
  const dots = DOTS[value]!.map(([fx, fy]) => `<circle cx="${fx * size}" cy="${fy * size}" r="${r}" fill="#1f1f1f"/>`).join("");
  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">
    <rect x="1" y="1" width="${size - 2}" height="${size - 2}" rx="${size / 8}" fill="#f5f5f5" stroke="#444" stroke-width="2"/>
    ${dots}
  </svg>`;
}

const colorName = (p: Piece) => (p.color === "w" ? "White" : "Black");
const pieceLabel = (p: Piece) => `${colorName(p)} ${PIECE_NAMES[p.kind] ?? p.kind}`;

/** Show the dice combat modal. Returns the outcome after the user dismisses. */
export function runDiceCombat(
  game: Game,
  move: Move,
  atkPiece: Piece,
  defPiece: Piece,
): Promise<CombatOutcome> {
  return new Promise((resolve) => {
    const atk = 1 + Math.floor(Math.random() * 6);
    const def = 1 + Math.floor(Math.random() * 6);
    const outcome = combatOutcome(atk, def);

    const scrim = document.createElement("div");
    scrim.className = "modal-scrim";
    const dialog = document.createElement("div");
    dialog.className = "modal-dialog dice-modal";
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.tabIndex = -1;

    const matchupLabel = `${pieceLabel(atkPiece)}  vs  ${pieceLabel(defPiece)}`;

    dialog.innerHTML = `
      <h2>Combat</h2>
      <p class="matchup"></p>
      <div class="dice-row">
        <div class="die" data-side="atk"></div>
        <span class="vs">vs</span>
        <div class="die" data-side="def"></div>
      </div>
      <p class="result"></p>
      <div class="modal-actions">
        <button type="button" data-ok class="primary" disabled>OK</button>
      </div>
    `;
    (dialog.querySelector(".matchup") as HTMLElement).textContent = matchupLabel;
    const atkEl = dialog.querySelector("[data-side=atk]") as HTMLElement;
    const defEl = dialog.querySelector("[data-side=def]") as HTMLElement;
    const resultEl = dialog.querySelector(".result") as HTMLElement;
    const okBtn = dialog.querySelector("[data-ok]") as HTMLButtonElement;

    scrim.appendChild(dialog);
    root().appendChild(scrim);

    // Roll animation: cycle random faces, then settle.
    let ticks = 0;
    const interval = window.setInterval(() => {
      atkEl.innerHTML = dieSVG(1 + Math.floor(Math.random() * 6));
      defEl.innerHTML = dieSVG(1 + Math.floor(Math.random() * 6));
      if (++ticks >= 8) {
        window.clearInterval(interval);
        atkEl.innerHTML = dieSVG(atk);
        defEl.innerHTML = dieSVG(def);
        const winnerText =
          outcome === "blocked"
            ? "Blocked — turn passes."
            : outcome === "attacker_wins"
              ? `${pieceLabel(atkPiece)} wins the combat!`
              : `${pieceLabel(defPiece)} defends — attacker lost!`;
        resultEl.textContent = `${atk} vs ${def}. ${winnerText}`;
        okBtn.disabled = false;
        okBtn.focus();
      }
    }, 90);

    const finish = () => {
      window.clearInterval(interval);
      window.removeEventListener("keydown", onKey, true);
      scrim.remove();
      // Apply non-attacker-wins outcomes to the game state here so the
      // caller doesn't need to know about combat resolution.
      if (outcome === "blocked") game.skipTurn(move);
      else if (outcome === "defender_wins") game.makeAttackerLoss(move);
      resolve(outcome);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Enter" || e.key === "Escape" || e.key === " ") {
        if (!okBtn.disabled) {
          e.preventDefault();
          finish();
        }
      }
    };
    okBtn.addEventListener("click", finish);
    window.addEventListener("keydown", onKey, true);
    requestAnimationFrame(() => dialog.focus());
  });
}
