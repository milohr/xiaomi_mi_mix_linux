#!/usr/bin/env python3
"""Audit an Android v0 boot image against lithium's deviceinfo and stock layout.

Checks the header (magic, version 0, page size, load addresses = base +
offsets), the command line, the kernel payload (gzip Image followed by an
appended FDT whose compatible starts with xiaomi,lithium), and the size
limit of the 64 MiB boot/recovery partitions. Read-only.
Usage: audit_bootimg.py BOOT_IMG DEVICEINFO
"""
import re
import struct
import sys
import zlib

PARTITION_BYTES = 67108864          # boot and recovery, research/partition-inventory.json
FDT_MAGIC = b"\xd0\x0d\xfe\xed"

failures = 0


def check(ok, label, detail=""):
    global failures
    failures += 0 if ok else 1
    print(f"{'ok  ' if ok else 'FAIL'} {label}{': ' + detail if detail else ''}")


def deviceinfo(path):
    values = {}
    for line in open(path):
        m = re.match(r'(deviceinfo_\w+)="(.*)"', line.strip())
        if m:
            values[m.group(1)] = m.group(2)
    return values


def main():
    image = open(sys.argv[1], "rb").read()
    info = deviceinfo(sys.argv[2])
    base = int(info["deviceinfo_flash_offset_base"], 16)
    page = int(info["deviceinfo_flash_pagesize"])

    check(image[:8] == b"ANDROID!", "magic ANDROID!")
    (kernel_size, kernel_addr, ramdisk_size, ramdisk_addr, second_size, second_addr,
     tags_addr, page_size, header_version, _os_version) = struct.unpack_from("<10I", image, 8)
    cmdline = image[64:64 + 512].split(b"\0")[0].decode()
    check(header_version == 0, "header version 0", str(header_version))
    check(page_size == page, "page size", str(page_size))
    for name, addr, key in (("kernel", kernel_addr, "kernel"), ("ramdisk", ramdisk_addr, "ramdisk"),
                            ("second", second_addr, "second"), ("tags", tags_addr, "tags")):
        want = base + int(info[f"deviceinfo_flash_offset_{key}"], 16)
        check(addr == want, f"{name} address", f"{addr:#x} (want {want:#x})")
    for arg in info.get("deviceinfo_kernel_cmdline", "").split():
        check(arg in cmdline.split(), f"cmdline has {arg}", repr(cmdline))

    kernel = image[page:page + kernel_size]
    check(kernel[:2] == b"\x1f\x8b", "kernel payload is gzip")
    decomp = zlib.decompressobj(16 + zlib.MAX_WBITS)
    raw = decomp.decompress(kernel)
    tail = decomp.unused_data
    check(raw[56:60] == b"ARMd", "gzip holds an arm64 Image", f"{len(raw)} bytes")
    check(tail[:4] == FDT_MAGIC, "FDT appended after Image.gz", f"{len(tail)} bytes")
    if tail[:4] == FDT_MAGIC:
        fdt_size = struct.unpack_from(">I", tail, 4)[0]
        check(fdt_size == len(tail), "exactly one appended FDT", f"{fdt_size} bytes")
        check(b"xiaomi,lithium\0" in tail[:fdt_size], "appended FDT is lithium's")
    check(ramdisk_size > 0, "ramdisk present", f"{ramdisk_size} bytes")
    check(second_size == 0, "no second stage")
    check(len(image) <= PARTITION_BYTES, "fits the 64 MiB boot/recovery partition",
          f"{len(image)} bytes, {100 * len(image) / PARTITION_BYTES:.1f}%")

    print("all checks passed" if not failures else f"{failures} check(s) failed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
