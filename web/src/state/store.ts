/** Tiny pub/sub store. ~50 lines on purpose — see plan §5. */
import { Game, type Move } from "../engine";

export type ThemeIndex = 0 | 1 | 2 | 3 | 4;
export type ModalKind = "newGame" | "help" | "checkmate" | "confirm" | "pgn";

export interface Options {
  themeIndex: number;
  showCoords: boolean;
  aiEnabled: boolean;
  aiDepth: number; // 1..5
}

export interface Toast {
  message: string;
  expiresAt: number;
}

export interface State {
  game: Game;
  selected: [number, number] | null;
  cursor: [number, number] | null;
  lastMove: Move | null;
  options: Options;
  modal: ModalKind | null;
  toast: Toast | null;
  thinking: boolean;
}

type Listener = (s: State) => void;

export class Store {
  private state: State;
  private listeners = new Set<Listener>();

  constructor(initial: State) {
    this.state = initial;
  }

  get(): State {
    return this.state;
  }

  set(patch: Partial<State>): void {
    this.state = { ...this.state, ...patch };
    for (const l of this.listeners) l(this.state);
  }

  subscribe(l: Listener): () => void {
    this.listeners.add(l);
    return () => this.listeners.delete(l);
  }
}

export const DEFAULT_OPTIONS: Options = {
  themeIndex: 0,
  showCoords: false,
  aiEnabled: true,
  aiDepth: 3,
};

export function initialState(rows = 8, cols = 8, opts: Options = DEFAULT_OPTIONS): State {
  return {
    game: new Game(rows, cols, opts.aiDepth),
    selected: null,
    cursor: null,
    lastMove: null,
    options: opts,
    modal: null,
    toast: null,
    thinking: false,
  };
}
