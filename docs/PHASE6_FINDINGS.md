# Phase 6 findings — storage, USB, the installed system (2026-10-18, in progress)

Status: **postmarketOS is installed on `userdata` and boots by itself at power-on** (lk2nd in
the boot partition, the kernel after it). Working on hardware as of kernel r10 / device r4:
UFS, USB networking (`user@172.16.42.1`), **the display on the msm DRM driver** with our FTE716
panel driver (brightness via PMI8994 WLED, screen off/on), **touch** (FT8716, edt-ft5x06),
**Wi-Fi** (QCA6174 hw3.2 on PCIe0, ath10k, up 19 s after boot, `user@192.168.1.96` on the
home network), Sxmo (dwm) and **Phosh** (software rendering until the GPU works). Raw logs:
`artifacts/p6/` (ignored). Live partition map: `research/live-partitions-p6.json`.

## Audio, GPU, USB-C, Bluetooth, charging (2026-10-18, kernel r11–r19)

Hardware facts found by testing, where the stock tree is wrong or silent:

- **TLMM 47/48 are BLSP1 I2C3** (speaker and earpiece amps), not panel enable and
  backlight enable as stock's DSI node claims. With I2C3 on, the panel's `enable-gpios`
  made the panel probe fail and took the whole display down; the panel has no enable GPIO.
- **The speaker amp is a TFA9891** (revision 0x92), though stock names it tfa9890; patch
  0010 adds it to `tfa989x` with NXP's `tfa9891_specific()` init. It is fed by quaternary
  MI2S; the DSP accepts the clock-set API (`Q6AFE_LPASS_CLK_ID_QUAD_MI2S_IBIT`, patch 0007).
- **The TUSB320L interrupt is TLMM 63** (stock lists none): measured low with an interrupt
  pending, high after clearing it. It is at 0x47 on BLSP2 I2C3; 0x67 is unpopulated.
- **GPU_GX needs PMI8994 S2** (`vdd_gfx`, stock 0.4–1.065 V), or the GDSC never turns on and
  the msm DRM device fails to bind with the GPU node enabled (patch 0009).
- **Bluetooth's UART needs `serial1`**: without the alias it became port 0, i.e. the
  console, and `hci_uart` could not open it (patch 0014). Controller 0x00440302 (Rome 3.2),
  generic `rampatch/nvm_00440302`; it is unconfigured until a public address is set, which
  device r9 does from `persist:/wlan_bt/bt.mac` (byte-reversed).
- **Self-powered USB-C docks give no data**: without USB Power Delivery the dock is the
  source, the phone attaches as a device, and the dock keeps its hub off unless it sees a
  powered host. Unpowered docks and devices work automatically. Patch 0013 makes the
  charger refuse OTG boost while USB input is present (the DWC3 enables VBUS on every
  switch to host).
- **Charging**: fuel-gauge current sign inverted for upower (0008); 3.2 A cap; the USB-C
  current advertisement raises the input limit (device r8). Dock data ports deliver about
  0.5 A. No Quick Charge (HVDCP) in mainline `qcom-smbchg`.
- **Chromium/QtWebEngine on the Adreno 530 faults** (`gpu fault ... WRITE PERMISSION`) with
  every GPU flag combination tried; web views render on the CPU (device r8,
  `environment.d`). Phosh/KWin GL is fine.
