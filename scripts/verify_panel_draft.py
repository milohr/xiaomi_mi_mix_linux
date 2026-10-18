#!/usr/bin/env python3
"""Check the FTE716 panel driver draft against the audited stock streams.

Rebuilds each variant's on/off packet list from the driver C source and
compares it, packet by packet, with the decoded stock DTB streams in
research/delegated/display-audit/panel-*.json: payload bytes, DCS versus
generic class, and the wait after each packet. Reports, but does not fail
on, the known 2-byte generic long (0x29) -> short (0x23) type change.
Zero-padded 0-parameter DCS short writes (0x05 "11 00") are compared as
the single command byte, which is the same packet on the wire.
Usage: verify_panel_draft.py [DRIVER_C]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT = ROOT / "research/delegated/display-audit"
DRIVER = ROOT / "kernel/panel-draft/panel-xiaomi-lithium-fte716.c"

HELPERS = {
    "mipi_dsi_dcs_exit_sleep_mode_multi": [0x11],
    "mipi_dsi_dcs_enter_sleep_mode_multi": [0x10],
    "mipi_dsi_dcs_set_display_on_multi": [0x29],
    "mipi_dsi_dcs_set_display_off_multi": [0x28],
}
DCS_TYPES = {0x05, 0x15, 0x39}
GENERIC_TYPES = {0x03, 0x13, 0x23, 0x29}


def function_body(src, name):
    m = re.search(rf"static int {name}\(struct fte716 \*ctx\)\n\{{\n(.*?)\n\}}\n", src, re.S)
    if not m:
        sys.exit(f"error: {name} not found")
    return m.group(1)


def driver_packets(body):
    packets = []
    for call in re.finditer(r"(mipi_dsi_\w+)\(&dsi_ctx(.*?)\);", body, re.S):
        fn, args = call.group(1), call.group(2)
        values = [int(v, 16) for v in re.findall(r"0x[0-9a-fA-F]+", args)]
        if fn == "mipi_dsi_msleep":
            packets[-1]["wait"] += int(args.strip(", "))
        elif fn == "mipi_dsi_generic_write_seq_multi":
            packets.append({"class": "generic", "payload": values, "wait": 0})
        elif fn == "mipi_dsi_dcs_write_seq_multi":
            packets.append({"class": "dcs", "payload": values, "wait": 0})
        elif fn in HELPERS:
            packets.append({"class": "dcs", "payload": HELPERS[fn], "wait": 0})
        else:
            sys.exit(f"error: unhandled call {fn}")
    return packets


def stock_packets(stream):
    packets = []
    for p in stream["packets"]:
        dtype = p["dtype"]
        if dtype in DCS_TYPES:
            cls = "dcs"
        elif dtype in GENERIC_TYPES:
            cls = "generic"
        else:
            sys.exit(f"error: unexpected dtype {dtype:#x}")
        payload = [int(b, 16) for b in p["payload_hex"].split()]
        # A DCS short write without parameters (0x05) always carries two
        # bytes on the wire; downstream spells the zero pad out, mainline
        # helpers pass the command byte alone. Same packet on the link.
        if dtype == 0x05 and len(payload) == 2 and payload[1] == 0x00:
            payload = payload[:1]
        packets.append({
            "class": cls,
            "payload": payload,
            "wait": p["wait_ms"],
            "dtype": dtype,
        })
    return packets


def stream(audit, key):
    streams = audit["streams"]
    if isinstance(streams, dict):
        return streams[key]
    for s in streams:
        if s["property"] == key:
            return s
    sys.exit(f"error: stream {key} not found")


def compare(label, ours, stock):
    if len(ours) != len(stock):
        print(f"FAIL {label}: {len(ours)} packets, stock has {len(stock)}")
        return False
    type_changes = 0
    for i, (a, b) in enumerate(zip(ours, stock)):
        for field in ("class", "payload", "wait"):
            if a[field] != b[field]:
                print(f"FAIL {label} packet {i}: {field} {a[field]} != stock {b[field]}")
                return False
        if b["dtype"] == 0x29 and len(b["payload"]) == 2:
            type_changes += 1
    print(f"ok   {label}: {len(ours)} packets match stock bytes, class and waits; "
          f"{type_changes} two-byte generic writes go out as 0x23 instead of 0x29")
    return True


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else DRIVER).read_text()
    ok = True
    for variant in ("sharp", "auo"):
        audit = json.loads((AUDIT / f"panel-{variant}-fte716-1080p-video.json").read_text())
        for fn, key in (("on", "on_command"), ("off", "off_command")):
            ours = driver_packets(function_body(src, f"{variant}_fte716_{fn}"))
            ok &= compare(f"{variant} {fn}", ours, stock_packets(stream(audit, key)))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
