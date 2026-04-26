#!/usr/bin/env python3
"""Generate simple SVG chess pieces for missing files."""
from pathlib import Path

svg_dir = Path(__file__).parent / "assets" / "svg"
svg_dir.mkdir(parents=True, exist_ok=True)

# Simple SVG pieces (geometric shapes representing each piece type)
PIECES_SVG = {
    "w_k": '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="60" r="35" fill="white" stroke="black" stroke-width="2"/>
  <rect x="45" y="15" width="10" height="35" fill="white" stroke="black" stroke-width="2"/>
  <polygon points="50,10 55,20 45,20" fill="white" stroke="black" stroke-width="2"/>
</svg>''',
    "w_q": '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="60" r="35" fill="white" stroke="black" stroke-width="2"/>
  <circle cx="30" cy="25" r="8" fill="white" stroke="black" stroke-width="2"/>
  <circle cx="50" cy="15" r="8" fill="white" stroke="black" stroke-width="2"/>
  <circle cx="70" cy="25" r="8" fill="white" stroke="black" stroke-width="2"/>
</svg>''',
    "w_r": '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <rect x="20" y="50" width="60" height="35" fill="white" stroke="black" stroke-width="2"/>
  <rect x="25" y="25" width="12" height="25" fill="white" stroke="black" stroke-width="2"/>
  <rect x="50" y="25" width="12" height="25" fill="white" stroke="black" stroke-width="2"/>
  <rect x="63" y="25" width="12" height="25" fill="white" stroke="black" stroke-width="2"/>
</svg>''',
    "w_b": '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="65" r="30" fill="white" stroke="black" stroke-width="2"/>
  <circle cx="50" cy="30" r="20" fill="white" stroke="black" stroke-width="2"/>
  <circle cx="50" cy="15" r="6" fill="white" stroke="black" stroke-width="2"/>
</svg>''',
    "w_n": '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <path d="M 50 25 Q 65 30 70 50 Q 65 65 50 70 Q 35 65 30 50 Q 35 30 50 25 Z" fill="white" stroke="black" stroke-width="2"/>
  <path d="M 55 35 Q 60 40 58 50" fill="none" stroke="black" stroke-width="2"/>
</svg>''',
    "w_p": '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="65" r="25" fill="white" stroke="black" stroke-width="2"/>
  <circle cx="50" cy="35" r="15" fill="white" stroke="black" stroke-width="2"/>
</svg>''',
    "b_k": '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="60" r="35" fill="black" stroke="white" stroke-width="2"/>
  <rect x="45" y="15" width="10" height="35" fill="black" stroke="white" stroke-width="2"/>
  <polygon points="50,10 55,20 45,20" fill="black" stroke="white" stroke-width="2"/>
</svg>''',
    "b_q": '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="60" r="35" fill="black" stroke="white" stroke-width="2"/>
  <circle cx="30" cy="25" r="8" fill="black" stroke="white" stroke-width="2"/>
  <circle cx="50" cy="15" r="8" fill="black" stroke="white" stroke-width="2"/>
  <circle cx="70" cy="25" r="8" fill="black" stroke="white" stroke-width="2"/>
</svg>''',
    "b_r": '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <rect x="20" y="50" width="60" height="35" fill="black" stroke="white" stroke-width="2"/>
  <rect x="25" y="25" width="12" height="25" fill="black" stroke="white" stroke-width="2"/>
  <rect x="50" y="25" width="12" height="25" fill="black" stroke="white" stroke-width="2"/>
  <rect x="63" y="25" width="12" height="25" fill="black" stroke="white" stroke-width="2"/>
</svg>''',
    "b_b": '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="65" r="30" fill="black" stroke="white" stroke-width="2"/>
  <circle cx="50" cy="30" r="20" fill="black" stroke="white" stroke-width="2"/>
  <circle cx="50" cy="15" r="6" fill="black" stroke="white" stroke-width="2"/>
</svg>''',
    "b_n": '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <path d="M 50 25 Q 65 30 70 50 Q 65 65 50 70 Q 35 65 30 50 Q 35 30 50 25 Z" fill="black" stroke="white" stroke-width="2"/>
  <path d="M 55 35 Q 60 40 58 50" fill="none" stroke="white" stroke-width="2"/>
</svg>''',
    "b_p": '''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="65" r="25" fill="black" stroke="white" stroke-width="2"/>
  <circle cx="50" cy="35" r="15" fill="black" stroke="white" stroke-width="2"/>
</svg>''',
}

print("Generating SVG chess pieces...")
for name, svg_content in PIECES_SVG.items():
    svg_path = svg_dir / f"{name}.svg"
    svg_path.write_text(svg_content)
    print(f"  Created {name}.svg")

print(f"\nDone! Generated {len(PIECES_SVG)} pieces in {svg_dir}")
print(f"Total pieces: {len(list(svg_dir.glob('*.svg')))}")
