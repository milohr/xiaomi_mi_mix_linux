# Phase 3 — hardware map and minimal DTS

## Status

Phase 3 is in progress. The running device identity and its bootloader-selected
device tree were inspected read-only. An original minimal DTS has been started
against the pinned MSM8996 kernel; no image has been written to the device.

## Live silicon and board selection

The running phone reports SoC ID 305, revision 1.1, and machine `MSM8996pro`.
Its selected DT has board ID 38 (`0x26`) and PMI8996 IDs `0x20009 0x10013 0 0`.
This resolves the stock archive's two lithium DTBs: the actual target uses the
Pro description, while the v3 DTB remains a firmware-supported alternate board
artifact. The minimal Linux DTS therefore includes `msm8996pro.dtsi`.

The live stock command line selects
`qcom,mdss_dsi_sharp_fte716_1080p_video`. This proves the panel variant currently
installed in this unit. The complete command line is not retained because it
also contains a device identifier.

## Memory evidence

The bootloader-selected memory property contains two banks:

| Base | Size |
|---|---:|
| `0x80000000` | `0x80000000` |
| `0x100000000` | `0x7e550000` |

Mainline's MSM8996 DTS deliberately leaves the memory size at zero for the
bootloader to populate, so the board DTS does not hard-code these sizes.

The live DT confirms the splash reservation at `0x83401000` with size
`0x23ff000`, matching stock DTB indices 4 and 5. This does not prove the active
scanout byte count, stride, pixel format, or retained clocks. The initial DTS
therefore does not create a simple-framebuffer node.

## Minimal DTS policy

The initial DTS enables only BLSP1 UART2 beyond the inherited SoC and PMIC
descriptions. Downstream Xiaomi source enables this UART, and stock bootargs use
`ttyHSL0,115200,n8`. Whether the pins are externally accessible remains unknown.

Display, touch, modem, audio, cameras and guessed framebuffer geometry remain
disabled. UFS and USB will be added only after their lithium regulator, PHY and
connector dependencies are traced through stock and downstream evidence.

The structured evidence is in
[hardware-map.json](../research/hardware-map.json).

## First build result

The minimal DTS compiles at pinned kernel commit
`1aed438cb5f49d7a61593f764d4a82f83b14114f`. Targeted validation against the
Qualcomm board schema passes with `dtschema 2026.9`. The resulting DTB is 64,405
bytes with SHA-256
`74fae8d5515899757bd937fc8dc13f1b22bbbcf1388b182a42815ef7a4ef371b`.
This proves source and binding consistency, not hardware bootability.

The reproducible source patch is in `kernel/patches`; build evidence is in
[kernel-dtb-build.json](../research/kernel-dtb-build.json).
