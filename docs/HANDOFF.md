# Session handoff — P5 next (awaiting the user's go for Step A)

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

## Phase 3 completed (2026-10-17)

Offline gate passed; see [PHASE3_FINDINGS.md](PHASE3_FINDINGS.md). The DTS no
longer includes `msm8996-xiaomi-common.dtsi`. It enables the console
(`blsp2_uart2`, 0x75b0000, gpio4/5), UFS, USB in peripheral mode on the HS PHY,
six RPM rails at stock voltages, power and volume keys, and the reserved memory
the stock map needs. `scripts/build_lithium_dtb.sh` builds it (`622ba9fa…`,
reproducible), runs the full schema check, and checks it against the stock DTB
(39/39). **Correction:** revision 1 sent the console to 0x7570000, which
lithium's stock disables as a console. Phase completion does not authorize flashing.

## Phase 4 completed (2026-10-18), lint pending

`scripts/pmb_build.sh` built `device-xiaomi-lithium-1-r0` and the shared
`linux-postmarketos-qcom-msm8996` 6.19.5-r1 with patch 0001, installed a console
rootfs and exported to `artifacts/pmb-export` (ignored). `boot.img` (`c2f98e2b…`)
passes `audit_bootimg.py`; its appended DTB is the Phase 3 DTB byte for byte
(`622ba9fa…`). `p5-boot.img` (`af734348…`) adds the four P5 debug arguments and
passes too. The kernel embeds its config (IKCONFIG): 30/30 of `kernel/lithium.config`.
The initramfs has unudhcpd, telnetd and the debug-shell path. Details and every
hash: [PHASE4_FINDINGS.md](PHASE4_FINDINGS.md), `research/pmb-build.json`,
`artifacts/pmb-export/P5_PREP_REPORT.md` (`scripts/p5_prep_check.sh`).
Open: the package lint. Fixed: the export loop's `cp -L` on `dtbs/` (now `cp -rL`).

**Next: P5.** docs/P5_FIRST_BOOT.md is complete. Its Step A (lk2nd into the
recovery partition) is the first device write and needs the user's explicit go.

## Phase 4 plan (done, kept for history)

1. Write `device-xiaomi-lithium` (APKBUILD + deviceinfo) following the pinned
   pmaports conventions. Take boot-image values from the Phase 1/2 audit (v0
   header, page 4096, kernel 0x8000, ramdisk 0x1000000, second 0xf00000, tags
   0x100), the screen size 1080x2040, and the DTB
   `qcom/msm8996pro-xiaomi-lithium.dtb`.
2. Use the shared `linux-postmarketos-qcom-msm8996` package. Phase 3 showed its
   config already satisfies `kernel/lithium.config`. The only kernel change is
   adding the DTB patch.
3. Kernel command line for the first boot should include `lk2nd.pass-simplefb`
   (docs/DISPLAY.md). USB networking is the primary console; UART reachability
   is unknown.
4. The pinned pmaports checkout is `sources/pmaports`. The old `/tmp/lithium-p2-*`
   copies were deleted on 2026-10-17.

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

**(Resolved in Phase 3, kept for history.)** The pinned lk2nd image already contains
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

## Touch track (prepares P6) — 2026-10-18

Touch is described but kept out of the P4 image: `kernel/patches/0002-…touchscreen.patch`
applies on top of 0001 (FTE8716 at 0x38 on blsp2_i2c6, IRQ gpio125 falling,
reset gpio89 active low, L14 1.8 V always-on). Mainline `edt-ft5x06` supports
`focaltech,ft8716`; the shared kernel config lacks `CONFIG_TOUCHSCREEN_EDT_FT5X06`
(`kernel/touch.config`). Offline: schema check adds no warnings,
`scripts/verify_touch_dtb.py` 14/14 against stock. Test it as its own change
after the first P5 boot. Details, evidence and the stale stock `interrupts` trap:
docs/TOUCH.md.

## P5 review packet (drafted 2026-10-18, not authorized)

docs/P5_FIRST_BOOT.md: exact commands, expected behaviour, failure table and
restore for the first boot (lk2nd into recovery, Linux from RAM, stock
recovery back). Read from the pinned sources, now checked out at `sources/lk2nd`
(8b46487c, ignored). Key findings: both volume keys at power-on = EDL; lk2nd
maps boot's first 512 KiB as its own partition even from recovery, so never
flash in lk2nd; the first boot ends in the pmOS debug shell (telnet
172.16.42.1) because no pmOS partition exists. `scripts/make_p5_bootimg.py`
appends `lk2nd.pass-ramoops=zap console=tty0 clk_ignore_unused pd_ignore_unused`
to the audited boot.img; image hashes are filled in after the P4 export.