- **Suspend works (kernel r22)**: s2idle only (no PSCI SYSTEM_SUSPEND); wakes on the RTC
  alarm and on the Power key (`pm8941_pwrkey`); suspend 0.40 s, resume 0.58 s; display,
  Wi-Fi and battery come back. Two kernel bugs were behind the hangs:
  - **PCIe0's GDSC was powered off under a live link** (patch 0016). The qcom PCIe driver
    keeps the link of a controller with an active device up, but genpd turned the GDSC off in
    the noirq phase; the phone reset at once. `pm_test=platform` passed only with the Wi-Fi
    device removed. The PCIe GDSCs are now `PWRSTS_RET_ON`, as on newer Qualcomm SoCs.
  - **mdp5 lost its hwpipe after a resume** (patch 0015). The plane state saved at suspend
    still named DMA0, so the resume commit kept it without assigning it in the global state;
    every later plane disable hit `WARN_ON` in `mdp5_pipe_release()` (-EINVAL): the screen
    could not be turned off (blank but lit) and `msm_kms_pm_prepare` refused suspend.
  - Crash logs do not survive a reset on this phone: ramoops (lk2nd's region sits inside the
    HDMI splash area 0xb1c00000 and `zap` clears it; a DT node at 0x92900000 stays empty after
    even a clean reboot), so DDR is not retained. Stages were bisected with `pm_test` instead.
  - **CPU idle works (device r11)**: PSCI 1.0 firmware in OS-initiated mode ("failed to
    set PC mode" is harmless with only a per-CPU state); `standalone-power-collapse` is
    used heavily. Screen off, awake: 172–181 mA with it, 240–278 mA without. Suspend and
    Wi-Fi under load (≈ 130 Mbit/s) unaffected. Device r11 also drops lk2nd's ramoops
    (useless here) and the Sxmo profile.
  - Harmless: `qcom-wled` warns "Unbalanced enable for IRQ" once per boot (the bootloader
    leaves WLED on, the driver's brightness starts at 0, so the OVP IRQ is enabled twice).

## Headphone jack, browser GPU faults (2026-10-18, kernel r23–r24, device r12)

- **Jack detection works by the jack switch** (patch 0017). WCD9335 has no MBHC ADC, and
  mainline's generic `wcd-mbhc-v2` only classifies plugs with it: every measurement timed
  out and the state flapped. A `mech_only` config reports headphones straight from the
  mechanical switch. Stock's `msm-mbhc-hphl-swh = 1` / `gnd-swh = 1` read **inverted** as
  mainline's "normally closed" properties; the defaults are right. UCM: Headphones
  priority 300 with `JackControl "Headphone Jack"`, so they win while plugged. Headset mic
  detection (downstream "legacy" detection) and button thresholds are still open.
- **Browser GPU faults are not Chromium's**: Firefox (WebRender) triggers the same
  translation faults. They come from the browser's GPU process (none with Chromium on the
  CPU, none from KWin), run 0.8–1 MB past the end of a 2.5 MiB buffer (a 1088×544 BGRA
  raster tile, bucket-rounded), and survive `FD_MESA_DEBUG=sysmem/noubwc/nobin/nolrz/
  flush/noblit`, `QTWEBENGINE_FORCE_USE_GBM=0` and `--gpu-rasterization-msaa-sample-count=0`
  (single zero-fault runs were luck; counts are rate-limited at 10/20). Rendering looks
  right. Angelfish stays on the CPU; Firefox runs on the GPU.
- **Venus**: lithium's signed firmware is on the modem partition, not yet in our firmware
  package; enabling the node without it fails with -2.

## The real display driver and the rest of the day (2026-10-18, kernel r5–r10)

- **Panel** (patch 0003): `panel-xiaomi-lithium-fte716` (lmdpdg tables from stock) on DSI0,
  supplies/pins/VDDR/WLED from stock. LAB/IBB are left as the bootloader set them (as gemini);
  `artifacts/p6/labibb-audit.md` now says GO for a `qcom,pmi8994-lab-ibb` + pmi8998 fallback.
  Found on hardware: WLED OVP uses PMI8994's own table (31000 mV, not WLED4's 31100); the off
  commands must go in `.disable` (in `.unprepare` the msm DSI host waits for a video-done that
  never comes, -110); reset/enable are claimed in the bootloader's running state so the
  picture survives until the first modeset.
- **Simplefb fallback** stays (patch 0001: framebuffer node holding MDSS GDSC/clocks; the MDSS
  node keeps interconnect bandwidth until msm binds). The `msm` blacklist and the xrgb8888
  handover are gone (device r4); an apk-kept `/etc/modprobe.d/lithium-no-msm.conf` from a hand
  install had to be removed by hand.
