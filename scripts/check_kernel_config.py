#!/usr/bin/env python3
"""Compare kernel/lithium.config with a full kernel .config.

Prints, per fragment option, the value in the target config: "ok" when equal,
"module" when the fragment wants y and the target builds it as m (fine with
the postmarketOS initramfs, listed for review), "MISSING" otherwise.
Exits 1 only on MISSING or a different value.
Usage: check_kernel_config.py FRAGMENT TARGET_CONFIG
"""
import re
import sys


def parse(path):
    values = {}
    for line in open(path):
        m = re.match(r"(CONFIG_\w+)=(.*)", line.strip())
        if m:
            values[m.group(1)] = m.group(2)
            continue
        m = re.match(r"# (CONFIG_\w+) is not set", line.strip())
        if m:
            values[m.group(1)] = "n"
    return values


def main():
    wanted, target = parse(sys.argv[1]), parse(sys.argv[2])
    bad = 0
    for key, want in wanted.items():
        have = target.get(key, "n")
        if have == want:
            state = "ok"
        elif want == "y" and have == "m":
            state = "module"
        else:
            state = "MISSING"
            bad += 1
        print(f"{state:8} {key}={want} (target: {have})")
    print(f"{len(wanted) - bad}/{len(wanted)} satisfied")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
