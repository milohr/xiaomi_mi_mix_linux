# Phase 5 findings — first native boot (2026-10-18)

Status: **gate met.** Linux 6.19.5 boots on the Mi MIX from RAM, puts its console on
the screen through lk2nd's simple-framebuffer, and opens the postmarketOS debug shell
over USB networking (telnet 172.16.42.1). The only partition written is recovery
(lk2nd); boot, system and userdata were never touched. Raw logs:
`artifacts/p5/` (ignored).

## What happened, in order

| Step | Result |
|---|---|
| Host prep | all four image hashes matched docs/P5_FIRST_BOOT.md; bootloader unlocked (verified boot orange); battery 100 % on AC |
| A: `fastboot flash recovery lk2nd.img` (stock fastboot, `MSM8996_A8`) | OKAY |
| enter lk2nd | via Volume Up + Power. lk2nd: `xiaomi,lithium`, version `next-8b46487-…`, panel `qcom,mdss_dsi_sharp_fte716_1080p_video`; continuous splash found (1080×2040, stride 3240); no Linux at boot+512 KiB, so fastboot |
| B: `fastboot boot p5-boot.img` (`af734348…`) | **hang at 1.47 s**, reset about 10 s later; the stock bootloader then started Android |
| ramoops | read through lk2nd after the restart: 30 KB of console with bit errors (memory decay through a reset and an Android boot), but legible. The last line: `arm-smmu d00000.iommu: preserved 0 boot mappings` |
| Android boot | **MIUI restored its stock recovery** (the risk the packet named). Step A repeated |
| fix | `&mdp_smmu`: `qcom,no-smr-check; qcom,skip-init; /delete-property/ power-domains;`, as the upstream sibling `msm8996pro-xiaomi-scorpio.dts` in the pinned tree has ("required to avoid crashing"). This kernel's `arm-smmu.c` reads both properties. DTB `8f8d7512…` (66,236 bytes), stock evidence check all passed, no new schema warnings |
| B again: `p5b-boot.img` (`77505d98…`), Volume Up held so a crash would land in lk2nd | **booted.** Kernel text on screen, USB network up (host got 172.16.42.2), debug shell after the 30 s wait for pmOS partitions |

`p5b-boot.img` is `p5-boot.img` with only the appended DTB replaced
(`scripts/swap_bootimg_dtb.py`: same gzip kernel, ramdisk and command line; header id
recomputed and checked against the mkbootimg formula on the original).

## What the running system shows

- `uname`: `6.19.5 #2-postmarketos-qcom-msm8996`, the P5 command line, 8 CPUs online.
- **Display:** `simple-framebuffer 83401000.framebuffer: … mode=1080x2040x24, linelength=3240 … fb0: simplefb registered`; fbcon at 135×127 characters. At 50.9 s the ramdisk's on-screen keyboard (`buffyboard`) starts and the screen goes blank; `ioctl(FBIOBLANK): Invalid argument` (simplefb cannot blank). The framebuffer itself works.
- **USB:** dwc3 peripheral on the HS PHY; RNDIS/NCM gadget `18d1:d001`; unudhcpd hands out 172.16.42.2.
- **UFS: not working.** `ufshcd-qcom 624000.ufshc` probes (`scsi host0`), but the link fails:
  `dme-get: attr-id 0xa00b failed`, `hw clk gating enabled failed`, then `saved_uic_err 0x41`,
  92 data-link errors (`dl_err … 0x80000002`) and an aborted command at 7.9 s. No `/dev/sd*`,
  so the initramfs finds no partitions (`failed to mount subpartitions`) and opens the debug
  shell, as planned. Also: `Unable to find vdd-hba-supply regulator, assuming enabled`, and
  `phy@627000: Failed to get clk index: 1 ret: -517` (deferred). Only reads were attempted.
- **Reserved memory:** lk2nd put the ramoops buffer at `b2280000` (512 KiB), inside the stock
  region `memory@b1c00000` (36 MiB, no-map) the DTS reserves. The kernel warns
  `failed to reserve … memory@b1c00000` once, then reserves it (`b1c00000..b3ffefff nomap`).
  Harmless for P5; ramoops should move out of a firmware region later.
- `psci: [Firmware Bug]: failed to set PC mode: -1`: firmware, expected on this SoC.

## Lessons for the next sessions

- **Android must not boot between Step A and a test**: it restores stock recovery. Go
  stock fastboot → flash lk2nd → Volume Up + Power (hold through the reset).
- **A long Power press resets the phone; it doesn't power it off.** For a real power-off,
  use lk2nd's menu → Shutdown. From Android, `adb reboot recovery` reaches recovery.
- **Hold Volume Up during a test boot**, so a crash reset lands in lk2nd with ramoops intact.
- Stock fastboot and lk2nd share USB ID `18d1:d00d`; tell them apart with `getvar lk2nd:compatible`.

## Next (P6 candidates)

1. **UFS link**: compare the stock UFS node (supplies, `vdd-hba`, PHY clocks, lanes,
   `freq-table-hz`, `reset-gpios`) with ours; the deferred PHY clock and the missing
   vdd-hba are the first suspects. Storage is needed before any rootfs.
2. Touch (patch 0002) as its own change, now that the boot path is known good.
3. Move or drop ramoops out of `memory@b1c00000`.
4. A full package build with the fixed patch 0001 (kernel r2) to replace the swapped-DTB image.
