# Phase 3 — hardware map and minimal DTS

## Status

Phase 3 is **complete as an offline gate** (2026-10-17). The DTS compiles
reproducibly and adds no schema warnings of its own. Every enabled node is
checked against lithium's own stock DTB by script. The hardware map, the DTS
patch and a kernel config fragment exist. Nothing has booted and no device
write occurred. Hardware confirmation of these choices belongs to P5.

Revision 1 of the DTS (first build, `74fae8d5…`) was superseded. It pointed the
console at the wrong UART (see Corrections).

## Live silicon and board selection

The running phone reports SoC ID 305, revision 1.1, and machine `MSM8996pro`.
Its selected DT has board ID 38 (`0x26`) and PMI8996 IDs `0x20009 0x10013 0 0`.
The actual target uses the Pro description (`boot.img.dtb-5`), so the DTS
includes `msm8996pro.dtsi`. The live command line selects the Sharp FTE716
panel. The full command line is not retained (device identifier).

## Method

The evidence is lithium's own stock `boot.img.dtb-5`, decompiled with the
pinned kernel's `dtc`. Phandles are resolved with `scripts/dtb_supplies.py`.
Sibling boards (scorpio, gemini) and the upstream `msm8996-xiaomi-common.dtsi`
were used only to learn mainline idioms, never as values.

`scripts/verify_lithium_dtb.py BUILT STOCK` pairs each built node with its
stock source and compares the hardware values. Its 39 checks cover identity,
reserved memory coverage in both directions, the voltage of every rail per
consumer, UFS current limits, the console UART address and pins, and keys.
A mutated DTB (L20 at 3.3 V, console moved to 0x7570000) fails 3 checks.

## What the DTS enables

| Block | Lithium evidence (stock dtb-5) |
|---|---|
| Console `blsp2_uart2` @0x75b0000, gpio4/5 `blsp_uart8` | `serial@075b0000` status ok, pinctrl `uart_console_active` |
| UFS `ufshc` + `ufsphy` | vcc L20 2.95 V, vccq L25 1.2 V, vccq2 S4 1.8 V, 600/450/450 mA; PHY L28 0.925 V, L12 1.8 V |
| USB `usb3` + `hsusb_phy1`, peripheral, high-speed | QUSB vdda18 L12 1.8 V, vdda33 L24 3.075 V |
| RPM regulators S4, L12, L20, L24, L25, L28 | exact stock min/max voltages |
| Power key, volume down | PON pon_1 code 116, pon_2 (resin) code 114 |
| Volume up | PM8994 GPIO 2, active low, 30 µA pull-up, VIN2 (S4), 15 ms, code 115 |
| Reserved memory | see below |

Deliberate choices, recorded as choices and not hardware facts:

- **S4 always-on.** It is the shared 1.8 V I/O rail, and UFS runtime PM must
  not drop Linux's vote on it. Stock doesn't set this flag; mainline MSM8996
  boards do.
- **USB fixed peripheral, high-speed PHY only.** The TUSB320L Type-C chip is
  declared at 0x47 and 0x67 with no interrupt, and the mainline binding needs
  one. The SS PHY stays unused for the first boot.
- **No `msm8996-xiaomi-common.dtsi`.** It enables NFC, IR, Type-C, modem,
  audio and GPU with sibling GPIOs. All of these stay off by SoC default.

Left untouched on purpose: TLMM 8/10/40/47/48 and PM8994 L14 plus PMI8994
LAB/IBB (live splash), and TLMM 89/125 (touch).

## Reserved memory

Lithium's stock static reservations form one contiguous block,
0x85800000–0x92900000 (`removed_regions`, `modem_region`,
`peripheral_region`). Next to it sit `dfps_data_mem` 0x83400000+0x1000,
`cont_splash_mem` 0x83401000+0x23ff000, `cont_splash_mem_hdmi` 0xb1c00000+0x23ff000
and `ocimem_log` 0xb4000000+0x100000.

The mainline SoC carveouts (hyp … mba) are contiguous from 0x85800000 to
0x91700000 and lie entirely inside the stock block. The DTS keeps them and adds
0x91700000+0x1200000 (the rest of the peripheral region) and the four outside
regions. The script confirms that every stock region is covered and every
built region lies inside a stock one. rmtfs stays dynamic, since stock has no
fixed address. ramoops is left to lk2nd, which inserts its own node.

The Xiaomi PIL layout (mpss 0x89c00000, adsp 0x8fe00000 … venus ending
0x92900000) fits lithium's stock envelopes exactly. It is only needed once
remoteprocs are enabled (P7).

## Framebuffer

No `simple-framebuffer` node. The pinned lk2nd image contains cont-splash and
`lk2nd.pass-simplefb`, which reads the live MDP5 pipe and inserts a measured
node at boot (see [DISPLAY.md](DISPLAY.md)). The DTS only keeps the splash and
dfps memory reserved. Whether lk2nd produces correct values on lithium is a
P5 check.

## Corrections

- **Console UART.** Revision 1 enabled `blsp1_uart2` (0x7570000) as stdout,
  based on the upstream Xiaomi include. In lithium's stock DTB the 0x7570000
  lsuart is `disabled`. That block is the high-speed UART that the Xiaomi tree
  gives to Bluetooth. The enabled console is `serial@075b0000` on gpio4/5,
  which is ttyHSL0 because it is the only enabled lsuart. Fixed in revision 2.
- **Reserved-memory "conflict".** The include's 0x8fe00000+0x1b00000 is
  `adsp_mem`, not lithium's `peripheral_region`. There was no conflict.

## Schema check

Full `CHECK_DTBS` (dtschema 2026.9), not only `qcom.yaml`. Every remaining
warning also appears for the upstream `msm8996pro-xiaomi-scorpio` board and
comes from shared includes:

- `pmi8994` fuel-gauge and `qcom,pmi8994-haptics` nodes are unknown to the schemas.
- `syscon@9a10000` has a single `syscon` compatible.
- `qcom,msm8996-qusb2-phy` wants `vdd-supply`. Lithium's stock feeds it from
  the CX corner (`pm8994_s2_corner`), a power domain in mainline. Upstream
  Xiaomi boards also leave it unset.

## Kernel configuration

`kernel/lithium.config` lists the 30 options this DTS and the lk2nd hand-off
need. `scripts/check_kernel_config.py` finds them all in the pinned pmaports
`linux-postmarketos-qcom-msm8996` config (sha512 matches its APKBUILD;
`USB_CONFIGFS` is a module there). They also all survive a `merge_config.sh`
onto defconfig. For P4 this means the shared kernel package is enough and only
the DTB is new.

## Deliverables

- [hardware-map.json](../research/hardware-map.json): the complete map with sources.
- `kernel/msm8996pro-xiaomi-lithium.dts` and `kernel/patches/0001-…patch`:
  identical content. The patch applies to the pinned tree.
- `kernel/lithium.config`, `scripts/check_kernel_config.py`.
- `scripts/build_lithium_dtb.sh`: builds, runs the full schema check and the stock evidence check.
- Build evidence: [kernel-dtb-build.json](../research/kernel-dtb-build.json).

## Carried into P4/P5

- Whether the gpio4/5 UART pads are physically reachable is unknown, so
  the first boot should not depend on serial. USB networking is the primary
  channel.
- Confirm on hardware: lk2nd simplefb values, UFS probe, USB gadget enumeration, keys.
- Which TUSB320L address is populated, and its interrupt (for USB role switching later).
