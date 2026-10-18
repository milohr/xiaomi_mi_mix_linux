#!/usr/bin/env python3
"""Check that every local source of an APKBUILD matches its sha512sums entry.

Remote sources (URLs) are skipped; abuild verifies them after download.
Exits 1 on a mismatch, a missing file, or a local source without a checksum.
Usage: verify_apkbuild_checksums.py PACKAGE_DIR [PACKAGE_DIR ...]
"""
import hashlib
import re
import sys
from pathlib import Path


def block(text, name):
    m = re.search(rf'^{name}="(.*?)"', text, re.S | re.M)
    return m.group(1).split() if m else []


def main():
    bad = 0
    for pkg in map(Path, sys.argv[1:]):
        text = (pkg / "APKBUILD").read_text()
        sums = block(text, "sha512sums")
        recorded = dict(zip(sums[1::2], sums[0::2]))
        for src in block(text, "source"):
            if "://" in src or "::" in src or "$url" in src:
                continue
            name = src.replace("$_flavor", "postmarketos-qcom-msm8996").replace("$arch", "aarch64")
            path = pkg / name
            if not path.exists():
                print(f"MISSING  {pkg.name}/{name}")
                bad += 1
            elif hashlib.sha512(path.read_bytes()).hexdigest() != recorded.get(name):
                print(f"MISMATCH {pkg.name}/{name}")
                bad += 1
            else:
                print(f"ok       {pkg.name}/{name}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
