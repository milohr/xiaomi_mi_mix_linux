# Lithium display evidence audit

Device: Xiaomi Mi MIX (`lithium`, MSM8996 Pro, board-id 38). Read-only, offline,
clean-room audit made on 2026-10-17. No hardware validation. Nothing was flashed, and no
existing project file was changed.

Status words used throughout: **observed** (lithium stock artifact or live DT),
**source_evidence** (pinned downstream source), **inferred**, **conflicting**,
**unknown**. Machine-readable values with full provenance are in
`display-evidence.json`. The decoded streams are in `panel-*.json`.

## 1. Executive findings

1. **Two panel variants, both 1080×2040 video mode.** Lithium's own DT carries
   exactly two FTE716 panels: Sharp (`qcom,mdss_dsi_sharp_fte716_1080p_video`)
   and AUO (`qcom,mdss_dsi_auo_fte716_1080p_video`). Timings, PHY timings,
   lanes, reset sequence, supplies and backlight are identical. The vendor init
   tables, the DCS ordering and the off order differ.
2. **The bootloader chooses the panel at runtime.** Stock aboot contains
   "Sharp/Fte716 FHD panel detected", "AUO/Fte716 FHD panel detected",
   "Defalut Sharp/Fte716 FHD panel" and "lcd 3state id = %d". It passes
   `mdss_mdp.panel=…:dsi:0:<node>`, and the downstream kernel matches that node name
   (`mdss_dsi.c:2833`). `qcom,mdss-dsi-panel-id` (Sharp 0, AUO 5) is never
   parsed. The audited unit runs **Sharp** (observed live, recorded in
   `research/hardware-map.json`). How aboot reads the ID (which GPIO, which
   mapping) is **unknown**.
3. **The DT default panel is wrong for lithium.** `a8-msm8996-mtp.dtsi:297`
   prefers `dsi_lgd_sw43101_fhd_video` (an LG panel). Only the bootloader
   override makes FTE716 active. Don't take the panel from the DT default.
4. **The source matches stock at the panel level.** All 77 Sharp and 93 AUO panel
   properties are byte-identical across all four lithium stock DTBs
   (boot/recovery indices 4 and 5), including every command stream. A negative
   control (Sharp source compared with the AUO stock node) does detect differences.
5. **The source does not match stock at the board level.** Stock `mdss_dsi_ctrl0` has
   `vddr-supply = <&disp_vddr_vreg>`, which is absent from the pinned source. Stock
   WLED lacks `qcom,en-phase-stag`, which the source sets. So the LineageOS tree
   is not the exact stock build tree. For board wiring, treat the stock DTB as authoritative.
6. **The encoding is proven, not assumed.** Each packet is a 7-byte header
   (`dtype, last, vc, ack, wait_ms, dlen_be16`) plus `dlen` payload bytes. Proof:
   `struct dsi_ctrl_hdr` (`mdss_dsi_cmd.h:84-91`) and `ntohs()` in
   `mdss_dsi_parse_dcs_cmds` (`mdss_dsi_panel.c:1098-1181`, line 1125). All
   8 decoded streams round-trip losslessly, and there are no malformed streams.
7. **Framebuffer: the reservation is proven, the scan-out geometry is not.**
   `cont_splash_mem` 0x83401000 + 0x23ff000 is in lithium's own stock DTBs and the
   live DT, and overlaps no static reserved region. Scan-out base within it,
   stride and memory format are runtime MDP state left by aboot: **unknown**.
8. **Mainline has no `struct mipi_dsi_dcs_cmd`** in the selected tree
   (`1aed438c…`). The current model is `struct mipi_dsi_multi_context` plus
   `*_multi()` helpers, and those helpers choose the packet type from payload length. 59
   Sharp and 93 AUO 2-byte generic **long** writes (0x29) would go out as
   generic **short** writes (0x23). That needs a decision or a hardware test.

## 2. Evidence and provenance

| ID | Input | Pin / hash | Used for |
|---|---|---|---|
| K | LineageOS `android_kernel_xiaomi_msm8996` (lineage-18.1) | `4aa1814c63b82ce67d0ef0434ca510be94bb8284` | panel DTSI, board DTSI, MDSS driver |
| D | LineageOS `android_device_xiaomi_lithium` (lineage-19.1) | `bac0b4e18fc2c6d86d7c79b2764c6e575ad140ec` | checked: no panel/DSI data |
| C | LineageOS `android_device_xiaomi_msm8996-common` (lineage-19.1) | `7486d07ec3f7d5413a53009d63fe98c783667d15` | light HAL sysfs path only |
| M | msm8996-mainline `linux` tag v6.19.5-msm8996 | `1aed438cb5f49d7a61593f764d4a82f83b14114f` | DRM/DSI API, bindings |
| B4 | `boot.img.dtb-4` (MSM8996 v3.0, board 38) | `211d7e0022c937bc18117415f5015ed5518c3eb82b56630de10049ecdd5dba66` | corroboration |
| B5 | `boot.img.dtb-5` (MSM8996 Pro, board 38, the live SoC) | `a2968fa1b189c5e73bbd89a578575ce7cf0a42f2bc31968265260b362f49ce01` | corroboration |
| R4 | `recovery.img.dtb-4` | `211d7e00…dba66` (identical to B4) | corroboration |
| R5 | `recovery.img.dtb-5` | `a2968fa1…ce01` (identical to B5) | corroboration |
| A | `emmc_appsboot.mbn` (stock aboot) | `a9cf47cc2795c3ded98dbc501bb52739de8dc51803e26defcb51c0c461ff2083` | panel-detection strings |
| L | `research/hardware-map.json` live observations | (existing project file) | installed variant, live reservations |

The other 16 stock DTB indices (board-ids 31–34, 37, 47) also contain both
FTE716 nodes, because the Xiaomi panel include is shared. They are not lithium and
were not used. Every lithium-applicable fact below cites K by path and line, and B4/B5/R4/R5 by DTB index.

Key source locations (repository K):

