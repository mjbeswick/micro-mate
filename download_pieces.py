#!/usr/bin/env python3
"""Download SVG chess pieces from Wikimedia Commons with rate limiting."""
import time
import urllib.request
from pathlib import Path

# Add a User-Agent
opener = urllib.request.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')]
urllib.request.install_opener(opener)

# Corrected Wikimedia URLs for t45 style pieces
PIECES = {
    "w_k": "https://upload.wikimedia.org/wikipedia/commons/6/6f/Chess_klt45.svg",
    "w_q": "https://upload.wikimedia.org/wikipedia/commons/4/47/Chess_qlt45.svg",
    "w_r": "https://upload.wikimedia.org/wikipedia/commons/7/72/Chess_rlt45.svg",
    "w_b": "https://upload.wikimedia.org/wikipedia/commons/b/b1/Chess_blt45.svg",
    "w_n": "https://upload.wikimedia.org/wikipedia/commons/7/78/Chess_nlt45.svg",
    "w_p": "https://upload.wikimedia.org/wikipedia/commons/4/45/Chess_plt45.svg",
    "b_k": "https://upload.wikimedia.org/wikipedia/commons/3/30/Chess_kdt45.svg",
    "b_q": "https://upload.wikimedia.org/wikipedia/commons/4/40/Chess_qdt45.svg",
    "b_r": "https://upload.wikimedia.org/wikipedia/commons/f/ff/Chess_rdt45.svg",
    "b_b": "https://upload.wikimedia.org/wikipedia/commons/9/98/Chess_bdt45.svg",
    "b_n": "https://upload.wikimedia.org/wikipedia/commons/e/ef/Chess_ndt45.svg",
    "b_p": "https://upload.wikimedia.org/wikipedia/commons/c/c7/Chess_pdt45.svg",
}

svg_dir = Path(__file__).parent / "assets" / "svg"
svg_dir.mkdir(parents=True, exist_ok=True)

print("Downloading SVG chess pieces from Wikimedia Commons...")
print("(Adding 2-second delay between requests to avoid rate limiting)\n")

for i, (name, url) in enumerate(PIECES.items(), 1):
    output_path = svg_dir / f"{name}.svg"

    # Skip if already downloaded
    if output_path.exists():
        print(f"  [{i:2d}/12] {name}.svg exists, skipping")
        continue

    try:
        print(f"  [{i:2d}/12] Downloading {name}.svg...", end=" ", flush=True)
        urllib.request.urlretrieve(url, output_path)
        print("✓")

        # Rate limit: wait between requests (except after last one)
        if i < len(PIECES):
            time.sleep(2)

    except Exception as e:
        print(f"✗ Error: {e}")
        # If download failed, remove the partial file
        if output_path.exists():
            output_path.unlink()

print(f"\nDone! Pieces saved to {svg_dir}")
print(f"Total pieces in {svg_dir}: {len(list(svg_dir.glob('*.svg')))}/12")
