# Display audit handoff

Delegated, read-only, offline audit of 2026-10-17. No device contact, no flashing,
no hardware validation, no existing project file changed, no commit. This handoff
doesn't propose a final DTS or a panel driver. Both wait for the hardware map
and the selected kernel's bindings to be integrated.

## Proven

- **Panel variants.** Lithium's own stock DTBs (boot/recovery indices 4 and 5,
  board-id 38) carry exactly two FTE716 nodes: Sharp
  (`qcom,mdss_dsi_sharp_fte716_1080p_video`) and AUO
  (`qcom,mdss_dsi_auo_fte716_1080p_video`). This unit runs **Sharp** (live,
  `research/hardware-map.json`).
- **Selection.** aboot detects the panel and passes `mdss_mdp.panel=…:dsi:0:<node>`.
  The kernel matches the node name. `qcom,mdss-dsi-panel-id` is unused. The A8 DT
  default (LG SW43101) is overridden and isn't evidence about the panel.
- **Source equals stock for the panels.** Every Sharp (77) and AUO (93) panel property,
  every command stream included, is byte-identical between LineageOS
  `4aa1814c…` and all four lithium stock DTBs.
- **Encoding.** Each packet is a 7-byte `dsi_ctrl_hdr` (`dtype,last,vc,ack,wait_ms,dlen_be16`) plus
  the payload (`mdss_dsi_cmd.h:84-91`, `mdss_dsi_panel.c:1098-1181`). All 8 streams decode
  losslessly. Nothing is malformed, every packet has vc=0 and ack=0, and every stream ends with last=1.
- **Both variants share** 1080×2040 video burst mode, 4 lanes, RGB888 (24 bpp), VC 0,
  HFP/HBP/HPW 46/32/4, VFP/VBP/VPW 16/16/4, 60 Hz, 75×143 mm, the same PHY timings,
  reset `<1 10>,<0 1>,<1 10>` on TLMM gpio8, enable gpio47, backlight-enable gpio48,
  TE gpio10, supplies vddio L14 1.8 V plus LAB/IBB 4.6–6.0 V, WLED backlight 1–4095,
  TE-based ESD, on-commands in LP and off-commands in HS.
- **They differ in** the vendor init (88 vs 144 packets), the DCS order
  (AUO sends 51/53/55/35 *before* sleep-out) and the off order (AUO: sleep-in before display-off).
- **Board conflict.** Stock adds `vddr-supply` (fixed regulator on gpio40, 4 ms) on
  DSI0 and lacks WLED `qcom,en-phase-stag`. So the LineageOS tree isn't the exact stock build.
- **Splash reservation.** 0x83401000 + 0x23ff000. It is in lithium's own DTBs and the live DT,
  and it doesn't overlap any static reserved region (it sits between `dfps_data_mem` and `removed_regions`).
- **Mainline (`1aed438c…`)** has no `struct mipi_dsi_dcs_cmd`. It uses
  `mipi_dsi_multi_context`. Its generic write helper sends 2-byte payloads as
  0x23, not 0x29, and `mipi_dsi_device_transfer` is static.

## Unknown

- Scan-out base inside the reservation, stride, memory pixel format.
- How aboot reads the panel ID (GPIO, mapping), and so how to tell AUO from Sharp in Linux.
- The role of gpio47 and the voltage of the gpio40 "vddr" rail.
- Whether the panel accepts 0x23 instead of 2-byte 0x29 writes (59 Sharp / 93 AUO packets).
- PMI8994/PMI8996 LAB/IBB in mainline (the binding has only `qcom,pmi8998-lab-ibb`).
- Whether native MDP5/DSI takeover works on lithium.

## Safe for the minimal DTS (Phase 3)

- Keep the `cont_splash_mem` 0x83401000/0x23ff000 reservation (and `dfps_data_mem`
  0x83400000/0x1000), so Linux never reuses live scan-out memory.
- Keep the display path disabled, and leave TLMM 8/10/40/47/48, L14 and LAB/IBB
  untouched, so the bootloader's state survives.