| File | Lines | Symbol |
|---|---|---|
| `arch/arm/boot/dts/qcom/dsi-panel-sharp-fte716-1080p-video.dtsi` | 15–260 | `dsi_sharp_fte716_1080p_video` |
| `arch/arm/boot/dts/qcom/dsi-panel-auo-fte716-1080p-video.dtsi` | 15–565 | `dsi_auo_fte716_1080p_video` |
| `arch/arm/boot/dts/qcom/msm8996-mdss-panels-xiaomi.dtsi` | 54–55, 60–94 | includes, `dsi_panel_pwr_supply` |
| `arch/arm/boot/dts/qcom/a8-msm8996pro-pmi8996-mtp.dts` | 17–24 | A8 Pro top, board-id <38 0> |
| `arch/arm/boot/dts/qcom/a8-msm8996-v3.0-pmi8996-mtp.dts` | 17–24 | A8 v3.0 top, board-id <38 0> |
| `arch/arm/boot/dts/qcom/a8-msm8996-mtp.dtsi` | 32–34, 193–268, 293–315 | WLED OVP, FT5x46 touch, `&mdss_dsi0/1` |
| `arch/arm/boot/dts/qcom/msm8996-xiaomi-common.dtsi` | 354–371, 1103–1115, 1219–1244, 1787–1794 | DSI0 defaults, LAB/WLED overrides, vddr pinctrl, `disp_vddr_vreg` |
| `arch/arm/boot/dts/qcom/msm8996-mdss.dtsi` | 291–297, 401–450 | `mdss_fb0` splash link, `mdss_dsi0` supplies |
| `arch/arm/boot/dts/qcom/msm8996.dtsi` | 225–238 | `dfps_data_mem`, `cont_splash_mem` |
| `arch/arm/boot/dts/qcom/msm8996-pinctrl.dtsi` | 391–439 | gpio8 reset, gpio10 TE pinctrl |
| `arch/arm/boot/dts/qcom/msm-pmi8994.dtsi` | 448–549 | LAB/IBB, WLED |
| `drivers/video/msm/mdss/mdss_dsi_cmd.h` | 47–70, 84–91 | DTYPE table, `struct dsi_ctrl_hdr` |
| `drivers/video/msm/mdss/mdss_dsi_panel.c` | 214–241, 375–537, 1098–1181 | cmds send (LP/HS), reset, parser |
| `drivers/video/msm/mdss/mdss_dsi_cmd.c` | 95–130, 272–332, 584–616 | packet builders, dispatch |
| `drivers/video/msm/mdss/mdss_dsi_host.c` | 33, 1653–1702 | `VSYNC_PERIOD`, batching by `last` |
| `drivers/video/msm/mdss/mdss_dsi.c` | 275–348, 1486–1502, 2833–2900, 4095–4126 | power on/off, LP-11 reset, panel lookup, GPIO parse |
| `drivers/video/msm/mdss/mdss_mdp_splash_logo.c` | 683–722 | splash reservation consumer |

## 3. Panel variant comparison

All rows are source_evidence and byte-identical in B4/B5/R4/R5, unless marked otherwise.

| Field | Sharp FTE716 | AUO FTE716 |
|---|---|---|
| Downstream node | `qcom,mdss_dsi_sharp_fte716_1080p_video` | `qcom,mdss_dsi_auo_fte716_1080p_video` |
| Panel name / model | "sharp fte716 1080p video mode dsi panel" / "SHARP FHD FTE716 VIDEO PANEL" | "auo fte716 1080p video mode dsi panel" / "AUO FHD FTE716 VIDEO PANEL" |
| `qcom,mdss-dsi-panel-id` | 0 (unused by the driver) | 5 (unused by the driver) |
| Selection | aboot fallback default; observed on the audited unit | aboot "detected" path; not observed |
| Touch FW pairing (lcd-vendor) | 0x33, `fte8716_sharp_incell_*_a8.fw` | 0x34, `fte8716_auo_incell_*_a8.fw` |
| Type | `dsi_video_mode`, burst, h-sync-pulse 1 | same |
| Resolution | 1080 × 2040 | same |
| Physical size | 75 × 143 mm | same |
| Frame rate | 60 Hz (min 53, max 60) | same |
| Pixel format | 24 bpp | same |
| VC / stream | 0 / 0 | same |
| Lanes | 4 (lane-0..3-state) | same |
| H timings | FP 46, BP 32, PW 4, skew 0 | same |
| V timings | FP 16, BP 16, PW 4 | same |
| Borders | all 0 | same |
| PHY timings v2 | `23 1F 07 09 05 03 04 a0` ×4, `23 1A 08 09 05 03 04 a0` | same |
| t-clk-post / pre | 0x0D / 0x2F | same |
| Flags | lp11-init, tx-eot-append, bllp-power-mode, bllp-eof-power-mode | same |
| Triggers | dma `trigger_sw`, mdp `none` | same |
| Reset sequence | <1 10>, <0 1>, <1 10> | same |
| Backlight | `bl_ctrl_wled`, 1–4095, brightness-max 4095 | same |
| ESD | `te_signal_check`, video-panel-esd-te-check; no status-read command | same |
| Continuous splash | `qcom,cont-splash-enabled` | same |
| On-command | 1085 B, 88 packets, 20 batches, LP | 1768 B, 144 packets, 21 batches, LP |
| On DCS order | 11 (120 ms) → 51 FF, 53 24, 55 00, 35 00 → 29 (20 ms) | 51 FF, 53 24, 55 00, 35 00 → 11 (120 ms) → 29 (20 ms) |
| Off-command | 28 (50 ms) → 10 (120 ms), HS | **10 (120 ms) → 28 (50 ms)**, HS |
| Display on / off | `05 01 00 00 20 00 02 29 00` / `… 28 00`, HS | identical |
| Vendor init | CA (11 B), 16 × C6/C7 tables, B3 0C | adds C0, A5, C2, C3, CE, F5, C5, CF, CB, F3, CA 02 0F 00 and its own C7 values |
| Night brightness | <8 26 44 62> | <7 25 43 61> |
| Extra Xiaomi commands | CABC, dimming, idle, warm, cold | same, plus papermode and papermode1–7 |

Both on-streams begin with the same vendor preamble: address window `2A 00 00 04 37`
/ `2B 00 00 07 F7` (columns 0–1079, rows 0–2039, which corroborates the resolution),
then `FF 87 16 01` / `FF 87 16` (inferred: command-2 unlock of an FT8716-class
controller, consistent with the FTE716/FTE8716 naming), and they end with
`FF 00 00 00` / `FF 00 00` (inferred: re-lock). Every `29 … 02 00 xx` packet sets a
register offset for the next write (inferred, from the alternating pattern).
Opcode meanings beyond MIPI DCS are inferences and are not needed to reproduce the bytes.

## 4. Command encoding and decoding

Downstream layout, proven by `struct dsi_ctrl_hdr` (`mdss_dsi_cmd.h:84-91`, `__packed`):

