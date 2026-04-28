/** Themes ported verbatim from src/micromate/renderer.py THEMES tuple. */
export interface Theme {
  name: string;
  background: string;
  lightSquare: string;
  darkSquare: string;
  fromHighlight: string;
  toHighlight: string;
  checkHighlight: string;
  selectedHighlight: string;
  cursorHighlight: string;
  panelFill: string;
  panelBorder: string;
  text: string;
  subtext: string;
}

const rgb = (r: number, g: number, b: number) => `rgb(${r}, ${g}, ${b})`;

export const THEMES: readonly Theme[] = [
  {
    name: "Classic",
    background: rgb(24, 24, 28),
    lightSquare: rgb(240, 217, 181),
    darkSquare: rgb(181, 136, 99),
    fromHighlight: rgb(244, 208, 63),
    toHighlight: rgb(88, 214, 141),
    checkHighlight: rgb(220, 80, 80),
    selectedHighlight: rgb(100, 149, 237),
    cursorHighlight: rgb(200, 200, 200),
    panelFill: rgb(18, 20, 24),
    panelBorder: rgb(72, 78, 88),
    text: rgb(240, 240, 240),
    subtext: rgb(210, 210, 210),
  },
  {
    name: "Forest",
    background: rgb(18, 28, 21),
    lightSquare: rgb(219, 236, 204),
    darkSquare: rgb(102, 138, 92),
    fromHighlight: rgb(246, 221, 110),
    toHighlight: rgb(102, 255, 163),
    checkHighlight: rgb(255, 100, 80),
    selectedHighlight: rgb(80, 160, 220),
    cursorHighlight: rgb(180, 220, 180),
    panelFill: rgb(17, 41, 26),
    panelBorder: rgb(108, 150, 101),
    text: rgb(237, 244, 231),
    subtext: rgb(197, 221, 190),
  },
  {
    name: "Midnight",
    background: rgb(12, 16, 28),
    lightSquare: rgb(137, 173, 212),
    darkSquare: rgb(54, 74, 108),
    fromHighlight: rgb(255, 210, 79),
    toHighlight: rgb(94, 234, 212),
    checkHighlight: rgb(255, 80, 100),
    selectedHighlight: rgb(120, 160, 255),
    cursorHighlight: rgb(180, 200, 240),
    panelFill: rgb(17, 25, 42),
    panelBorder: rgb(98, 123, 166),
    text: rgb(239, 244, 255),
    subtext: rgb(190, 204, 233),
  },
  {
    name: "Grey",
    background: rgb(40, 42, 46),
    lightSquare: rgb(200, 200, 200),
    darkSquare: rgb(110, 112, 116),
    fromHighlight: rgb(220, 200, 120),
    toHighlight: rgb(160, 200, 170),
    checkHighlight: rgb(220, 100, 100),
    selectedHighlight: rgb(130, 160, 200),
    cursorHighlight: rgb(210, 210, 210),
    panelFill: rgb(30, 32, 36),
    panelBorder: rgb(110, 112, 118),
    text: rgb(235, 235, 235),
    subtext: rgb(190, 192, 196),
  },
  {
    name: "Rosewood",
    background: rgb(34, 22, 24),
    lightSquare: rgb(232, 201, 188),
    darkSquare: rgb(132, 82, 74),
    fromHighlight: rgb(250, 201, 80),
    toHighlight: rgb(111, 233, 164),
    checkHighlight: rgb(240, 100, 90),
    selectedHighlight: rgb(180, 120, 200),
    cursorHighlight: rgb(230, 200, 190),
    panelFill: rgb(48, 30, 32),
    panelBorder: rgb(162, 113, 104),
    text: rgb(247, 236, 232),
    subtext: rgb(223, 194, 187),
  },
];

export function themeAt(i: number): Theme {
  const t = THEMES[((i % THEMES.length) + THEMES.length) % THEMES.length];
  return t!;
}
