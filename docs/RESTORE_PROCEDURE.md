# Scoped recovery procedure — lithium

This procedure concerns recovery from a later **boot-partition-only experiment**.
It is documentation, not authorization to flash. It does not cover damaged GPT,
primary bootloaders, modem calibration or arbitrary partition modifications.

## Required local evidence

- `research/stock-image-audit.json`: complete-archive hash, gzip validation and
  exact stock boot/recovery image hashes, lengths and header fields.
- `research/partition-inventory.json`: live mapping and sizes.
- `research/recovery-baseline.json`: current build and tested bootloader access.
- Installed stock build must remain V11.0.2.0.OAHMIXM or this baseline must be
  reassessed. Preserve the original firmware configuration during experiments.

## Recovery after a boot-only experiment

1. Enter stock Fastboot using the verified physical key path. Connect USB to
   this Linux host. Select the already-identified device explicitly by serial.
2. Check identity against the ADB identity and the tested stock Fastboot product
   `MSM8996_A8`; that product string alone is not unique proof of lithium.
3. Verify SHA-256 of `artifacts/stock/audit/boot.img` against the audit JSON.
   Verify the boot partition is still 0x4000000 bytes and the image fits.
4. After explicit approval for restoration, write **only** the known stock boot
   image to the stock bootloader's `boot` partition, then reboot to Android.
5. Confirm ADB identifies lithium, `sys.boot_completed=1`, and the stock build.

The eventual stock-Fastboot command is `fastboot -s SERIAL flash boot IMAGE`.
Do not execute it in lk2nd: lk2nd may apply a boot-partition offset. This project
has not installed lk2nd. Do not use `flash_all`, `flash_all_lock`, relock commands,
GPT writes or a sibling-device image. Boot-only restoration avoids unnecessary
changes to the remaining working stock system.

## Separate recovery partition

Stock recovery is distinct from boot on this device. Preserve it during Linux
bring-up. If an explicitly authorized experiment ever changes recovery, review
its separate restoration using the matched stock `recovery.img`. A recovery menu
boot test does not test actual partition flashing or guarantee all future restores.

## Coverage limits

A successful Fastboot round trip validates communications and return to stock
Android. It does not demonstrate temporary-image boot, flashing reliability,
Linux kernel compatibility or EDL availability. No restoration write has been
performed during Phase 1. A full ROM is retained for offline reference; generic
full-ROM flashing is not part of the approved plan.