| Byte | Field | Meaning (code reference) |
|---|---|---|
| 0 | `dtype` | MIPI data type; dispatched in `mdss_dsi_cmd_dma_add` (`mdss_dsi_cmd.c:584-616`) |
| 1 | `last` | 1 = end of a DMA batch; packets accumulate until `last` (`mdss_dsi_host.c:1675`) |
| 2 | `vc` | virtual channel → `DSI_HDR_VC` |
| 3 | `ack` | request BTA/ACK → `DSI_HDR_BTA` (`mdss_dsi_cmd.c:288, 321`) |
| 4 | `wait` | milliseconds slept after the batch; only read on `last=1` packets (`mdss_dsi_host.c:1694-1695`) |
| 5–6 | `dlen` | payload length, big-endian (`ntohs`, `mdss_dsi_panel.c:1125`) |
| 7… | payload | `dlen` bytes |

Rules that affect translation:

- A wait ≤ 17 ms (`VSYNC_PERIOD`) is skipped when the video engine was busy. Both
  FTE716 waits (120, 50, 32, 20 ms) exceed 17, so they always apply.
- `0x05` (DCS short, 0 parameters) entries carry `dlen=2` with a trailing `00`. The
  host sends only `payload[0]` and forces data1 to 0 (`mdss_dsi_cmd.c:293-297`),
  so the pad byte never reaches the wire. That doesn't change the bytes on the wire.
- `0x29` generic long writes are padded with 0xFF to 4 bytes in the host DMA
  buffer only. The word count stays `dlen` (`mdss_dsi_cmd.c:105-118`).
- `2A`/`2B` are sent as **generic** long writes (0x29), not DCS long writes (0x39).
- The command state comes from the `*-command-state` property. LP sets
  `CMD_REQ_LP_MODE`, HS sets `CMD_REQ_HS_MODE` (`mdss_dsi_panel.c:231-234`). On is LP;
  off, display-on and display-off are HS.
- All packets: `vc=0`, `ack=0`. Every stream ends with `last=1`. No trailing
  bytes, no oversize `dlen`, no stream that is malformed or ambiguous.

The full packet tables are in the appendix (section 11).

## 5. Power, reset and backlight sequence (downstream, source_evidence)

Board wiring (source and stock agree unless noted):

| Signal | Lithium value | Evidence |
|---|---|---|
| DSI host | DSI0 @0x994000, `single_dsi` | `msm8996-mdss.dtsi:401`, `a8-msm8996-mtp.dtsi:294`; B5 |
| Reset | TLMM gpio8 (pinctrl: 8 mA no-pull active, 2 mA pull-down sleep) | `a8-msm8996-mtp.dtsi:302`, `msm8996-pinctrl.dtsi:391-414`; B4/B5 |
| Enable | TLMM gpio47 (`disp_en_gpio`) | `a8-msm8996-mtp.dtsi:303`; B4/B5 |
| Backlight enable | TLMM gpio48 (`bklt_en_gpio`) | `a8-msm8996-mtp.dtsi:304`; B4/B5 |
| TE | TLMM gpio10, function `mdp_vsync` | `a8-msm8996-mtp.dtsi:301`, `msm8996-pinctrl.dtsi:417` |
| VDDR | `disp_vddr_vreg` regulator-fixed, TLMM gpio40, active-high, boot-on, 4 ms startup; pinctrl output-high | `msm8996-xiaomi-common.dtsi:1219, 1787-1794`; B5 |
| VDDR on DSI ctrl | `vddr-supply` on `mdss_dsi_ctrl0` | **conflicting**: present in B4/B5/R4/R5, absent from K |
| vddio | PM8994 L14, 1.8 V; load 62 mA / 80 µA; post-on 1 ms, pre-off 10 ms | `msm8996-mdss-panels-xiaomi.dtsi:64-73`, `msm8996-regulator.dtsi:228` |
| lab | PMI8994 LAB @0xde00, 4.6–6.0 V (init LCD 5.5 V); load 100 mA | `…panels-xiaomi.dtsi:75-82`, `msm-pmi8994.dtsi:488-502` |
| ibb | PMI8994 IBB @0xdc00, 4.6–6.0 V (init LCD 5.5 V); post-on 10 ms, pre-off 5 ms | `…panels-xiaomi.dtsi:84-93`, `msm-pmi8994.dtsi:456-470` |
| LAB/IBB mode | `lcd`; stock IBB discharge 300 Ω, LAB soft-start 400 | `msm8996-xiaomi-common.dtsi:368-371, 1104`, `msm-pmi8996.dtsi:23` |
| Backlight | PMI8994 WLED, OVP 31 V, 20 mA full-scale, 600 kHz, strings 0–1, CABC on, hybrid dim | stock B5 node; source `a8…:33`, `common:1109-1114` (en-phase-stag **conflicting**) |
| Android sysfs | `/sys/class/leds/lcd-backlight/{brightness,max_brightness}` | C `light/service.cpp:34-35` |

Downstream power-on order, derived from code paths and not from a trace:

1. `msm_dss_enable_vreg` in list order: vddio on, 1 ms; lab on; ibb on, 10 ms
   (`mdss_dsi.c:309-322`).
2. DSI link clocks on, controller sw-reset, lanes at LP-11 (`mdss_dsi.c:1486-1489`).
3. Because of `lp11-init`, the reset happens *now* (`mdss_dsi.c:1491-1499`): pinctrl
   `mdss_default`, gpio47 high, 100–110 µs (`mdss_dsi_panel.c:459-469`), then the
   reset sequence on gpio8: high 10 ms, low 1 ms, high 10 ms (`:471-486`), then gpio48 high (`:488-496`).
4. On-command in LP mode, 20–21 batches, waits as decoded.
5. Video stream, then WLED brightness (`bl_ctrl_wled`).

Off: off-command in HS; gpio48 low; gpio47 low, 100 µs; gpio8 low
(`mdss_dsi_panel.c:520-531`); pinctrl sleep; regulators in reverse: ibb (5 ms
pre-off), lab, vddio (10 ms pre-off). With continuous splash active at first
boot, the GPIO/reset steps are skipped (`mdss_dsi_panel.c:458`).

The in-cell touch (FT5x46-family driver, I2C 0x38, reset TLMM 89, IRQ TLMM 125)
shares LAB/IBB with the panel (`a8-msm8996-mtp.dtsi:194-214`).
`mdss_panel_reset_skip_enable()` is called only by Synaptics drivers, so on
lithium the display driver owns the LCD reset.

## 6. Framebuffer findings

