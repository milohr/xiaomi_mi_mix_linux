#!/usr/bin/env python3
"""Assemble the lithium FTE716 panel driver draft from lmdpdg output.

The init/off command bodies are copied verbatim from lmdpdg --dumb-dcs output
generated from stock boot.img.dtb-5; only the surrounding driver is original.
Usage: assemble_panel_draft.py LMDPDG_OUT_DIR TEMPLATE OUTPUT
"""
import re
import sys
from pathlib import Path

VARIANTS = {
    "sharp": "sharp_fte716_1080p_video/panel-sharp-fte716.c",
    "auo": "auo_fte716_1080p_video/panel-auo-fte716.c",
}


def body(src: str, prefix: str, fn: str) -> str:
    m = re.search(rf"static int {prefix}_{fn}\(struct {prefix} \*ctx\)\n\{{\n(.*?)\n\}}\n",
                  src, re.S)
    if not m:
        sys.exit(f"error: {prefix}_{fn} not found")
    return m.group(1)


def main() -> None:
    out_dir, template, output = map(Path, sys.argv[1:4])
    text = template.read_text()
    for variant, rel in VARIANTS.items():
        src = (out_dir / rel).read_text()
        prefix = f"{variant}_fte716"
        for fn in ("on", "off"):
            text = text.replace(f"@{variant.upper()}_{fn.upper()}@", body(src, prefix, fn))
    if "@" in re.sub(r"<[^>]*@[^>]*>", "", text):
        sys.exit("error: unreplaced placeholder")
    output.write_text(text)


if __name__ == "__main__":
    main()
