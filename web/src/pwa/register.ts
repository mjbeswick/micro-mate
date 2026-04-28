/** PWA SW registration + update flow. Only loaded in production. */
import type { Store } from "../state/store";
import { showToast } from "../ui/toast";

export interface InstallPromptHandle {
  available: boolean;
  trigger: () => Promise<void>;
}

let deferredPrompt: any = null;

export function setupInstallPrompt(): InstallPromptHandle {
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferredPrompt = e;
  });
  return {
    get available() {
      return deferredPrompt !== null;
    },
    async trigger() {
      if (!deferredPrompt) return;
      deferredPrompt.prompt();
      try {
        await deferredPrompt.userChoice;
      } catch {
        // ignore
      }
      deferredPrompt = null;
    },
  };
}

export function setThemeColor(color: string): void {
  const el = document.querySelector('meta[name="theme-color"]') as HTMLMetaElement | null;
  if (el) el.content = color;
}

export async function registerPWA(store: Store): Promise<void> {
  if (!("serviceWorker" in navigator)) return;
  try {
    const { registerSW } = await import("virtual:pwa-register");
    registerSW({
      immediate: true,
      onNeedRefresh() {
        showToast(store, "New version available — reload to update", 8000);
      },
      onOfflineReady() {
        showToast(store, "Ready to play offline");
      },
    });
  } catch {
    // dev mode without the plugin — ignore
  }
}
