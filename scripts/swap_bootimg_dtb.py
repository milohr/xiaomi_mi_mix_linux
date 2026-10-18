#!/usr/bin/env python3
"""Replace the DTB appended to the kernel of an Android v0 boot image.

For a DTB-only change between full package builds: the gzip kernel, the ramdisk,
the second stage and the command line stay byte-identical; only the appended
FDT, the kernel size, the payload layout and the header id change. Read-only on
the inputs; writes OUT only, then checks that the new image's kernel is the old
gzip stream followed by exactly NEW_DTB.
Usage: swap_bootimg_dtb.py BOOT_IMG NEW_DTB OUT_IMG
"""
import hashlib
import struct
import sys
import zlib

FDT_MAGIC = b"\xd0\x0d\xfe\xed"


def parse(image):
    if image[:8] != b"ANDROID!" or struct.unpack_from("<I", image, 40)[0] != 0:
        sys.exit("error: not an Android boot image header v0")
    k_size, k_addr, r_size, r_addr, s_size, s_addr, tags, page = struct.unpack_from("<8I", image, 8)
    align = lambda n: (n + page - 1) // page * page
    k_off = page
    r_off = k_off + align(k_size)
    s_off = r_off + align(r_size)
    return {"page": page, "kernel": image[k_off:k_off + k_size], "ramdisk": image[r_off:r_off + r_size],
            "second": image[s_off:s_off + s_size]}


def split_kernel(kernel):
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    d.decompress(kernel)
    tail = d.unused_data
    if tail[:4] != FDT_MAGIC or struct.unpack_from(">I", tail, 4)[0] != len(tail):
        sys.exit("error: the kernel is not a gzip stream followed by exactly one FDT")
    return kernel[:len(kernel) - len(tail)], tail


def main():
    src, dtb_path, out = sys.argv[1:4]
    image = open(src, "rb").read()
    new_dtb = open(dtb_path, "rb").read()
    if new_dtb[:4] != FDT_MAGIC or struct.unpack_from(">I", new_dtb, 4)[0] != len(new_dtb):
        sys.exit("error: NEW_DTB is not a single FDT blob")
    parts = parse(image)
    gz, old_dtb = split_kernel(parts["kernel"])
    kernel = gz + new_dtb
    page = parts["page"]
    pad = lambda b: b + b"\0" * ((-len(b)) % page)

    header = bytearray(image[:page])
    struct.pack_into("<I", header, 8, len(kernel))
    # v0 id (mkbootimg): SHA-1 over each payload and its size, then the 20 bytes into id[0:20]
    sha = hashlib.sha1()
    for blob in (kernel, parts["ramdisk"], parts["second"]):
        sha.update(blob)
        sha.update(struct.pack("<I", len(blob)))
    header[576:608] = sha.digest().ljust(32, b"\0")
    new = bytes(header) + pad(kernel) + pad(parts["ramdisk"]) + (pad(parts["second"]) if parts["second"] else b"")

    check = parse(new)
    gz2, dtb2 = split_kernel(check["kernel"])
    assert gz2 == gz and dtb2 == new_dtb and check["ramdisk"] == parts["ramdisk"], "round trip failed"
    assert new[64:64 + 512] == image[64:64 + 512], "command line changed"
    open(out, "wb").write(new)
    print(f"old dtb {len(old_dtb)} bytes sha256 {hashlib.sha256(old_dtb).hexdigest()}")
    print(f"new dtb {len(new_dtb)} bytes sha256 {hashlib.sha256(new_dtb).hexdigest()}")
    print(f"input  sha256 {hashlib.sha256(image).hexdigest()}  {src}")
    print(f"output sha256 {hashlib.sha256(new).hexdigest()}  {out}  ({len(new)} bytes)")


if __name__ == "__main__":
    main()