- **Wi-Fi** (patch 0004): PCIe0 with stock WL_EN (PM8994 GPIO8), rome 3.3 V (GPIO9),
  PERST/WAKE (TLMM 35/37), S3/L30/L28/L12 rails. Board ID is blank (`sub 0000:0000`), so
  `board-2.bin` has no match and lithium's stock `bdwlan30.bin` serves as `board.bin`
  (hand-installed; `firmware-xiaomi-lithium` from P9 packages it). r10 drops
  `FW_LOADER_USER_HELPER_FALLBACK`: each missing optional file had cost 60 s (up at 203 s).
- **Userspace**: Sxmo needs `~/.cache/sxmo/sxmo.nosuspend` (its suspend hangs the phone with
  the backlight on); Phosh needs `WLR_RENDERER=pixman` in `/etc/environment` until the GPU
  works (mesa tries freedreno and phoc does not fall back). Default UI: Phosh (greetd).

## UFS: the link needed load votes on its rails

P5 ended with the UFS link down (`dl_err` storm, no disks). The other agent's audit
(`artifacts/p6/ufs-audit.md`) found our regulators lacked `regulator-allow-set-load`, which
`msm8996-xiaomi-common.dtsi` and the OnePlus tree set on every UFS rail. With the flag the
UFS driver may vote the high-power mode on the rails, and the link comes up at once: six LUNs,
`TOSHIBA THGBF7T0L8LBATAB`, `sda` 123 GB (userdata `sda15`, 114 GiB), the small LUNs with
`system`, `boot`, `modem`, `persist`, `recovery`, `cache` among the 68 labelled partitions.

Kept in the DTS: the flag on **L20 (vcc) and L25 (vccq)** only. L28 and L12 are shared with
the USB PHY; the flag there was tested (U1, U2) and made no difference to UFS.

## USB: a race with UFS's first idle, fixed by holding the reference clock

With UFS working, the USB gadget died in every run (`dwc3: failed to enable ep0out`,
`No resource for ep0out`, endpoint commands timing out), and with it the debug shell. Bisected
over nine RAM-only boots, one change each:

| Boot | Change | UFS | USB |
|---|---|---|---|
| P5 | — (UFS failing) | no | yes |
| U1 | allow-set-load on L20 L25 S4 L28 L12 | yes | no |
| U2 | … on L20 L25 L28 | yes | no |
| U3 | … on L20 L25 | yes | no |
| U4 | U3 + `initcall_blacklist=ufs_qcom_pltform_init` | off | yes |
| U5 | U3 + `snps,usb2-gadget-lpm-disable` | yes | no |
| U7 | U3 + USB PHY `vdd-supply` L28 | yes | no |
| U8 | U3 + `tp_printk trace_event=…` (slower boot) | yes | **yes** |
| U9 | U3 + `&usb3` holds `RPM_SMD_LN_BB_CLK` | yes | **yes** |

U8's trace shows what UFS switches off when it idles at 4–7 s: its own clocks, its PHY's symbol
clocks, the 0.925 V rail, and **`ln_bb_clk`**, the RPM's low-noise XO buffer, whose prepare
count reached zero three times. The USB PHY's reference (`GCC_RX1_USB2_CLKREF_CLK`) is derived
from that buffer (`gcc`'s `cxo2` input is `RPM_SMD_LN_BB_CLK`), yet nothing on this board held
it: the working siblings enable PCIe for Wi-Fi, whose PHY also uses `ln_bb_clk`, so it never
turns off for them. The failure is a race: the initramfs starts the gadget at about 6.5 s,
inside UFS's idle transition; whenever the start fell outside that window (P5 at 9.5 s, U4 without
UFS, U8 slowed by tracing) USB worked.

Fix (U9, now in the DTS and patch 0001): the `qcom,msm8996-dwc3` glue lists
`<&rpmcc RPM_SMD_LN_BB_CLK>` as a sixth clock, so `dwc3-qcom` (`clk_bulk_get_all`) keeps it on
while USB is active. The binding's schema allows five clocks, so the schema check reports the
extra entry; it is a board-level workaround. A proper fix (keeping the buffer on in
`clk-smd-rpm`, or a PHY/glue ordering fix) is being researched (`artifacts/p6/usb-ufs-race.md`
when done).

Verified on U9: the gadget started at 6.67 s, inside the old failure window, and works.

