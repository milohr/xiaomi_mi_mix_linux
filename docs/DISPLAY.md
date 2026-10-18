# Display track — status and next steps

Parallel to Phase 3; prepares Phase 6. Updated 2026-10-17. Nothing here has
run on hardware and no device write happened. Read this with the audit in
[research/delegated/display-audit](../research/delegated/display-audit/HANDOFF.md).

## What is ready

| Item | State | Where |
|---|---|---|
| Panel evidence audit | Complete, hashes re-verified (`sha256sum -c SHA256SUMS`) | `research/delegated/display-audit/` |
| Installed variant | Sharp FTE716 on this unit (live cmdline) | `research/hardware-map.json` |
| Panel driver draft | Sharp + AUO in one driver; compiles `W=1` clean against the pinned kernel; checkpatch 0/0 | `kernel/panel-draft/` |
| Stream check | All 236 packets (Sharp 88+2, AUO 144+2) match stock bytes, DCS/generic class and waits | `scripts/verify_panel_draft.py` |
| lk2nd panel selection | Draft patch `0002`, builds, decoded DTB checked | `bootloader/lk2nd/0002-…patch` |
| Reproduction | One script regenerates, verifies and compile-tests | `scripts/build_panel_draft.sh` |

Build hashes and tool pins: [display-draft-build.json](../research/display-draft-build.json).

**Not ready:** nothing displays yet. The driver needs a Linux DTS panel node,
WLED, LAB/IBB regulators and working native MDP5/DSI. All of these are Phase 6
work that depends on the first boot (P5).

## Findings from this pass

1. **lk2nd already solves the simple-framebuffer geometry problem.** The
   reviewed Phase 2 image (`b845d9b6…`) contains lk2nd's cont-splash and
   simplefb modules (strings `lk2nd.pass-simplefb`, `cont-splash@%08x`;
   `config.h`: `WITH_LK2ND_DISPLAY`, `LK2ND_DISPLAY_CONT_SPLASH`, `MDP5`).
   With `lk2nd.pass-simplefb` on the Linux command line, lk2nd reads the live
   MDP5 SSPP address, stride and format left by aboot and writes a
   `simple-framebuffer` node into the Linux DTB at boot
   (`lk2nd/display/simplefb.c`, `cont-splash/pipe.c`). Options: `xrgb8888`,
   `rgb565`, `autorefresh`, `relocate`. So the Phase 3 DTS should **not**
   hard-code a simplefb node; it only has to keep `cont_splash_mem` reserved.
   Unverified until lk2nd runs on lithium.
2. **lk2nd can tell Sharp from AUO.** lk2nd parses the stock
   `mdss_mdp.panel=1:dsi:0:<node>` argument (`lk2nd/device/2nd/parse-cmdline.c`),
   publishes it as `fastboot getvar lk2nd:panel`, and with a `lk2nd,panel`
   node rewrites the Linux panel's compatible. Patch `0002` maps
   `qcom,mdss_dsi_sharp_fte716_1080p_video` → `xiaomi,lithium-sharp-fte716` and
   the AUO node → `xiaomi,lithium-auo-fte716`. The Linux DTS panel node must
   then carry `compatible = "xiaomi,lithium-panel"`. This resolves audit
   unknown 2 for Linux purposes. How aboot detects the panel stays unknown,
   but it no longer matters.
3. **Correction to the audit's inferred mode flags.** Audit §7 suggests
   `MIPI_DSI_MODE_VIDEO_SYNC_PULSE`. In mainline's MSM DSI driver, downstream
   `qcom,mdss-dsi-h-sync-pulse = 1` maps to `MIPI_DSI_MODE_VIDEO_HSE`, which is
   what lmdpdg emits. The draft uses `VIDEO | VIDEO_BURST | VIDEO_HSE |
   CLOCK_NON_CONTINUOUS`. Non-continuous follows from the absent
   `force-clk-lane-hs`, and EoT stays on because `tx-eot-append` is present.
4. **DCS helpers would have changed the wire format.** Default lmdpdg turns
   stock `15 51 ff` into `mipi_dsi_dcs_set_display_brightness_multi(0x00ff)`,
   which sends `51 ff 00` as a long 0x39 packet. The draft is generated with
   `--dumb-dcs`, so DCS packets are sent byte-exact.
