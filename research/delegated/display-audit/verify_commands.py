#!/usr/bin/env python3
"""Verify the decoded lithium panel command streams are lossless.

For every panel-*.json next to this script (or given as arguments), rebuild
each stream from its parsed packets and require it to equal the recorded
original bytes. Header layout (downstream struct dsi_ctrl_hdr):

    dtype u8, last u8, vc u8, ack u8, wait u8 (ms), dlen u16 big-endian, payload[dlen]

Also checks dlen against the payload, packet offsets, the recorded SHA-256 and
batch boundaries. Exits non-zero on any mismatch. Standard library only.
"""
import glob
import hashlib
import json
import os
import sys


def rebuild(packets):
    out = bytearray()
    for p in packets:
        payload = bytes.fromhex(p["payload_hex"])
        if len(payload) != p["dlen"]:
            raise ValueError("packet %d: dlen %d != payload length %d"
                             % (p["index"], p["dlen"], len(payload)))
        for field in ("dtype", "last", "vc", "ack", "wait_ms"):
            if not 0 <= p[field] <= 0xFF:
                raise ValueError("packet %d: %s out of u8 range" % (p["index"], field))
        if not 0 <= p["dlen"] <= 0xFFFF:
            raise ValueError("packet %d: dlen out of u16 range" % p["index"])
        if p["byte_offset"] != len(out):
            raise ValueError("packet %d: byte_offset %d != %d"
                             % (p["index"], p["byte_offset"], len(out)))
        header = bytes([p["dtype"], p["last"], p["vc"], p["ack"], p["wait_ms"],
                        p["dlen"] >> 8, p["dlen"] & 0xFF])
        if header.hex(" ") != p["header_hex"]:
            raise ValueError("packet %d: header_hex disagrees with fields" % p["index"])
        out += header + payload
    return bytes(out)


def check_batches(stream):
    expect, start = [], 0
    for p in stream["packets"]:
        if p["last"]:
            expect.append([start, p["index"]])
            start = p["index"] + 1
    got = [b["packets"] for b in stream["batches"]]
    if got != expect:
        raise ValueError("batch boundaries do not follow the last flags")
    if start != len(stream["packets"]):
        raise ValueError("stream ends without last=1")


def main(argv):
    here = os.path.dirname(os.path.abspath(__file__))
    files = argv or sorted(glob.glob(os.path.join(here, "panel-*.json")))
    if not files:
        print("no panel-*.json files found", file=sys.stderr)
        return 2
    failures = total = 0
    for path in files:
        with open(path) as f:
            panel = json.load(f)
        for sid, stream in panel["streams"].items():
            total += 1
            label = "%s:%s" % (os.path.basename(path), sid)
            try:
                original = bytes.fromhex(stream["original_hex"])
                if len(original) != stream["byte_length"]:
                    raise ValueError("byte_length mismatch")
                if hashlib.sha256(original).hexdigest() != stream["sha256"]:
                    raise ValueError("sha256 mismatch")
                if len(stream["packets"]) != stream["packet_count"]:
                    raise ValueError("packet_count mismatch")
                rebuilt = rebuild(stream["packets"])
                if rebuilt != original:
                    raise ValueError("reconstruction differs from original stream")
                check_batches(stream)
            except (ValueError, KeyError) as e:
                failures += 1
                print("FAIL %s: %s" % (label, e))
                continue
            print("ok   %s: %d bytes, %d packets, %d batches, sha256 %s"
                  % (label, len(original), stream["packet_count"],
                     len(stream["batches"]), stream["sha256"][:16]))
    print("%d/%d streams verified" % (total - failures, total))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