## The screen: simple-framebuffer kept alive (2026-10-18)

After boot the kernel text vanished and the panel stayed lit but black; writes to `/dev/fb0`
showed nothing. Two causes, found one after the other on the installed system:

1. **The MDSS power domain was switched off** (`pm_genpd_summary`: `mdss off-0`): nothing
   claimed it, so genpd powered it down despite `pd_ignore_unused`. Fix: the DTS gets a
   `/chosen/framebuffer` node (`simple-framebuffer`, status disabled) that lk2nd fills in and
   enables instead of creating its own; it carries `power-domains = <&mmcc MDSS_GDSC>` and the
   MDSS AHB/AXI/MDP/VSYNC clocks. Result: domain on, but the screen turned **solid blue**.
2. **Blue is the MDP's underflow colour**: the controller ran but could not fetch. The
   interconnect summary showed `mas_mdp_p0` at zero bandwidth: the `qnoc` providers had
   reached `sync_state` and dropped the bootloader's votes. Fix: `&mdss { status = "okay"; }`
   with the `msm` module blacklisted (`/etc/modprobe.d/lithium-no-msm.conf`, now in
   `device-xiaomi-lithium` r1). The unbound MDSS node holds `mmcc` and `qnoc` `sync_state`
   pending (dmesg: `sync_state() pending due to 900000.display-subsystem`), so the bandwidth
   stays at the bootloader's level.

Verified (`p6fb2-boot.img`, written behind lk2nd in `boot`): kernel text stays, then the
`lithium login:` prompt on the panel. Both fixes are in patch 0001 (kernel r4). This lasts until
a real panel driver replaces simplefb; then the blacklist goes.

Testing without keys: `systemctl reboot --reboot-argument=bootloader` lands in **stock**
fastboot (the stock bootloader handles that reason before lk2nd); `--reboot-argument=recovery`
reaches the lk2nd copy in `recovery`, which boots the kernel from `boot`. Volume Up at lk2nd's
logo only pauses it. So DTB experiments went straight into `boot` (offset 512 KiB, lk2nd left
alone) with the verified full-partition backup `artifacts/p6/boot-partition-current.img`
(`271bbe6a…`) ready for `fastboot flash boot` from stock fastboot.

## Procedure lessons

- `scripts/swap_bootimg_dtb.py` made each DTS experiment a 2-minute build instead of a 2-hour
  package build. The final state still needs a real package build (kernel r2 carries the fix).
- `tp_printk trace_event=…` on the command line, read back through lk2nd's ramoops, gave the
  decisive evidence without a serial console.
- The ramoops console holds about 45 s of a verbose boot; filter the events.

## The rootfs install (2026-10-18)

1. **`fastboot flash userdata` through lk2nd stalled**: chunk 1 of 2 (508 MB of the 1.3 GB
   image, sent as sparse chunks under lk2nd's 512 MiB download limit) showed no progress for
   16 minutes; lk2nd's own UFS writer gives no feedback. Aborted (`artifacts/p6/rootfs-install.log`).
2. **The `dd` route worked in 40 s**: boot the kernel with `pmos.debug-shell` on the command
   line (forces the initramfs shell before it looks at storage, which matters once a partial
   image is on `userdata`), run `setup_usb_storage_configfs /dev/sda15` on the phone, and the
   laptop sees a "Linux File-Stor Gadget" disk of exactly 122,758,868,992 bytes;
   `artifacts/p6/write-rootfs-usbstorage.sh --really` refuses any other disk and runs the `dd`
   (sudo). Verified by reading the first 16 MiB back (same hash) and `blkid` (GPT on sda15).
3. First boot into the rootfs: the initramfs finds the image's sub-partitions by UUID,
   `/` = `loop0p2` (resized to 113.9 GiB), `/boot` = `loop0p1`; systemd, NetworkManager,
   `unudhcpd`, sshd and an `agetty` on the simplefb console; 346 packages; `sudo` needs the
   password; no `doas`. `apk info -e` confirms `linux-postmarketos-qcom-msm8996` and
   `device-xiaomi-lithium`. dmesg: the known P5/P6 lines plus `GPT: Use GNU Parted to correct
   GPT errors` (the image's backup GPT header is not at the end of the 114 GiB partition;
   benign, fix with `sgdisk -e` later) and the clock is wrong (RTC present, no time source yet).
4. **Boot by itself**: from lk2nd's fastboot, `flash lk2nd lk2nd.img` (the first 512 KiB of
   `boot`, `partition-size:lk2nd` 0x80000) and `flash boot p6u9-boot.img` (the rest,
   0x3f80000). Power-on now runs the stock bootloader → lk2nd (from `boot`) → the kernel at
   boot+512 KiB with `lk2nd.pass-simplefb`, no keys. **Android is unbootable** from now on:
   its `boot` partition holds Linux, its `userdata` the rootfs. Restore path: stock `boot.img`
   (`fe99b14b…`) and `recovery.img` (`1c22cdc5…`) from `artifacts/stock/audit/` via stock
   fastboot; `userdata` would need a factory reset. The user accepted erasing Android.