5. **The 0x29 → 0x23 question is unchanged and still needs hardware.** 59 Sharp
   and 93 AUO 2-byte generic long writes go out as short 0x23. The pinned kernel
   exports no explicit-type transfer, and no mainline panel driver calls
   `host->ops->transfer` directly. Test 0x23 first. Many FocalTech/Orisetech-style
   panels in mainline accept it.
6. **Stock 0-parameter DCS packets are zero-padded** (`05 … 11 00`). Mainline
   sends the same two bytes from a 1-byte payload. The verifier treats them as equal.
7. **Android fbdev, read-only over ADB on the unrooted stock unit:**
   `/sys/class/graphics/fb0` `virtual_size` 1080,4080, `stride` 4352,
   `bits_per_pixel` 32. That is Android's double-buffered surface, **not** the
   aboot splash scan-out, so it does not set any simplefb value. The device is
   not rooted (`su` absent, `ro.build.type=user`), so MDP registers aren't
   readable from Android.

## What the draft driver contains (and doesn't)

- Init/off tables: verbatim lmdpdg output from stock `boot.img.dtb-5`
  (`a2968fa1…`), the DTB the live unit selects.
- Power order from audit §5: vddio, 1 ms; lab; ibb, 10 ms; enable GPIO,
  100 µs; reset `<1 10>,<0 1>,<1 10>`; init in LP. Off: off cmds in HS; enable
  low; reset asserted; ibb (5 ms), lab, 10 ms, vddio.
- Supplies `vddio`, `lab`, `ibb`; `reset-gpios` (TLMM 8, active low);
  optional `enable-gpios` (TLMM 47, role unverified).
- **Not included:** TLMM 48 backlight enable, TLMM 40 `vddr` fixed regulator,
  TE (TLMM 10) and WLED. These belong in the DTS/backlight bindings once
  their roles are proven. `xiaomi,lithium-*-fte716` compatibles are
  provisional and have no dt-binding yet.
- Mainline has no PMI8994/PMI8996 LAB/IBB binding (only `qcom,pmi8998-lab-ibb`).
  Until it exists, `lab`/`ibb` resolve to dummy regulators and the bootloader's
  rails must stay on.

## Next steps, in order

1. **P3 (other agent):** keep `cont_splash_mem` reserved and the display off.
   Add no simplefb node. Plan to boot with `lk2nd.pass-simplefb` instead.
2. **Before the first lk2nd flash (P5 review):** decide whether to ship lk2nd
   with `0002`. It only adds a DT rewrite for Linux boots and changes nothing
   for Android. Rebuild and re-hash if yes.
3. **First lk2nd start (P5), read-only checks:** `fastboot getvar lk2nd:panel`
   (expect the Sharp node), `fastboot oem log` (look for `cont-splash@…`, the
   detected pipe, stride and format), and `fastboot oem parsed-cmdline`.
4. **First Linux boot:** add `lk2nd.pass-simplefb` (try plain first, then
   `xrgb8888`/`autorefresh` if the image is static or wrong). Expect a console on
   the splash buffer. Record the generated node from `/proc/device-tree`.
5. **P6:** dt-binding for the panel, LAB/IBB for PMI8994/6, WLED (stock: 31 V OVP,
   20 mA, strings 0–1), the panel node, then a native MDP5/DSI attempt, with
   the 0x23 test first.

## Host tooling added (rootless, under ignored `artifacts/toolchain/`)

- `lld/` — Arch `lld-23.1.1-1` (sha256 `4c3505d0…`) matching the system
  LLVM 23.1.1. Use the wrapper `lld/bin/ld.lld`; it sets `LD_LIBRARY_PATH`.
- `bc/` — Arch `bc-1.08.2-1` (sha256 `b9e5f0d6…`), needed by kernel `prepare`.
- `venv-lmdpdg/` — Python venv with `pylibfdt` for lmdpdg.
- `sources/lmdpdg` — lmdpdg at `28c4df25628f6241ce925af15637a443ea2b3bb5`.
- `artifacts/build/kernel-panel/` — separate `O=` tree (defconfig plus
  `DRM_MSM=m`), so `kernel-phase3` stays the Phase 3 DTB build.
- `artifacts/build/lk2nd-panel/` — lk2nd built with `0001`+`0002`.
