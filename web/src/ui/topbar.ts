import type { Store } from "../state/store";
import { THEMES } from "../render/themes";

export interface TopbarHandlers {
  onNewGame: () => void;
  onHelp: () => void;
  onPGN: () => void;
  onUndo: () => void;
  onRedo: () => void;
  onToggleAI: () => void;
  onToggleDice: () => void;
  onCycleTheme: () => void;
  onToggleCoords: () => void;
  onChangeDepth: (delta: number) => void;
}

export function mountTopbar(host: HTMLElement, store: Store, h: TopbarHandlers): () => void {
  host.innerHTML = `
    <div class="bar">
      <button data-act="new">New</button>
      <button data-act="undo" title="[">◀</button>
      <button data-act="redo" title="]">▶</button>
      <span class="sep"></span>
      <label>Theme
        <select data-act="theme">
          ${THEMES.map((t, i) => `<option value="${i}">${t.name}</option>`).join("")}
        </select>
      </label>
      <label><input type="checkbox" data-act="coords" /> Coords</label>
      <label><input type="checkbox" data-act="ai" /> AI</label>
      <label><input type="checkbox" data-act="dice" /> Dice</label>
      <label>AI level
        <button data-act="depth-down">−</button>
        <span data-act="depth-val">3</span>
        <button data-act="depth-up">+</button>
      </label>
      <span class="sep"></span>
      <button data-act="pgn">PGN</button>
      <button data-act="help" title="?">?</button>
      <span class="thinking" data-act="thinking" hidden>Thinking…</span>
    </div>
  `;

  const $ = (sel: string) => host.querySelector(sel) as HTMLElement;
  const themeSel = $("[data-act=theme]") as HTMLSelectElement;
  const coordsBox = $("[data-act=coords]") as HTMLInputElement;
  const aiBox = $("[data-act=ai]") as HTMLInputElement;
  const diceBox = $("[data-act=dice]") as HTMLInputElement;
  const depthVal = $("[data-act=depth-val]");
  const thinking = $("[data-act=thinking]");

  const sync = () => {
    const s = store.get();
    themeSel.value = String(s.options.themeIndex);
    coordsBox.checked = s.options.showCoords;
    aiBox.checked = s.options.aiEnabled;
    diceBox.checked = s.options.diceMode;
    depthVal.textContent = String(s.options.aiDepth);
    thinking.hidden = !s.thinking;
  };
  const unsub = store.subscribe(sync);
  sync();

  $("[data-act=new]").addEventListener("click", h.onNewGame);
  $("[data-act=help]").addEventListener("click", h.onHelp);
  $("[data-act=pgn]").addEventListener("click", h.onPGN);
  $("[data-act=undo]").addEventListener("click", h.onUndo);
  $("[data-act=redo]").addEventListener("click", h.onRedo);
  themeSel.addEventListener("change", () => {
    const i = Number(themeSel.value);
    if (i !== store.get().options.themeIndex) {
      store.set({ options: { ...store.get().options, themeIndex: i } });
    }
  });
  coordsBox.addEventListener("change", () =>
    store.set({ options: { ...store.get().options, showCoords: coordsBox.checked } }),
  );
  aiBox.addEventListener("change", h.onToggleAI);
  diceBox.addEventListener("change", h.onToggleDice);
  $("[data-act=depth-down]").addEventListener("click", () => h.onChangeDepth(-1));
  $("[data-act=depth-up]").addEventListener("click", () => h.onChangeDepth(1));

  // Bonus: also expose theme cycle keyboard via an attribute
  (host as HTMLElement & { _cycleTheme: () => void })._cycleTheme = h.onCycleTheme;
  (host as HTMLElement & { _toggleCoords: () => void })._toggleCoords = h.onToggleCoords;
  return () => unsub();
}
