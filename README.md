# Xiaomi Mi MIX native Linux port

Target: **original Xiaomi Mi MIX (`lithium`)**, Qualcomm MSM8996 Pro (Snapdragon 821).
**postmarketOS (Alpine) with a mainline Linux 6.19 kernel runs on the phone**, booted by
lk2nd from the `boot` partition, with Plasma Mobile as the user interface.
This repository is independent of the MediaTek Redmi `flare` project.

## Status (2026-10-18)

| Area | State | Notes |
|---|---|---|
| Boot | ✅ | stock bootloader → lk2nd (first 512 KiB of `boot`) → kernel; boots unattended |
| Storage (UFS) | ✅ | rootfs on `userdata` |
| USB networking | ✅ | ssh at `172.16.42.1` (gadget) |
| Display | ✅ | msm DRM + own FTE716 panel driver; brightness (PMI8994 WLED), screen off/on |
| Touch | ✅ | FocalTech FT8716 (edt-ft5x06) |
| Wi-Fi | ✅ | QCA6174 hw3.2 on PCIe, ath10k, lithium board file; 2.4 and 5 GHz |
| Battery / charging | ✅ | PMI8996 fuel gauge + SMB charger, up to 3.2 A; input follows the USB-C current advertisement; no Quick Charge yet |
| Headphones | ✅ | ADSP + WCD9335 over SLIMbus; switches to/from the speaker on plug/unplug (jack switch; no headset mic yet) |
| UI | ✅ | Plasma Mobile (GPU-accelerated) with the KDE mobile apps |
| Speaker | ✅ | TFA9891 (stock DT says TFA9890) on quaternary MI2S; tfa989x TFA9891 support added |
| GPU (Adreno 530) | ✅ | lithium's signed zap shader; GPU_GX supplied from PMI8994 S2; Plasma Mobile (KWin) renders on the GPU |
| Bluetooth | ✅ | QCA6174 (Rome 3.2) on BLSP1 UART2; address from persist; A2DP audio (AAC) to headphones |
| Microphones | 🔧 | codec capture path present, untested |
| USB host / OTG | ✅ | automatic via TUSB320L (INT on TLMM 63): devices and unpowered docks get host + 5 V; powered docks only charge (no USB-PD) |
| Suspend / CPU idle | ✅ | s2idle, wakes on Power key and RTC; PSCI CPU idle (≈ 80 mA less awake with the screen off) |
| Earpiece (piezo, LM48560) | ❌ | no mainline driver |
| Modem / calls | ❌ | out of scope for now |

Details: [Phase 6 findings](docs/PHASE6_FINDINGS.md) (current), [handoff](docs/HANDOFF.md)
(how to build, install and recover), [plan](docs/PLAN.md).

## How it is built

- **Kernel**: pinned msm8996 mainline tree plus the patches in [`kernel/patches/`](kernel/patches):
  device tree (0001), touch (0002), display + panel driver (0003), Wi-Fi (0004),
  battery/charger (0005), audio codec (0006), apq8096 MI2S clocks (0007),
  fuel-gauge current sign (0008), GPU (0009), TFA9891 driver (0010), speaker (0011),
  automatic USB host mode (0012), OTG VBUS guard (0013), Bluetooth (0014), mdp5 resume
  fix (0015), PCIe power domain kept on in suspend (0016), headphone jack detection (0017). Every board value is traced to
  lithium's stock device tree.
- **Packages**: [`packaging/pmaports/`](packaging/pmaports) — `linux-postmarketos-qcom-msm8996`,
  `device-xiaomi-lithium` (deviceinfo, UCM, WirePlumber rule, USB-C current, Bluetooth address) and
  `firmware-xiaomi-lithium`, built from a tarball of the owner's stock firmware made by
  [`scripts/make-firmware-tarball.sh`](scripts/make-firmware-tarball.sh). **No proprietary
  blob is committed.**
- **Build**: `sh scripts/pmb_build.sh --kernel` (pmbootstrap, pinned); full image without
  `--kernel`.
- **Install on a running phone**: `apk add` the packages, then copy `/boot/boot.img` behind
  lk2nd (`boot` + 512 KiB); see [handoff](docs/HANDOFF.md). Recovery: stock fastboot and
  [restore procedure](docs/RESTORE_PROCEDURE.md).

## Layout

| Path | Purpose |
|---|---|
| `docs/` | Plan, phase findings, device facts, recovery, firmware map |
| `research/` | Reviewed JSON evidence and source inventory |
| `scripts/` | Builds, staging, firmware tarball, DTB swap, checks, read-only collection |
| `bootloader/` | lk2nd lithium selector patch |
| `kernel/` | DTS, patches, panel driver source (`panel-draft/`) |
| `packaging/` | pmaports overlay (kernel, device and firmware packages) |
| `tests/` | Parser and checksum tests |
| `sources/` | Ignored external checkouts (kernel, lk2nd, pmaports, pmbootstrap) |
| `artifacts/` | Ignored dumps, firmware, logs, build outputs, agent briefs |

## Start here

1. [Device evidence](docs/DEVICE.md) and [phased plan](docs/PLAN.md).
2. [Handoff](docs/HANDOFF.md) for the current state, build and install commands.
3. `python3 scripts/preflight.py`, `python3 -m unittest discover -s tests -v` and
   `sh scripts/audit.sh` (static checks of everything we write).

## Safety

No flash commands are automated. Never write the bootloader, TrustZone, modem, `persist`,
`devinfo` or the partition tables; never lock the bootloader. Booting Android again would
restore stock recovery and wipe `userdata` (the Linux rootfs).
