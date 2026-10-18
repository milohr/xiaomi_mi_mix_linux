#!/usr/bin/env python3
"""Derive the P5 first-boot image from the pmbootstrap boot.img.

Appends debug arguments to the Android v0 header command line and changes
nothing else: the script checks that every byte outside the 512-byte cmdline
field is identical. The v0 header id is a hash of the payloads, not of the
cmdline, so it stays valid. Read-only on the input; writes OUT only.
Usage: make_p5_bootimg.py BOOT_IMG OUT_IMG ARG [ARG ...]
"""
import hashlib
import sys

CMDLINE_OFF, CMDLINE_LEN = 64, 512   # boot_img_hdr_v0.cmdline


def main():
    src, out, args = sys.argv[1], sys.argv[2], sys.argv[3:]
    image = open(src, "rb").read()
    if image[:8] != b"ANDROID!" or int.from_bytes(image[40:44], "little") != 0:
        sys.exit("error: not an Android boot image header v0")

    field = image[CMDLINE_OFF:CMDLINE_OFF + CMDLINE_LEN]
    old = field.split(b"\0")[0].decode()
    words = old.split()
    for arg in args:
        if arg in words:
            sys.exit(f"error: {arg} is already on the command line")
    new = " ".join(words + args).encode()
    if len(new) >= CMDLINE_LEN:
        sys.exit(f"error: command line would be {len(new)} bytes, the field holds {CMDLINE_LEN - 1}")

    patched = bytearray(image)
    patched[CMDLINE_OFF:CMDLINE_OFF + CMDLINE_LEN] = new.ljust(CMDLINE_LEN, b"\0")
    outside = lambda b: bytes(b[:CMDLINE_OFF]) + bytes(b[CMDLINE_OFF + CMDLINE_LEN:])
    assert outside(patched) == outside(image), "bytes outside the cmdline field changed"

    open(out, "wb").write(patched)
    print(f"old cmdline: {old}")
    print(f"new cmdline: {new.decode()}")
    print(f"input  sha256 {hashlib.sha256(image).hexdigest()}  {src}")
    print(f"output sha256 {hashlib.sha256(patched).hexdigest()}  {out}")


if __name__ == "__main__":
    main()
