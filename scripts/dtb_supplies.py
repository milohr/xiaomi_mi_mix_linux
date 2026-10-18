#!/usr/bin/env python3
"""Resolve the *-supply and *-gpio(s) phandles of downstream DTB nodes.

Read-only, offline evidence helper for the hardware map. For every node whose
path contains one of the given substrings, prints each supply with the
regulator node path, regulator-name and voltage limits, and each GPIO
property with its controller path and raw cells.
Usage: dtb_supplies.py DTB PATH_SUBSTRING [PATH_SUBSTRING ...]
Needs pylibfdt (artifacts/toolchain/venv-lmdpdg).
"""
import struct
import sys

import libfdt


def walk(fdt, offset=0, path=""):
    yield offset, path or "/"
    child = fdt.first_subnode(offset, quiet=(libfdt.NOTFOUND,))
    while child >= 0:
        yield from walk(fdt, child, f"{path}/{fdt.get_name(child)}")
        child = fdt.next_subnode(child, quiet=(libfdt.NOTFOUND,))


def prop(fdt, offset, name):
    try:
        return fdt.getprop(offset, name)
    except libfdt.FdtException:
        return None


def u32s(raw):
    return list(struct.unpack(f">{len(raw) // 4}I", bytes(raw)))


def text(raw):
    return bytes(raw).rstrip(b"\0").decode(errors="replace") if raw is not None else None


def main():
    fdt = libfdt.Fdt(open(sys.argv[1], "rb").read())
    nodes = list(walk(fdt))
    by_phandle = {}
    for off, path in nodes:
        ph = prop(fdt, off, "phandle") or prop(fdt, off, "linux,phandle")
        if ph is not None:
            by_phandle[u32s(ph)[0]] = (off, path)

    def describe(ph):
        if ph not in by_phandle:
            return f"<phandle {ph:#x} unresolved>"
        off, path = by_phandle[ph]
        bits = [path]
        for key in ("regulator-name", "qcom,init-voltage", "regulator-min-microvolt",
                    "regulator-max-microvolt", "parent-supply", "status"):
            raw = prop(fdt, off, key)
            if raw is None:
                continue
            if key in ("regulator-name", "status"):
                bits.append(f"{key}={text(raw)}")
            elif key == "parent-supply":
                bits.append(f"parent={by_phandle.get(u32s(raw)[0], (0, '?'))[1]}")
            else:
                bits.append(f"{key}={u32s(raw)[0]}")
        return "  ".join(bits)

    for off, path in nodes:
        if not any(s in path for s in sys.argv[2:]):
            continue
        status = text(prop(fdt, off, "status"))
        print(f"{path}  status={status}")
        poff = fdt.first_property_offset(off, quiet=(libfdt.NOTFOUND,))
        while poff >= 0:
            p = fdt.get_property_by_offset(poff)
            if p.name.endswith("-supply"):
                print(f"  {p.name}: {describe(u32s(p)[0])}")
            elif p.name.endswith("-gpio") or p.name.endswith("-gpios") or p.name == "gpios":
                cells = u32s(p)
                print(f"  {p.name}: {by_phandle.get(cells[0], (0, '?'))[1]} {cells[1:]}")
            poff = fdt.next_property_offset(poff, quiet=(libfdt.NOTFOUND,))


if __name__ == "__main__":
    main()
