#!/usr/bin/env python3
"""Render the real demo canvas to a README image (optional dependency: Pillow)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", type=Path, required=True, help="path to a monospace TTF font")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/assets/preview.png")
    args = parser.parse_args()
    from PIL import Image, ImageDraw, ImageFont

    from cpp_tree.app import App
    from cpp_tree.models import Options
    from cpp_tree.storage import Store
    from cpp_tree.theme import PALETTE

    app = App(Store(Path("unused-demo.json"), demo=True), Options(Path("unused-demo.json")))
    app.jump_to_quest()
    app.toast = ""
    frame = app.render(132, 44)
    font = ImageFont.truetype(str(args.font), 18)
    cell_w, cell_h, pad = round(font.getlength("M")), 26, 22
    image = Image.new("RGB", (frame.w * cell_w + pad * 2, frame.h * cell_h + pad * 2), "#0c111b")
    draw = ImageDraw.Draw(image)
    for y, row in enumerate(frame.cells):
        for x, (char, style) in enumerate(row):
            fg, bg, bold = PALETTE[style]
            xx, yy = pad + x * cell_w, pad + y * cell_h
            draw.rectangle((xx, yy, xx + cell_w - 1, yy + cell_h - 1), fill=bg)
            draw.text((xx, yy + 1), char, font=font, fill=fg, stroke_width=0)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, optimize=True)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
