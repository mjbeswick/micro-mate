/** HTML overlay modals. Each function appends a <div> to #modal-root and
 *  returns a Promise that resolves with the user's choice. ESC closes with
 *  the default (cancel) result. */

const ROOT_ID = "modal-root";

function root(): HTMLElement {
  const el = document.getElementById(ROOT_ID);
  if (!el) throw new Error("modal-root missing");
  return el;
}

function buildScrim(): { scrim: HTMLDivElement; dialog: HTMLDivElement } {
  const scrim = document.createElement("div");
  scrim.className = "modal-scrim";
  const dialog = document.createElement("div");
  dialog.className = "modal-dialog";
  dialog.setAttribute("role", "dialog");
  dialog.setAttribute("aria-modal", "true");
  dialog.tabIndex = -1;
  scrim.appendChild(dialog);
  return { scrim, dialog };
}

function present<T>(
  build: (resolve: (v: T) => void) => HTMLElement,
  cancelValue: T,
): Promise<T> {
  return new Promise<T>((resolve) => {
    const { scrim, dialog } = buildScrim();
    const finish = (v: T) => {
      window.removeEventListener("keydown", onKey, true);
      scrim.remove();
      resolve(v);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        finish(cancelValue);
      }
    };
    window.addEventListener("keydown", onKey, true);
    scrim.addEventListener("click", (e) => {
      if (e.target === scrim) finish(cancelValue);
    });
    dialog.appendChild(build(finish));
    root().appendChild(scrim);
    requestAnimationFrame(() => dialog.focus());
  });
}

// ---- New Game ----

export interface NewGameResult {
  rows: number;
  cols: number;
  aiEnabled: boolean;
  aiDepth: number;
  themeIndex: number;
}

const SIZE_PRESETS: [number, number, string][] = [
  [3, 3, "3×3"],
  [4, 4, "4×4"],
  [6, 6, "6×6"],
  [8, 8, "8×8"],
  [10, 10, "10×10"],
  [16, 16, "16×16"],
];

export function openNewGameModal(initial: NewGameResult): Promise<NewGameResult | null> {
  return present<NewGameResult | null>((resolve) => {
    const wrap = document.createElement("div");
    let chosen = { ...initial };
    wrap.innerHTML = `
      <h2>New game</h2>
      <fieldset><legend>Board size</legend><div class="size-grid"></div></fieldset>
      <label>AI <input type="checkbox" ${chosen.aiEnabled ? "checked" : ""} data-ai></label>
      <label>Depth <input type="range" min="1" max="5" value="${chosen.aiDepth}" data-depth /> <span data-depth-val>${chosen.aiDepth}</span></label>
      <label>Theme
        <select data-theme>
          ${["Classic", "Forest", "Midnight", "Grey", "Rosewood"]
            .map((n, i) => `<option value="${i}" ${i === chosen.themeIndex ? "selected" : ""}>${n}</option>`)
            .join("")}
        </select>
      </label>
      <div class="modal-actions">
        <button type="button" data-cancel>Cancel</button>
        <button type="button" data-ok class="primary">Start</button>
      </div>
    `;
    const sizeGrid = wrap.querySelector(".size-grid") as HTMLElement;
    for (const [rows, cols, label] of SIZE_PRESETS) {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = label;
      b.className =
        rows === chosen.rows && cols === chosen.cols ? "size-chip selected" : "size-chip";
      b.addEventListener("click", () => {
        chosen.rows = rows;
        chosen.cols = cols;
        sizeGrid.querySelectorAll("button").forEach((x) => x.classList.remove("selected"));
        b.classList.add("selected");
      });
      sizeGrid.appendChild(b);
    }
    wrap.querySelector("[data-ai]")!.addEventListener("change", (e) => {
      chosen.aiEnabled = (e.target as HTMLInputElement).checked;
    });
    const depthInput = wrap.querySelector("[data-depth]") as HTMLInputElement;
    const depthVal = wrap.querySelector("[data-depth-val]") as HTMLElement;
    depthInput.addEventListener("input", () => {
      chosen.aiDepth = Number(depthInput.value);
      depthVal.textContent = depthInput.value;
    });
    wrap.querySelector("[data-theme]")!.addEventListener("change", (e) => {
      chosen.themeIndex = Number((e.target as HTMLSelectElement).value);
    });
    wrap.querySelector("[data-cancel]")!.addEventListener("click", () => resolve(null));
    wrap.querySelector("[data-ok]")!.addEventListener("click", () => resolve(chosen));
    return wrap;
  }, null);
}

