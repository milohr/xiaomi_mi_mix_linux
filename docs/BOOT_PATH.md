# Lithium boot-path decision

Status: **offline implementation built; live validation pending**.

The first-stage experiment will preserve Android's stock boot partition:

1. Build a custom `lk2nd-msm8996` image containing a lithium board entry matched
   to stock board/SoC/PMIC IDs.
2. Review and hash the image, confirm it fits the 64 MiB recovery partition, and
   present exact restoration commands before asking for authorization.
3. Place lk2nd in the recovery partition only after authorization, then enter it
   with the already-tested physical recovery key path.
4. Use lk2nd Fastboot to load the Linux test image into RAM and retrieve logs.
5. Keep stock Android in `boot`; restore the exact hashed stock recovery image if
   lk2nd does not start or when the experiment ends.

The existing scorpio lk2nd DTB is not compatible with lithium. The stock Xiaomi
Fastboot implementation does not expose evidence of a `boot` command, so direct
temporary boot through stock Fastboot is not the selected assumption. Actual
flash and restore operations remain untested and require a separately reviewed,
concrete procedure.

The exact stock recovery baseline and recovery limitations are documented in
[RESTORE_PROCEDURE.md](RESTORE_PROCEDURE.md) and
[recovery-baseline.json](../research/recovery-baseline.json).

The reviewed build evidence and exact hashes are in
[lk2nd-build.json](../research/lk2nd-build.json). No device write has occurred.