- **Not** yet: `simple-framebuffer` (stride and format unproven), panel, DSI or WLED
  nodes. Measure the MDP SSPP address, stride and format read-only on stock, or via lk2nd, first.

## Waits for the panel-driver phase (Phase 6)

- The per-variant command tables (from `panel-*.json`), the DCS ordering and the delays.
- Reset/enable/vddr GPIO polarity and supply bindings; LAB/IBB support; WLED parameters
  (stock: 31 V OVP, 20 mA, 600 kHz, strings 0–1, CABC).
- The 0x29 → 0x23 decision, and the runtime method for detecting the variant.
- The DRM mode (inferred): 144739 kHz, h 1080/1126/1130/1162, v 2040/2056/2060/2076.

## Validation (run 2026-10-17, Python 3.14.8)

```
python3 -m json.tool display-evidence.json: OK
python3 -m json.tool panel-auo-fte716-1080p-video.json: OK
python3 -m json.tool panel-sharp-fte716-1080p-video.json: OK
$ python3 -I verify_commands.py
ok   panel-auo-fte716-1080p-video.json:on_command: 1768 bytes, 144 packets, 21 batches, sha256 f267976ed02b7798
ok   panel-auo-fte716-1080p-video.json:off_command: 18 bytes, 2 packets, 2 batches, sha256 3f39ff46cebe4fb0
ok   panel-auo-fte716-1080p-video.json:displayon_command: 9 bytes, 1 packets, 1 batches, sha256 75286f6cdad3872f
ok   panel-auo-fte716-1080p-video.json:displayoff_command: 9 bytes, 1 packets, 1 batches, sha256 cd2594af4b668506
ok   panel-sharp-fte716-1080p-video.json:on_command: 1085 bytes, 88 packets, 20 batches, sha256 3bdab20aa18e7f32
ok   panel-sharp-fte716-1080p-video.json:off_command: 18 bytes, 2 packets, 2 batches, sha256 c09f10cbd7e0150e
ok   panel-sharp-fte716-1080p-video.json:displayon_command: 9 bytes, 1 packets, 1 batches, sha256 75286f6cdad3872f
ok   panel-sharp-fte716-1080p-video.json:displayoff_command: 9 bytes, 1 packets, 1 batches, sha256 cd2594af4b668506
8/8 streams verified        (exit 0)
```

Other checks:
- A copy with one payload byte changed fails verification (exit 1, "reconstruction differs").
- A negative control, the Sharp source compared with the AUO stock node, reports 9 differing properties.
- The extractor checks every checkout against its pinned commit and every DTB for board-id <38 0>.
- No file outside this directory changed during the audit (checked by mtime).

Pinned source checkouts were fetched to a session scratchpad, not into
`sources/`. To reproduce, fetch them at the pinned commits and run the
command in `DISPLAY_EVIDENCE.md` §10.

## Deliverables

- A. `/home/camiloh/Coding/xiaomi_mi_linux_port/research/delegated/display-audit/DISPLAY_EVIDENCE.md`
- B. `/home/camiloh/Coding/xiaomi_mi_linux_port/research/delegated/display-audit/display-evidence.json`
- C. `/home/camiloh/Coding/xiaomi_mi_linux_port/research/delegated/display-audit/panel-sharp-fte716-1080p-video.json`,
     `/home/camiloh/Coding/xiaomi_mi_linux_port/research/delegated/display-audit/panel-auo-fte716-1080p-video.json`
- D. `/home/camiloh/Coding/xiaomi_mi_linux_port/research/delegated/display-audit/verify_commands.py`
- E. `/home/camiloh/Coding/xiaomi_mi_linux_port/research/delegated/display-audit/SHA256SUMS`
- F. `/home/camiloh/Coding/xiaomi_mi_linux_port/research/delegated/display-audit/HANDOFF.md`
- Generator (supporting): `/home/camiloh/Coding/xiaomi_mi_linux_port/research/delegated/display-audit/extract_evidence.py`
