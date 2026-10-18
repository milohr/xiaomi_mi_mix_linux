# Session handoff — Phase 3 next

## Current state

Complete stock V11.0.2.0.OAHMIXM archive obtained from Xiaomi cdnorg endpoint,
hashed and gzip-validated. Stock boot/recovery extracted and unpacked, matching
kernel version and partition sizes checked. See PHASE1_FINDINGS.md and
research/stock-image-audit.json. Earlier download blockers are resolved.

Fastboot round trip already succeeded and returned to Android. User states no
personal data needs backup. No firmware writes, unlocks or vendor flash scripts.

## Phase 1 completed

User confirmed physical recovery-menu entry and successful Reboot to System.
No recovery name/version was visible; both remain unknown. Evidence is explicitly
user-reported in research/recovery-baseline.json. All P1 completion gates passed.
Actual restoration flashing and temporary-image boot have not been tested.
Physical Fastboot key entry remains untested; the successful Fastboot round trip
used ADB entry. Do not describe the menu test as a tested firmware restoration.

## Next phase: P3

Phase 2 is complete. Begin the clean Linux hardware map and minimal original DTS
against the pinned MSM8996 kernel. Phase completion does not authorize flashing.

## Tooling

scripts/download_stock_ranges.py completed 430 validated ranges from cdnorg.
scripts/audit_stock.py validates archive and extracts selected inputs offline.
The audit also validates XML/live-size agreement and the contiguous 20-DTB tail.
Artifacts live under artifacts/stock and remain untracked. Do not execute any
extracted vendor script. The concrete restore procedure is documentation only.

## Phase 2 completed

Pinned pmaports, pmbootstrap, MSM8996 kernel, upstream Linux, lk2nd and LineageOS
evidence revisions in `research/source-lock.json`. Current pmaports carries
scorpio in testing and a v6.19.5 MSM8996 kernel package. Scorpio packaging is a
useful structural reference but its board-id, screen, touch and panel differ.

Current lk2nd includes `lk2nd-msm8996`; the project patch now adds lithium using
stock-verified board-id 38, MSM8996 v3/Pro and PMI8996 values. A real
`arm-none-eabi-gcc` build succeeded. The 372,752-byte image and decoded DTB are
recorded in `research/lk2nd-build.json`. No device write occurred.

Stock aboot static strings expose no registered `boot` command, so direct stock
`fastboot boot` is not assumed. Next: author and validate the minimal
pinned-kernel lithium DTS. See `docs/PHASE2_FINDINGS.md`.
