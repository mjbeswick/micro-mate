// Generate PWA icons from one of the SVG kings.
// Run: node scripts/gen-icons.mjs
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC = resolve(__dirname, "..", "..", "src", "micromate", "assets", "svg", "w_k.svg");
const OUT = resolve(__dirname, "..", "public", "icons");
mkdirSync(OUT, { recursive: true });

if (!existsSync(SRC)) {
  console.error(`Source SVG missing: ${SRC}`);
  process.exit(1);
}

const svg = readFileSync(SRC);

async function render(size, padded = false) {
  const inner = padded ? Math.round(size * 0.7) : size;
  const offset = Math.round((size - inner) / 2);
  const piece = await sharp(svg, { density: 600 })
    .resize(inner, inner, { fit: "contain", background: { r: 0, g: 0, b: 0, alpha: 0 } })
    .png()
    .toBuffer();
  return sharp({
    create: {
      width: size,
      height: size,
      channels: 4,
      background: { r: 58, g: 42, b: 31, alpha: 1 },
    },
  })
    .composite([{ input: piece, left: offset, top: offset }])
    .png()
    .toBuffer();
}

const targets = [
  { size: 192, name: "icon-192.png", padded: false },
  { size: 512, name: "icon-512.png", padded: false },
  { size: 512, name: "icon-512-maskable.png", padded: true },
];

for (const { size, name, padded } of targets) {
  const buf = await render(size, padded);
  writeFileSync(resolve(OUT, name), buf);
  console.log(`Wrote ${name} (${size}x${size}${padded ? " maskable" : ""})`);
}
