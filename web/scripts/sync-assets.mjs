// Copy SVG pieces from the Python project into web/public/pieces/.
// Runs as part of the dev/build flow so the web app stays self-contained
// (no symlinks — Windows-friendly).
import { copyFileSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC = resolve(__dirname, "..", "..", "src", "micromate", "assets", "svg");
const DEST = resolve(__dirname, "..", "public", "pieces");

if (!existsSync(SRC)) {
  console.warn(`Source SVG dir not found: ${SRC} — assuming public/pieces/ is pre-populated.`);
  process.exit(0);
}
mkdirSync(DEST, { recursive: true });

const files = readdirSync(SRC).filter((f) => f.endsWith(".svg"));
for (const f of files) {
  copyFileSync(join(SRC, f), join(DEST, f));
}
console.log(`Copied ${files.length} SVG pieces -> ${DEST}`);