| Item | Value | Status |
|---|---|---|
| `cont_splash_mem` | base 0x83401000, size 0x23ff000, end 0x85800000 | observed (B4/B5/R4/R5, live DT); source `msm8996.dtsi:230-231` |
| `dfps_data_mem` | 0x83400000 + 0x1000 (ends exactly at the splash base) | observed |
| Overlap with static stock reservations | none; adjacent to `dfps_data_mem` and `removed_regions@85800000` | observed (B5) |
| Kernel consumer | `mdss_fb0` → `qcom,cont-splash-memory` → `linux,contiguous-region`; only base/size read | source_evidence (`mdss_mdp_splash_logo.c:683-722`) |
| Scan-out base | inside the reservation; exact address not established | **unknown** |
| Stride | runtime MDP SSPP state | **unknown** |
| Memory pixel format | runtime MDP state (DSI link is RGB888) | **unknown** |
| Dimensions | 1080 × 2040 assumed equal to the panel | inferred |
| Size check | RGB888 6,609,600 B; XRGB8888 8,812,800 B; both fit 37,744,640 B | inferred, doesn't choose a format |

What is fixed and what is runtime: the reservation is a fixed DT value. The
address, stride and format actually being scanned out are runtime register state
written by aboot. The downstream kernel never reads them from DT. aboot holds no
literal 0x83401000. 0x83400000 appears twice as a little-endian 32-bit constant
(first at file offset 0xa0514), and what it means wasn't established. The
dynamically placed carve-outs (adsp, qseecom, secure) can't be checked offline.
The base matches scorpio's number, but here it comes only from lithium's own
DTBs and live DT. Scorpio's stride and format were **not** used.

## 7. Mainline model (selected tree `1aed438c…`)

| Question | Answer | Reference (M) |
|---|---|---|
| `struct mipi_dsi_dcs_cmd` | **does not exist** (no match in `include/` or `drivers/gpu/drm/`) | — |
| Batch API | `struct mipi_dsi_multi_context` + `*_multi()` | `include/drm/drm_mipi_dsi.h:202` |
| Generic write type | by length: 0 → 0x03, 1 → 0x13, **2 → 0x23**, >2 → 0x29 | `drm_mipi_dsi.c:744` |
| DCS write type | by length: 1 → 0x05, 2 → 0x15, >2 → 0x39 | `drm_mipi_dsi.c:920` |
| Explicit-type transfer | `mipi_dsi_device_transfer()` is `static` | `drm_mipi_dsi.c:448` |
| Sequence macros | `mipi_dsi_generic_write_seq_multi`, `mipi_dsi_dcs_write_seq_multi`, `mipi_dsi_msleep` | `drm_mipi_dsi.h:402, 434, 301` |
| LP commands | `MIPI_DSI_MODE_LPM` | `drm_mipi_dsi.h:138` |
| FTE716 driver | none; `panel-ebbg-ft8719.c` is a different FocalTech panel | `drivers/gpu/drm/panel/` |
| WLED binding | `qcom,pmi8994-wled` exists | `qcom-wled.yaml:23` |
| LAB/IBB binding | only `qcom,pmi8998-lab-ibb` | `qcom-labibb-regulator.yaml:20` |
| simple-framebuffer | `r8g8b8`, `x8r8g8b8`, `a8r8g8b8`, … | `simple-framebuffer.yaml:103` |

How each downstream construct maps to a modern representation. This is a
description, not a driver:

| Downstream | Modern equivalent | Fidelity |
|---|---|---|
| `05 … 02 11 00` | `mipi_dsi_dcs_exit_sleep_mode_multi()` (sends 0x05 + `11`) | exact on the wire |
| `15 … 02 51 FF` etc. | `mipi_dsi_dcs_write_seq_multi(ctx, 0x51, 0xff)` → 0x15 | exact |
| `29 …` with dlen ≥ 3 | `mipi_dsi_generic_write_seq_multi(ctx, …)` → 0x29 | exact |
| `29 …` with dlen = 2 | the same macro sends **0x23** | **type changes**; needs a hardware test, or a host-level `mipi_dsi_msg` with `.type = MIPI_DSI_GENERIC_LONG_WRITE` |
| `29 … 2A/2B` | keep as generic writes, not `mipi_dsi_dcs_set_column_address_multi()` (0x39) | keep 0x29 for fidelity |
| `last` batching | no equivalent; each helper call is one transfer | the stream order is kept; delays only follow `last=1` |
| `wait` on `last=1` | `mipi_dsi_msleep(ctx, ms)` after that packet | exact (all waits > 17 ms) |
| on LP / off HS | set `MIPI_DSI_MODE_LPM` for on; clear it for off | exact intent |
| reset `<1 10>,<0 1>,<1 10>` | `reset-gpios` (gpio8) with a mainline polarity convention, toggled with `usleep_range` | the polarity convention is a binding decision |
| enable gpio47, vddr gpio40 | `enable-gpios` / fixed regulator, or supplies | the role of gpio47 is unknown |
| h-sync-pulse, burst, EoT | `MIPI_DSI_MODE_VIDEO | _VIDEO_BURST | _VIDEO_SYNC_PULSE`; do **not** set `_NO_EOT_PACKET` | inferred |
| Mode | clock 144739 kHz, h 1080/1126/1130/1162, v 2040/2056/2060/2076, 75 × 143 mm | inferred arithmetic |

A lossless intermediate form is the per-packet table in `panel-*.json`: type,
last, vc, ack, wait, payload. A later panel driver can be generated or
checked against it.

## 8. Remaining unknowns

1. Scan-out base within the reservation, its stride, and its memory pixel format.
2. The aboot panel-ID mechanism (GPIO, tri-state mapping) and the AUO detection condition.
3. The electrical role of gpio47, and the voltage of `disp_vddr` (the node name suggests 1.6 V, inferred).
4. Whether the FTE716 accepts 0x23 in place of 2-byte 0x29 generic writes.
5. Why stock adds `vddr-supply` and drops `en-phase-stag`. The stock kernel source is
   not available, so other stock-only driver behaviour can't be excluded.
6. PMI8994/PMI8996 LAB/IBB support in mainline, and the needed power-up timing
   (stock `qpnp-ibb-lab-pwrup-delay` 8000 µs).
7. Whether mainline MDP5/DSI on MSM8996 can take over from continuous splash on lithium
   (scorpio disables native MDSS because of an SMMU fault; lithium is untested).

## 9. Recommendations

**Phase 3 (minimal DTS):**
- Keep `cont_splash_mem` reserved (0x83401000, 0x23ff000) so Linux never
  allocates over live scan-out. That value is proven for lithium.
- Don't add `simple-framebuffer` yet. First read the MDP SSPP source address,
  stride and format on stock read-only (for example the `mdp` debugfs register
  dump on the running Android kernel), or have lk2nd report them. Then fill
  the node from that measurement.