Partition writes in P6: `userdata` (rootfs), `boot` (lk2nd + kernel), `recovery` (lk2nd,
re-flashed after every Android boot during the session). Nothing on the forbidden list.

## lk2nd traps found on the way

- **Stale boot arguments after warm restarts**: lk2nd prepends `lk2nd` to the command line it
  receives, and that copy survives warm restarts and even a short power-off; after some
  dozen restarts the stock arguments were pushed out of the buffer and lk2nd detected the
  board as `oneplus,oneplus3t` (its fallback for an MSM8996 Pro). Our images still boot
  (the simplefb handoff comes from the MDP, not from the board match), so it is cosmetic for
  RAM boots, but anything that relies on `lk2nd:compatible`/`lk2nd:panel` must check for it.
  A long power-off (battery drained of its RAM, minutes) should clear it; not verified.
- lk2nd's fastboot has no `reboot recovery`; the menu's "recovery" and "shutdown" both come
  back to lk2nd while USB power is attached.
- The initramfs reads the volume keys during boot: Volume Up held = halt and dump logs,
  Volume Down held = debug shell. Release Volume Up as soon as the lk2nd menu shows.
- `pkill -f` with a pattern that appears in the caller's own command line kills the caller.

## Firmware from the stock archive (offline)

`artifacts/p6/firmware-extract.md`: from `NON-HLOS.bin` and `BTFM.bin` (read-only, mtools):
the QCA6174 board file `bdwlan30.bin`, the Rome 3.2 Bluetooth patch/NVM, ADSP and SLPI
firmware; `persist.img` in the archive is empty, the live `persist` (`sda12`) holds the
calibration and can be copied read-only from Linux. The phone's `/vendor/firmware` etc. were
root-only on stock MIUI (`artifacts/p6/pull-firmware.log`, 34 readable files).

## Next

1. Full package build (kernel r3: the config additions, the touch patch, and the proper USB
   fix `0004`/`0005` from `artifacts/p6/`, so the sixth clock can leave the DTS); then
   `apk upgrade` on the phone instead of RAM boots.
2. ~~Copy `persist`~~ done 2026-10-18: `sda12` (32 MiB) read over ssh into the ignored
   `artifacts/persist/persist-sda12.img`, sha256 `8595e02f…4e25a32`, same on both sides.
   Time: set from the laptop (`date -s`), but the PMIC RTC rejects writes (`RTC_SET_TIME`:
   No such device; the RTC belongs to the secure world), so every cold boot starts at the RTC's
   1970 count until `systemd-timesyncd` (enabled) reaches a time server. That and the GPT fix
   (`sgdisk -e`; no `sgdisk`/`parted` installed, the kernel says "Alternate GPT is invalid, using
   primary GPT") wait for internet on the phone over USB (laptop NAT).
3. Touch (patch 0002, `artifacts/p6/touch-test.sh`), power (`artifacts/p6/lithium-power.dtsi`),
   display (`artifacts/p6/display-plan.md`).
4. Before any `apk upgrade` of the kernel on the phone: check how pmOS's `boot-deploy` writes
   the boot partition on an lk2nd layout, so it doesn't overwrite lk2nd's first 512 KiB.
