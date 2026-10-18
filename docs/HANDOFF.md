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

## Display track (parallel to P3, prepares P6) — 2026-10-17

Separate session; touched no Phase 3 file (`kernel/msm8996pro-xiaomi-lithium.dts`,
`kernel/patches/`, `artifacts/build/kernel-phase3`) and did not rebuild the
reviewed Phase 2 lk2nd image (`b845d9b6…`, re-hashed, unchanged). No device writes;
only read-only ADB `getprop`/sysfs reads. Full status: [DISPLAY.md](DISPLAY.md).

- **Display audit**: complete and hash-verified; see
  `research/delegated/display-audit/HANDOFF.md`. It now feeds the items below.
- **Panel driver draft**: `kernel/panel-draft/`, Sharp and AUO in one driver,
  compile-tested `W=1` clean against the pinned kernel, checkpatch clean, and every
  packet checked against stock (`scripts/verify_panel_draft.py`). Rebuild with
  `scripts/build_panel_draft.sh`. Hashes are in `research/display-draft-build.json`.
- **lk2nd `0002` (draft)**: maps the stock `mdss_mdp.panel=` name to a Linux panel
  compatible. It builds and has its own image hash, and it isn't part of the reviewed
  Phase 2 image. Decide at P5 review whether to include it.

**For the Phase 3 owner:** the pinned lk2nd image already contains
cont-splash + `lk2nd.pass-simplefb`, which writes a measured simple-framebuffer
node into the Linux DTB at boot. So the minimal DTS needs **no** hard-coded
simplefb. Keep `cont_splash_mem`/`dfps_data_mem` reserved and leave TLMM
8/10/40/47/48, L14 and LAB/IBB untouched. Also note: the working-copy
`kernel/msm8996pro-xiaomi-lithium.dts` (includes `msm8996-xiaomi-common.dtsi`,
disables MDSS/GPU/PILs, no UART enable) differs from
`kernel/patches/0001-…patch`, which is what `kernel-dtb-build.json` records.
Reconcile them before the next DTB build.

New ignored host tools: `artifacts/toolchain/lld/bin/ld.lld` (wrapper),
`artifacts/toolchain/bc/usr/bin/bc`, `artifacts/toolchain/venv-lmdpdg`,
and `sources/lmdpdg` (pinned). A separate kernel `O=` tree is at `artifacts/build/kernel-panel`.
