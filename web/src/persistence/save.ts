/** localStorage save/load for full Game + Options. */
import { Game, type GameStateJSON } from "../engine";
import type { Options } from "../state/store";

const KEY = "micro-mate:save";

export interface Persisted {
  game: GameStateJSON;
  options: Options;
}

export function saveState(game: Game, options: Options): void {
  const data: Persisted = { game: game.toState(), options };
  try {
    localStorage.setItem(KEY, JSON.stringify(data));
  } catch {
    // quota / private mode — silently skip
  }
}

export function loadState(): Persisted | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    return JSON.parse(raw) as Persisted;
  } catch {
    return null;
  }
}

export function clearState(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    // ignore
  }
}

let saveTimer: number | null = null;
export function debouncedSave(game: Game, options: Options, delayMs = 250): void {
  if (saveTimer !== null) window.clearTimeout(saveTimer);
  saveTimer = window.setTimeout(() => saveState(game, options), delayMs);
}
