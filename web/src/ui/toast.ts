import type { Store } from "../state/store";

export function mountToast(host: HTMLElement, store: Store): () => void {
  let timer: number | null = null;
  const sync = () => {
    const t = store.get().toast;
    if (!t) {
      host.innerHTML = "";
      return;
    }
    host.innerHTML = `<div class="toast">${escape(t.message)}</div>`;
    if (timer) window.clearTimeout(timer);
    const remaining = Math.max(0, t.expiresAt - Date.now());
    timer = window.setTimeout(() => store.set({ toast: null }), remaining);
  };
  const unsub = store.subscribe(sync);
  sync();
  return () => {
    unsub();
    if (timer) window.clearTimeout(timer);
  };
}

export function showToast(store: Store, message: string, ms = 2200): void {
  store.set({ toast: { message, expiresAt: Date.now() + ms } });
}

function escape(s: string): string {
  return s.replace(/[&<>"']/g, (c) =>
    c === "&" ? "&amp;" : c === "<" ? "&lt;" : c === ">" ? "&gt;" : c === '"' ? "&quot;" : "&#39;",
  );
}
