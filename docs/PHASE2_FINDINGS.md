# Phase 2 — source and boot-path baseline

## Status

Phase 2 is complete. Source revisions are pinned, the current `scorpio` package
has been audited, the boot path is selected, and the lithium lk2nd board entry
builds with the pinned source and a real ARM bare-metal GCC toolchain. Kernel DTS
authoring and its first build now belong to Phase 3.

## Selected kernel and packaging baseline

Use pmaports commit `dfb010f5b9885d185d089b6e1e493030062f9756` and its
`linux-postmarketos-qcom-msm8996` package. It pins the close-to-mainline kernel
tag `v6.19.5-msm8996` at commit `1aed438cb5f49d7a61593f764d4a82f83b14114f`.
The package enables the essential MSM8996 pinctrl, APCC/RPM clocks, SPMI/RPM
regulators, UFS, interconnect, Q6 remote processors, MDP5/14 nm DSI, MSM8996
audio, QCA Bluetooth and ath10k PCI support. This makes it the best current
bring-up baseline. Mainline master is retained only as an upstream comparison.

Current pmaports contains `device-xiaomi-scorpio` in testing. It uses the shared
MSM8996 kernel, appends `qcom/msm8996pro-xiaomi-scorpio.dtb`, generates a legacy
Android boot image with the same base/offset/page values found in lithium's
stock image, and uses Fastboot. Those packaging mechanics are reusable after
verification. Its device-specific DTB, screen, firmware, touch modules and
calibration are not reusable.

## Scorpio versus lithium

| Area | Scorpio reference | Lithium evidence | Decision |
|---|---|---|---|
| SoC | MSM8996 Pro | Stock DTBs include MSM8996 v3 and Pro | Support both verified IDs during early matching |
| PMIC ID | PMI8996 | PMI8996 in lithium DTBs | Shared platform basis |
| Board ID | 34 | 38 (`0x26`) | Lithium-specific bootloader and DTS match required |
| Display | 1080×1920 | 1080×2040 | New mode and verified framebuffer geometry required |
| Touch | Atmel maXTouch, I2C `0x4a` | FocalTech FT5x46/FTE8716, I2C `0x38` | New touch node/driver validation required |
| Touch IRQ/reset | TLMM 125/75 on scorpio | TLMM 125/89 downstream evidence | Do not inherit scorpio GPIOs |
| Panel | LG SW43101 path in current scorpio package | AUO and Sharp FTE716 variants downstream | Detect actual variant; new panel driver likely required |
| Simple framebuffer | `0x83401000`, RGB888, 1080×1920 | Address/stride still unverified for lithium | Do not copy scorpio address or size |
| Native MDSS | Disabled on scorpio due MDP SMMU crash | Untested on lithium | Start with simplefb only after verified geometry |
| Storage | UFS enabled by Xiaomi common DTS | Live device uses UFS block layout | Shared controller support, lithium DTS still required |
| Wireless | QCA6174 family in Xiaomi common DTS | Shared downstream family evidence | Firmware/calibration must be lithium-specific |
| Audio | WCD9335/shared MSM8996 graph | A8 adds OPA1622, LM48560 and TFA9890 routing | Defer lithium audio additions until basic boot |

Downstream names lithium's board family `a8`. Its DTS supplies board-id 38,
FTE8716 touch configurations for AUO/Sharp displays, a 4400 mAh battery profile,
FPC1020 fingerprint wiring, and lithium-specific audio/camera nodes. These are
hardware leads to verify against stock DTB index selection and Linux bindings.

## lk2nd finding and correction

Current lk2nd does contain an `lk2nd-msm8996` target. Its MSM8996 DTB bundle
supports scorpio, OnePlus 3/3T, Mi 5/5s/5s Plus, LG H850/H990, Axon 7 and others,
but contains no lithium entry. The earlier conclusion based only on the public
device-list page was incomplete: the SoC target exists, while this board does not.

The stock DTB set gives the matching tuple needed for a lithium lk2nd entry:

- board-id: 38 (`0x26`)
- MSM8996 v3 ID: 246, revision `0x30000`
- MSM8996 Pro ID: 305, revision `0x10000`
- PMIC IDs: `0x20009 0x10013 0x00 0x00`

No existing scorpio lk2nd image should be booted or flashed on lithium.

## Boot-path decision

The preferred experimental path is a new lithium board entry in
`lk2nd-msm8996`, initially delivered through the separate recovery partition.
This preserves the stock Android boot partition. Once lk2nd starts from recovery,
its own Fastboot interface can load the mainline test image into RAM and expose
its log without first persisting Linux to the boot partition.

The matching stock bootloader contains registered `download`, `flash`, `erase`,
`continue`, `reboot` and `reboot-bootloader` commands, but no registered `boot`
command string. Therefore stock `fastboot boot IMAGE` is not selected as the
recovery-independent path. This is static evidence, not a live unsupported-command
test. Stock Fastboot and physical stock recovery are already verified, and the
exact stock recovery image is available for restoration.

This decision does not authorize a recovery flash. Before that experiment, the
lk2nd patch and resulting image must be reviewed, hashed, checked against the
64 MiB recovery limit, and paired with explicit commands and restoration steps.

## lk2nd build result

The patch in `bootloader/lk2nd` adds only the verified selector tuple. Building
the pinned lk2nd commit with `arm-none-eabi-gcc 16.2.0` succeeded and bundled ten
DTBs. The decoded lithium DTB contains board ID `0x26`, both verified SoC/revision
pairs, the verified PMIC IDs, and `xiaomi,lithium`.

The resulting `lk2nd.img` is 372,752 bytes with SHA-256
`b845d9b612bc08e457b9aa89b23850620e3284467fde4deef999955dac19444d`.
It occupies about 0.56% of the 67,108,864-byte recovery partition. This confirms
the size constraint only; it does not prove that the image starts on hardware.
No device write was performed.

`unpack_bootimg` confirms an Android boot-header v0 image with 4096-byte pages,
kernel address `0x00008000`, ramdisk address `0x01000000`, second address
`0x00f00000`, tags address `0x00000100`, and command line `lk2nd`. These packing
values agree with the audited lithium stock layout.

Phase 2's exit gate is satisfied: the kernel baseline and an explicitly scoped,
recoverable experimental boot path are selected with reproducible evidence.
Phase 3 will author the smallest original Linux DTS and build it before any live
recovery experiment.

See [source-lock.json](../research/source-lock.json) for immutable source pins.
See [lk2nd-build.json](../research/lk2nd-build.json) for the build manifest.
