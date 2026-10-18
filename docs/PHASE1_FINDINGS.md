# Phase 1 — recovery baseline

## Status

**Phase 1 is complete.** Stock-artifact acquisition, integrity verification,
image inspection, live partition comparison and a scoped restoration procedure
are complete. The Fastboot round trip succeeded. The user confirmed physical
recovery-menu entry and a successful Reboot to System. No recovery name/version
was visible, so the implementation remains unidentified.
No personal-data backup is required according to the user.

## Exact stock baseline

- Device: lithium; installed and archive build: V11.0.2.0.OAHMIXM.
- Archive metadata: userdata_version=20191023.0000.00.
- Source: Xiaomi cdnorg.d.miui.com HTTPS, exact filename in the JSON manifest.
- Archive size: 1803158296 bytes; full gzip CRC/length validation passed.
- Archive SHA-256: `713f8f6f4f65fc51cfb206e0606ae5af946a1baf344277c761530c13bb207b7d`.
- All 74 tar entries inventoried; only selected research inputs extracted.
- Local digests establish repeatable artifact identity; no independently
  published cryptographic signature was verified.

## Image and layout findings

| Property | Boot | Recovery |
|---|---|---|
| Image bytes | 24646986 | 29406542 |
| Partition bytes | 67108864 | 67108864 |
| Live node | /dev/block/sde36 | /dev/block/sda13 |
| Header version | 0 | 0 |
| Page size | 4096 | 4096 |
| Kernel bytes | 22170167 | 22170167 |
| Ramdisk bytes | 2466412 | 7227719 |
| Kernel load address | 0x80008000 | 0x80008000 |
| Ramdisk load address | 0x81000000 | 0x81000000 |
| Tags address | 0x80000100 | 0x80000100 |

Archive rawprogram XML sizes agree with live ADB and stock Fastboot. Vendor
flashing scripts check Fastboot product MSM8996_A8, matching the device. These
scripts were read as evidence and never executed.

Both images contain kernel 3.18.71-perf-g5edcf86 built October 23, 2019, matching
live uname. The kernel component consists of 12649678 gzip bytes followed by
20 contiguous DTBs totaling 9520489 bytes. DTB selection remains later work;
none is assumed to be the correct runtime board variant merely by its position.
Original DTBs are retained as evidence, not copied into an upstream tree.

## Recovery procedure and coverage

See [RESTORE_PROCEDURE.md](RESTORE_PROCEDURE.md) for scoped boot-only recovery.
Stock recovery is preserved. The Fastboot product and unlock state were read,
then Android returned with sys.boot_completed=1. That verifies communications,
not actual flashing or temporary-image boot. EDL remains unverified.

## Audit records

- [Image audit](../research/stock-image-audit.json): image hashes, headers,
  cmdlines, DTB offsets, metadata and partition comparison.
- [Recovery baseline](../research/recovery-baseline.json): live test and gates.
- [Partition inventory](../research/partition-inventory.json): full live map.

Host-only scripts: download_stock_ranges.py and audit_stock.py. Proprietary
artifacts and raw logs remain ignored by Git. No partition writes occurred.