- Leave TLMM gpio8/10/40/47/48 unclaimed and the display nodes disabled, so the
  bootloader's state is undisturbed. Don't let a regulator driver switch off
  L14, LAB/IBB or the gpio40 rail while splash is live (they must stay
  on or be left untouched).
- Don't take the panel from the A8 DT default (LG SW43101).

**Phase 6 (panel driver), after the hardware map and bindings are integrated:**
- One compatible per variant. Select by bootloader-reported panel, or by a read-back once the ID method is known.
- Generate the init tables from `panel-*.json`, and keep per-variant DCS order
  (AUO: DCS before sleep-out; off: sleep-in before display-off).
- Settle the 0x29 → 0x23 question on hardware before simplifying.
- Bring up the WLED with the stock parameters (31 V OVP, 20 mA, strings 0–1).
- Resolve LAB/IBB support for PMI8994 first. Touch depends on the same rails.

## 10. Reproduction

```
python3 -I extract_evidence.py --kernel-src <K> --device-src <D> --common-src <C> \
    --mainline-src sources/linux-msm8996 --stock-dir artifacts/stock/audit
python3 -I verify_commands.py
```
`extract_evidence.py` refuses checkouts whose HEAD isn't the pinned commit,
and DTBs whose board-id isn't <38 0>.

## 11. Appendix — decoded command tables

Columns: packet index, source line in the panel DTSI, data type, class, `last`,
`vc`, `ack`, wait (ms, applied after the batch), `dlen`, payload bytes, batch number.
"vendor offset" and opcode meanings beyond MIPI DCS are inferred. The raw
streams and per-packet byte offsets are in the JSON files.

#### Sharp FTE716 — qcom,mdss-dsi-on-command (dsi_lp_mode, lines 39–128, 1085 bytes, 88 packets, 20 batches)

