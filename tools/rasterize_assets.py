"""Rasterize SVG assets into PNGs for Pi packaging."""
import os
from pathlib import Path
try:
    import cairosvg
except Exception:
    cairosvg = None

SVG_DIR = Path(__file__).resolve().parents[1] / 'assets' / 'svg'
PNG_DIR = Path(__file__).resolve().parents[1] / 'assets' / 'png'
PNG_DIR.mkdir(parents=True, exist_ok=True)

def rasterize(size=64):
    if cairosvg is None:
        print('cairosvg not installed; cannot rasterize at runtime.')
        return
    for svg in SVG_DIR.glob('*.svg'):
        out = PNG_DIR / (svg.stem + f'-{size}.png')
        print('Rasterizing', svg, '->', out)
        cairosvg.svg2png(url=str(svg), write_to=str(out), output_width=size, output_height=size)

if __name__ == '__main__':
    rasterize(64)