// ---- Confirm ----

export function openConfirmModal(message: string): Promise<boolean> {
  return present<boolean>((resolve) => {
    const wrap = document.createElement("div");
    wrap.innerHTML = `
      <h2>Confirm</h2>
      <p></p>
      <div class="modal-actions">
        <button type="button" data-no>Cancel</button>
        <button type="button" data-yes class="primary">OK</button>
      </div>
    `;
    wrap.querySelector("p")!.textContent = message;
    wrap.querySelector("[data-no]")!.addEventListener("click", () => resolve(false));
    wrap.querySelector("[data-yes]")!.addEventListener("click", () => resolve(true));
    return wrap;
  }, false);
}

// ---- Checkmate / Stalemate ----

export function openEndgameModal(message: string): Promise<"newGame" | "close"> {
  return present<"newGame" | "close">((resolve) => {
    const wrap = document.createElement("div");
    wrap.innerHTML = `
      <h2>Game over</h2>
      <p></p>
      <div class="modal-actions">
        <button type="button" data-close>Close</button>
        <button type="button" data-new class="primary">New game</button>
      </div>
    `;
    wrap.querySelector("p")!.textContent = message;
    wrap.querySelector("[data-close]")!.addEventListener("click", () => resolve("close"));
    wrap.querySelector("[data-new]")!.addEventListener("click", () => resolve("newGame"));
    return wrap;
  }, "close");
}

// ---- Help ----

export function openHelpModal(installPrompt: { available: boolean; trigger: () => void }): Promise<void> {
  return present<void>((resolve) => {
    const wrap = document.createElement("div");
    wrap.innerHTML = `
      <h2>Micro-Mate help</h2>
      <table class="kbd">
        <tr><td>Click / tap</td><td>Select piece, then move</td></tr>
        <tr><td>Drag</td><td>Move piece</td></tr>
        <tr><td>Arrows / Space</td><td>Cursor + commit</td></tr>
        <tr><td>[ / ]</td><td>Step move history</td></tr>
        <tr><td>T / C</td><td>Theme / coords</td></tr>
        <tr><td>+ / −</td><td>AI depth</td></tr>
        <tr><td>N / R</td><td>New game</td></tr>
        <tr><td>P</td><td>PGN import/export (8×8)</td></tr>
        <tr><td>?</td><td>This help</td></tr>
      </table>
      <p class="install-row"></p>
      <div class="modal-actions">
        <button type="button" data-close class="primary">Close</button>
      </div>
    `;
    const row = wrap.querySelector(".install-row") as HTMLElement;
    if (installPrompt.available) {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = "Install Micro-Mate";
      b.addEventListener("click", () => {
        installPrompt.trigger();
        resolve();
      });
      row.appendChild(b);
    } else if (/iPhone|iPad|iPod/.test(navigator.userAgent)) {
      row.textContent = "On iOS, tap Share → Add to Home Screen to install.";
    } else {
      row.textContent = "Install option will appear when the browser allows it.";
    }
    wrap.querySelector("[data-close]")!.addEventListener("click", () => resolve());
    return wrap;
  }, undefined);
}

// ---- PGN ----

export interface PGNResult {
  action: "import" | "export" | "cancel";
  text?: string;
}

export function openPGNModal(currentExport: string): Promise<PGNResult> {
  return present<PGNResult>((resolve) => {
    const wrap = document.createElement("div");
    wrap.innerHTML = `
      <h2>PGN (8×8 only)</h2>
      <textarea rows="10" cols="40" data-text></textarea>
      <div class="modal-actions">
        <button type="button" data-cancel>Cancel</button>
        <button type="button" data-export>Export</button>
        <button type="button" data-import class="primary">Import</button>
      </div>
    `;
    const ta = wrap.querySelector("[data-text]") as HTMLTextAreaElement;
    ta.value = currentExport;
    wrap.querySelector("[data-cancel]")!.addEventListener("click", () => resolve({ action: "cancel" }));
    wrap.querySelector("[data-export]")!.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(ta.value);
      } catch {
        // ignore — user can copy manually
      }
      resolve({ action: "export", text: ta.value });
    });
    wrap.querySelector("[data-import]")!.addEventListener("click", () => {
      resolve({ action: "import", text: ta.value });
    });
    return wrap;
  }, { action: "cancel" });
}