| # | line | type | class | last | vc | ack | wait ms | dlen | payload | batch | note |
|---:|---:|---|---|---:|---:|---:|---:|---:|---|---:|---|
| 0 | 40 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 0 | vendor offset (inferred) |
| 1 | 41 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 5 | `2a 00 00 04 37` | 0 | DCS opcode in GENERIC long write |
| 2 | 42 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 0 | vendor offset (inferred) |
| 3 | 43 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 5 | `2b 00 00 07 f7` | 0 | DCS opcode in GENERIC long write |
| 4 | 44 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 0 | vendor offset (inferred) |
| 5 | 45 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 4 | `ff 87 16 01` | 0 |  |
| 6 | 46 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 80` | 0 | vendor offset (inferred) |
| 7 | 47 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 3 | `ff 87 16` | 0 |  |
| 8 | 48 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 80` | 1 | vendor offset (inferred) |
| 9 | 49 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 11 | `ca 80 bf ff 99 ff 80 ff 00 00 00` | 1 |  |
| 10 | 50 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 1 | vendor offset (inferred) |
| 11 | 51 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 10` | 1 |  |
| 12 | 52 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 1 | vendor offset (inferred) |
| 13 | 53 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 90 9a 9a 9b c9 a9 98 99 aa a8 bb 88 88 68 45 44 44 44` | 1 |  |
| 14 | 54 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 2 | vendor offset (inferred) |
| 15 | 55 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 11` | 2 |  |
| 16 | 56 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 2 | vendor offset (inferred) |
| 17 | 57 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 90 9a 8a 9b c8 99 99 99 a9 a8 ba 88 88 78 56 45 44 44` | 2 |  |
| 18 | 58 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 3 | vendor offset (inferred) |
| 19 | 59 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 12` | 3 |  |
| 20 | 60 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 3 | vendor offset (inferred) |
| 21 | 61 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 90 99 9a 8a b9 9a 98 89 b9 98 ba 88 88 78 56 55 55 44` | 3 |  |
| 22 | 62 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 4 | vendor offset (inferred) |
| 23 | 63 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 13` | 4 |  |
| 24 | 64 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 4 | vendor offset (inferred) |
| 25 | 65 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 90 99 8a 8a b9 99 89 89 a9 99 b9 88 88 88 56 55 55 55` | 4 |  |
| 26 | 66 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 5 | vendor offset (inferred) |
| 27 | 67 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 14` | 5 |  |
| 28 | 68 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 5 | vendor offset (inferred) |
| 29 | 69 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 8a 8a 9a b8 89 89 89 a9 98 b9 88 88 88 67 56 55 55` | 5 |  |
| 30 | 70 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 6 | vendor offset (inferred) |
| 31 | 71 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 15` | 6 |  |
| 32 | 72 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 6 | vendor offset (inferred) |
| 33 | 73 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 99 99 99 a8 99 89 98 a8 89 a9 88 88 88 67 66 66 55` | 6 |  |
| 34 | 74 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 7 | vendor offset (inferred) |
| 35 | 75 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 16` | 7 |  |
| 36 | 76 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 7 | vendor offset (inferred) |
| 37 | 77 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 99 89 8a a8 99 98 88 99 89 a9 88 88 88 67 66 66 66` | 7 |  |
| 38 | 78 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 8 | vendor offset (inferred) |
| 39 | 79 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 17` | 8 |  |
| 40 | 80 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 8 | vendor offset (inferred) |
| 41 | 81 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 89 99 89 99 99 88 89 89 89 a9 88 88 88 78 66 66 66` | 8 |  |
| 42 | 82 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 9 | vendor offset (inferred) |
| 43 | 83 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 18` | 9 |  |
| 44 | 84 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 9 | vendor offset (inferred) |
| 45 | 85 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 89 89 8a 98 89 89 88 99 98 98 88 88 88 78 77 67 66` | 9 |  |
| 46 | 86 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 10 | vendor offset (inferred) |
| 47 | 87 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 19` | 10 |  |
| 48 | 88 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 10 | vendor offset (inferred) |
| 49 | 89 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 98 98 89 98 89 89 88 99 88 99 88 88 88 78 77 77 66` | 10 |  |
| 50 | 90 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 11 | vendor offset (inferred) |
| 51 | 91 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 1a` | 11 |  |
| 52 | 92 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 11 | vendor offset (inferred) |
| 53 | 93 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 88 99 88 98 89 89 88 89 98 98 88 88 88 78 77 77 77` | 11 |  |
| 54 | 94 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 12 | vendor offset (inferred) |
| 55 | 95 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 1b` | 12 |  |
| 56 | 96 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 12 | vendor offset (inferred) |
| 57 | 97 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 88 89 89 88 89 89 88 98 88 98 88 88 88 88 78 77 77` | 12 |  |
| 58 | 98 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 13 | vendor offset (inferred) |
| 59 | 99 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 1c` | 13 |  |
| 60 | 100 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 13 | vendor offset (inferred) |
| 61 | 101 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 88 89 88 88 89 89 88 98 88 98 88 88 88 88 88 77 77` | 13 |  |
| 62 | 102 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 14 | vendor offset (inferred) |
| 63 | 103 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 1d` | 14 |  |
| 64 | 104 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 14 | vendor offset (inferred) |
| 65 | 105 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 88 88 89 88 98 88 88 98 88 88 88 88 88 88 88 88 77` | 14 |  |
| 66 | 106 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 15 | vendor offset (inferred) |
| 67 | 107 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 1e` | 15 |  |
| 68 | 108 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 15 | vendor offset (inferred) |
| 69 | 109 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 88 88 88 98 88 88 88 98 87 89 88 88 88 88 88 88 78` | 15 |  |
| 70 | 110 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 16 | vendor offset (inferred) |
| 71 | 111 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 1f` | 16 |  |
| 72 | 112 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 16 | vendor offset (inferred) |
| 73 | 113 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 88 88 88 88 88 88 88 88 88 98 88 88 88 88 88 88 88` | 16 |  |
| 74 | 114 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 17 | vendor offset (inferred) |
| 75 | 115 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 00` | 17 |  |
| 76 | 116 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 82` | 17 | vendor offset (inferred) |
| 77 | 117 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `b3 0c` | 17 |  |
| 78 | 118 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 17 | vendor offset (inferred) |
| 79 | 119 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 4 | `ff 00 00 00` | 17 |  |
| 80 | 120 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 80` | 17 | vendor offset (inferred) |
| 81 | 121 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 3 | `ff 00 00` | 17 |  |
| 82 | 122 | 0x05 DCS_WRITE | dcs short | 1 | 0 | 0 | 120 | 2 | `11 00` | 18 | MIPI_DCS_EXIT_SLEEP_MODE; pad byte not sent |
| 83 | 123 | 0x15 DCS_WRITE1 | dcs short | 0 | 0 | 0 | 0 | 2 | `51 ff` | 19 | MIPI_DCS_SET_DISPLAY_BRIGHTNESS |
| 84 | 124 | 0x15 DCS_WRITE1 | dcs short | 0 | 0 | 0 | 0 | 2 | `53 24` | 19 | MIPI_DCS_WRITE_CONTROL_DISPLAY |
| 85 | 125 | 0x15 DCS_WRITE1 | dcs short | 0 | 0 | 0 | 0 | 2 | `55 00` | 19 | MIPI_DCS_WRITE_POWER_SAVE |
| 86 | 126 | 0x15 DCS_WRITE1 | dcs short | 0 | 0 | 0 | 0 | 2 | `35 00` | 19 | MIPI_DCS_SET_TEAR_ON |
| 87 | 127 | 0x05 DCS_WRITE | dcs short | 1 | 0 | 0 | 20 | 2 | `29 00` | 19 | MIPI_DCS_SET_DISPLAY_ON; pad byte not sent |

#### Sharp FTE716 — qcom,mdss-dsi-off-command (dsi_hs_mode, lines 129–131, 18 bytes, 2 packets, 2 batches)

| # | line | type | class | last | vc | ack | wait ms | dlen | payload | batch | note |
|---:|---:|---|---|---:|---:|---:|---:|---:|---|---:|---|
| 0 | 130 | 0x05 DCS_WRITE | dcs short | 1 | 0 | 0 | 50 | 2 | `28 00` | 0 | MIPI_DCS_SET_DISPLAY_OFF; pad byte not sent |
| 1 | 131 | 0x05 DCS_WRITE | dcs short | 1 | 0 | 0 | 120 | 2 | `10 00` | 1 | MIPI_DCS_ENTER_SLEEP_MODE; pad byte not sent |

#### Sharp FTE716 — qcom,mdss-dsi-displayon-command (dsi_hs_mode, lines 135–135, 9 bytes, 1 packets, 1 batches)

| # | line | type | class | last | vc | ack | wait ms | dlen | payload | batch | note |
|---:|---:|---|---|---:|---:|---:|---:|---:|---|---:|---|
| 0 | 135 | 0x05 DCS_WRITE | dcs short | 1 | 0 | 0 | 32 | 2 | `29 00` | 0 | MIPI_DCS_SET_DISPLAY_ON; pad byte not sent |

#### Sharp FTE716 — qcom,mdss-dsi-displayoff-command (dsi_hs_mode, lines 134–134, 9 bytes, 1 packets, 1 batches)

| # | line | type | class | last | vc | ack | wait ms | dlen | payload | batch | note |
|---:|---:|---|---|---:|---:|---:|---:|---:|---|---:|---|
| 0 | 134 | 0x05 DCS_WRITE | dcs short | 1 | 0 | 0 | 32 | 2 | `28 00` | 0 | MIPI_DCS_SET_DISPLAY_OFF; pad byte not sent |

#### AUO FTE716 — qcom,mdss-dsi-on-command (dsi_lp_mode, lines 39–184, 1768 bytes, 144 packets, 21 batches)

| # | line | type | class | last | vc | ack | wait ms | dlen | payload | batch | note |
|---:|---:|---|---|---:|---:|---:|---:|---:|---|---:|---|
| 0 | 40 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 0 | vendor offset (inferred) |
| 1 | 41 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 5 | `2a 00 00 04 37` | 0 | DCS opcode in GENERIC long write |
| 2 | 42 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 0 | vendor offset (inferred) |
| 3 | 43 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 5 | `2b 00 00 07 f7` | 0 | DCS opcode in GENERIC long write |
| 4 | 44 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 0 | vendor offset (inferred) |
| 5 | 45 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 4 | `ff 87 16 01` | 0 |  |
| 6 | 46 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 80` | 0 | vendor offset (inferred) |
| 7 | 47 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 3 | `ff 87 16` | 0 |  |
| 8 | 48 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 a0` | 1 | vendor offset (inferred) |
| 9 | 49 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 8 | `c0 00 02 02 09 01 16 07` | 1 |  |
| 10 | 50 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 d0` | 1 | vendor offset (inferred) |
| 11 | 51 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 8 | `c0 00 02 02 09 01 16 07` | 1 |  |
| 12 | 52 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 82` | 1 | vendor offset (inferred) |
| 13 | 53 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 10 | `a5 33 02 0c 00 00 22 25 55 77` | 1 |  |
| 14 | 54 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 b0` | 1 | vendor offset (inferred) |
| 15 | 55 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 16 | `c2 85 02 01 0b 80 84 03 01 0b 80 83 04 01 0b 80` | 1 |  |
| 16 | 56 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 c0` | 1 | vendor offset (inferred) |
| 17 | 57 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 6 | `c2 82 05 01 0b 80` | 1 |  |
| 18 | 58 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 d0` | 1 | vendor offset (inferred) |
| 19 | 59 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 14 | `c3 00 0a 0a 00 00 00 00 01 04 00 5a 00 00` | 1 |  |
| 20 | 60 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 e0` | 1 | vendor offset (inferred) |
| 21 | 61 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 14 | `c3 00 0a 0a 00 00 00 00 01 04 00 5a 00 00` | 1 |  |
| 22 | 62 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 80` | 1 | vendor offset (inferred) |
| 23 | 63 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 7 | `ce 25 00 90 00 78 ff` | 1 |  |
| 24 | 64 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 8d` | 1 | vendor offset (inferred) |
| 25 | 65 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `f5 21` | 1 |  |
| 26 | 66 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 90` | 1 | vendor offset (inferred) |
| 27 | 67 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 11 | `c5 44 19 23 00 88 01 32 52 55 50` | 1 |  |
| 28 | 68 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 98` | 1 | vendor offset (inferred) |
| 29 | 69 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 3 | `c3 11 11` | 1 |  |
| 30 | 70 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 d1` | 1 | vendor offset (inferred) |
| 31 | 71 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `cf 02` | 1 |  |
| 32 | 72 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 d7` | 1 | vendor offset (inferred) |
| 33 | 73 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `cf 02` | 1 |  |
| 34 | 74 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 8a` | 1 | vendor offset (inferred) |
| 35 | 75 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `a5 00` | 1 |  |
| 36 | 76 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 a1` | 1 | vendor offset (inferred) |
| 37 | 77 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 8 | `ce 00 02 02 08 01 16 07` | 1 |  |
| 38 | 78 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 90` | 2 | vendor offset (inferred) |
| 39 | 79 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 9 | `ce 00 8c 0d 9b 00 5c 00 75` | 2 |  |
| 40 | 80 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 80` | 2 | vendor offset (inferred) |
| 41 | 81 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 9 | `cb 00 00 00 00 50 00 00 00` | 2 |  |
| 42 | 82 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 90` | 2 | vendor offset (inferred) |
| 43 | 83 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 16 | `cb 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` | 2 |  |
| 44 | 84 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 a0` | 2 | vendor offset (inferred) |
| 45 | 85 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 16 | `cb 00 00 00 00 00 00 00 c0 00 00 00 00 00 00 00` | 2 |  |
| 46 | 86 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 c0` | 2 | vendor offset (inferred) |
| 47 | 87 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 16 | `cb 15 00 15 00 15 15 15 15 2a 2a 00 00 15 15 15` | 2 |  |
| 48 | 88 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 d0` | 2 | vendor offset (inferred) |
| 49 | 89 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 16 | `cb 15 15 15 55 55 00 00 2a 00 00 00 00 00 00 00` | 2 |  |
| 50 | 90 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 f0` | 2 | vendor offset (inferred) |
| 51 | 91 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 9 | `cb 33 ff 00 3f f0 3c 00 00` | 2 |  |
| 52 | 92 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 81` | 2 | vendor offset (inferred) |
| 53 | 93 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 13 | `f3 ff ff c0 ff fc c0 ff ff c0 ff fc c0` | 2 |  |
| 54 | 94 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 90` | 2 | vendor offset (inferred) |
| 55 | 95 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c5 77` | 2 |  |
| 56 | 96 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 94` | 2 | vendor offset (inferred) |
| 57 | 97 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 5 | `cf 00 00 10 20` | 2 |  |
| 58 | 98 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 a4` | 2 | vendor offset (inferred) |
| 59 | 99 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 5 | `cf 00 07 01 80` | 2 |  |
| 60 | 100 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 d0` | 2 | vendor offset (inferred) |
| 61 | 101 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `cf 08` | 2 |  |
| 62 | 102 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 80` | 2 | vendor offset (inferred) |
| 63 | 103 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 11 | `ca 80 bf ff 99 ff 80 ff 00 00 00` | 2 |  |
| 64 | 104 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 2 | vendor offset (inferred) |
| 65 | 105 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 10` | 2 |  |
| 66 | 106 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 2 | vendor offset (inferred) |
| 67 | 107 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 90 9a 9a 9a c8 ba 99 aa 8b 98 88 88 88 57 55 55 55 55` | 2 |  |
| 68 | 108 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 3 | vendor offset (inferred) |
| 69 | 109 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 11` | 3 |  |
| 70 | 110 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 3 | vendor offset (inferred) |
| 71 | 111 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 90 8a 8b 8a b9 aa 99 aa aa 87 88 88 88 67 66 56 55 55` | 3 |  |
| 72 | 112 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 4 | vendor offset (inferred) |
| 73 | 113 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 12` | 4 |  |
| 74 | 114 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 4 | vendor offset (inferred) |
| 75 | 115 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 90 99 9a 89 b9 aa 89 aa 9a 88 88 88 88 67 66 66 56 55` | 4 |  |
| 76 | 116 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 5 | vendor offset (inferred) |
| 77 | 117 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 13` | 5 |  |
| 78 | 118 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 5 | vendor offset (inferred) |
| 79 | 119 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 90 99 99 99 b8 a9 99 a9 a9 78 88 88 88 67 66 66 66 66` | 5 |  |
| 80 | 120 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 6 | vendor offset (inferred) |
| 81 | 121 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 14` | 6 |  |
| 82 | 122 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 6 | vendor offset (inferred) |
| 83 | 123 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 8a 9a 98 a8 b9 98 a8 a9 88 88 88 88 78 66 66 66 66` | 6 |  |
| 84 | 124 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 7 | vendor offset (inferred) |
| 85 | 125 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 15` | 7 |  |
| 86 | 126 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 7 | vendor offset (inferred) |
| 87 | 127 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 99 99 89 a8 a9 89 a9 99 79 88 88 88 78 77 66 66 66` | 7 |  |
| 88 | 128 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 8 | vendor offset (inferred) |
| 89 | 129 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 16` | 8 |  |
| 90 | 130 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 8 | vendor offset (inferred) |
| 91 | 131 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 99 99 88 99 a9 98 98 a9 79 88 88 88 78 77 77 66 66` | 8 |  |
| 92 | 132 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 9 | vendor offset (inferred) |
| 93 | 133 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 17` | 9 |  |
| 94 | 134 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 9 | vendor offset (inferred) |
| 95 | 135 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 89 99 89 98 a9 88 99 99 79 88 88 88 78 77 77 77 66` | 9 |  |
| 96 | 136 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 10 | vendor offset (inferred) |
| 97 | 137 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 18` | 10 |  |
| 98 | 138 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 10 | vendor offset (inferred) |
| 99 | 139 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 98 a8 88 89 a9 88 99 89 79 88 88 88 78 77 77 77 77` | 10 |  |
| 100 | 140 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 11 | vendor offset (inferred) |
| 101 | 141 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 19` | 11 |  |
| 102 | 142 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 11 | vendor offset (inferred) |
| 103 | 143 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 98 98 89 88 a9 88 98 99 88 88 88 88 88 77 77 77 77` | 11 |  |
| 104 | 144 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 12 | vendor offset (inferred) |
| 105 | 145 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 1a` | 12 |  |
| 106 | 146 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 12 | vendor offset (inferred) |
| 107 | 147 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 98 98 88 98 89 89 98 98 89 88 88 88 88 78 77 77 77` | 12 |  |
| 108 | 148 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 13 | vendor offset (inferred) |
| 109 | 149 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 1b` | 13 |  |
| 110 | 150 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 13 | vendor offset (inferred) |
| 111 | 151 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 88 89 88 98 a8 88 98 88 89 88 88 88 88 88 78 77 77` | 13 |  |
| 112 | 152 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 14 | vendor offset (inferred) |
| 113 | 153 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 1c` | 14 |  |
| 114 | 154 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 14 | vendor offset (inferred) |
| 115 | 155 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 88 98 88 88 99 88 88 89 98 88 88 88 88 88 88 77 77` | 14 |  |
| 116 | 156 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 15 | vendor offset (inferred) |
| 117 | 157 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 1d` | 15 |  |
| 118 | 158 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 15 | vendor offset (inferred) |
| 119 | 159 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 88 98 87 89 98 88 88 98 98 88 88 88 88 88 88 78 77` | 15 |  |
| 120 | 160 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 16 | vendor offset (inferred) |
| 121 | 161 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 1e` | 16 |  |
| 122 | 162 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 16 | vendor offset (inferred) |
| 123 | 163 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 88 88 88 88 89 88 88 98 97 88 88 88 88 88 88 88 78` | 16 |  |
| 124 | 164 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 17 | vendor offset (inferred) |
| 125 | 165 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 1f` | 17 |  |
| 126 | 166 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 17 | vendor offset (inferred) |
| 127 | 167 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 19 | `c7 80 88 88 88 88 88 88 88 88 98 88 88 88 88 88 88 88 88` | 17 |  |
| 128 | 168 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 18 | vendor offset (inferred) |
| 129 | 169 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `c6 00` | 18 |  |
| 130 | 170 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 b0` | 18 | vendor offset (inferred) |
| 131 | 171 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 4 | `ca 02 0f 00` | 18 |  |
| 132 | 172 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 82` | 18 | vendor offset (inferred) |
| 133 | 173 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `b3 0c` | 18 |  |
| 134 | 174 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 00` | 18 | vendor offset (inferred) |
| 135 | 175 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 4 | `ff 00 00 00` | 18 |  |
| 136 | 176 | 0x29 GEN_LWRITE | generic long | 0 | 0 | 0 | 0 | 2 | `00 80` | 18 | vendor offset (inferred) |
| 137 | 177 | 0x29 GEN_LWRITE | generic long | 1 | 0 | 0 | 0 | 3 | `ff 00 00` | 18 |  |
| 138 | 178 | 0x15 DCS_WRITE1 | dcs short | 0 | 0 | 0 | 0 | 2 | `51 ff` | 19 | MIPI_DCS_SET_DISPLAY_BRIGHTNESS |
| 139 | 179 | 0x15 DCS_WRITE1 | dcs short | 0 | 0 | 0 | 0 | 2 | `53 24` | 19 | MIPI_DCS_WRITE_CONTROL_DISPLAY |
| 140 | 180 | 0x15 DCS_WRITE1 | dcs short | 0 | 0 | 0 | 0 | 2 | `55 00` | 19 | MIPI_DCS_WRITE_POWER_SAVE |
| 141 | 181 | 0x15 DCS_WRITE1 | dcs short | 0 | 0 | 0 | 0 | 2 | `35 00` | 19 | MIPI_DCS_SET_TEAR_ON |
| 142 | 182 | 0x05 DCS_WRITE | dcs short | 1 | 0 | 0 | 120 | 2 | `11 00` | 19 | MIPI_DCS_EXIT_SLEEP_MODE; pad byte not sent |
| 143 | 183 | 0x05 DCS_WRITE | dcs short | 1 | 0 | 0 | 20 | 2 | `29 00` | 20 | MIPI_DCS_SET_DISPLAY_ON; pad byte not sent |

#### AUO FTE716 — qcom,mdss-dsi-off-command (dsi_hs_mode, lines 185–188, 18 bytes, 2 packets, 2 batches)

| # | line | type | class | last | vc | ack | wait ms | dlen | payload | batch | note |
|---:|---:|---|---|---:|---:|---:|---:|---:|---|---:|---|
| 0 | 186 | 0x05 DCS_WRITE | dcs short | 1 | 0 | 0 | 120 | 2 | `10 00` | 0 | MIPI_DCS_ENTER_SLEEP_MODE; pad byte not sent |
| 1 | 187 | 0x05 DCS_WRITE | dcs short | 1 | 0 | 0 | 50 | 2 | `28 00` | 1 | MIPI_DCS_SET_DISPLAY_OFF; pad byte not sent |

#### AUO FTE716 — qcom,mdss-dsi-displayon-command (dsi_hs_mode, lines 192–192, 9 bytes, 1 packets, 1 batches)

| # | line | type | class | last | vc | ack | wait ms | dlen | payload | batch | note |
|---:|---:|---|---|---:|---:|---:|---:|---:|---|---:|---|
| 0 | 192 | 0x05 DCS_WRITE | dcs short | 1 | 0 | 0 | 32 | 2 | `29 00` | 0 | MIPI_DCS_SET_DISPLAY_ON; pad byte not sent |

#### AUO FTE716 — qcom,mdss-dsi-displayoff-command (dsi_hs_mode, lines 191–191, 9 bytes, 1 packets, 1 batches)

| # | line | type | class | last | vc | ack | wait ms | dlen | payload | batch | note |
|---:|---:|---|---|---:|---:|---:|---:|---:|---|---:|---|
| 0 | 191 | 0x05 DCS_WRITE | dcs short | 1 | 0 | 0 | 32 | 2 | `28 00` | 0 | MIPI_DCS_SET_DISPLAY_OFF; pad byte not sent |

