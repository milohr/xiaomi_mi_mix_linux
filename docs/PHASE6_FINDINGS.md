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
- *(Fixed in r29, see "GPU faults found and fixed" above.)* **Chromium/QtWebEngine on the Adreno 530 faults** (`gpu fault ... WRITE PERMISSION`) with
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
- **Headphones need their own DSP stream** (patch 0018, device r13). Sharing MultiMedia1
  with the speaker forced UCM conflicting devices, so each jack event made PipeWire switch
  profiles and reopen the PCM; through its `_ucmNNNN.` names that intermittently failed with
  -EINVAL and left only a dummy sink. MultiMedia2 (hw:N,1) feeds the headphones; both DSP
  routes are connected in the verb's EnableSequence (a front end opens only with a back end
  routed), so Speaker and Headphones are two sinks of one HiFi profile. WirePlumber ranks the
  headphone sink 1100 (ACP gives it 728 by PCM number, the speaker 1000), so it wins only while
  its route is available. Hardware: five plug/unplug switches, stream followed, 0 failed opens.
- **Browser GPU faults are not Chromium's**: Firefox (WebRender) triggers the same
  translation faults. They come from the browser's GPU process (none with Chromium on the
  CPU, none from KWin), run 0.8–1 MB past the end of a 2.5 MiB buffer (a 1088×544 BGRA
  raster tile, bucket-rounded), and survive `FD_MESA_DEBUG=sysmem/noubwc/nobin/nolrz/
  flush/noblit`, `QTWEBENGINE_FORCE_USE_GBM=0` and `--gpu-rasterization-msaa-sample-count=0`
  (single zero-fault runs were luck; counts are rate-limited at 10/20). Rendering looks
  right. Angelfish stays on the CPU; Firefox runs on the GPU.
- **Venus works** (patch 0019, firmware r1): lithium's signed firmware from the stock
  `NON-HLOS.bin` `/image` (venus.mdt + .b00–.b04, packaged as `venus.mbn`). Decoder and
  encoder at /dev/video0 and /dev/video1. A 720p H.264 clip decodes bit-exact against
  ffmpeg's software decoder (300/300 frames) with 0.33 s instead of 4.24 s of CPU; mpv with
  `hwdec=v4l2m2m-copy` plays 720p60 YouTube (H.264 via yt-dlp) at about 10–15 % CPU. A
  Wi-Fi failure seen once while testing was a coincidence on a truncated test image.

## Sensors and the GPU fault hunt (2026-10-18, kernel r26–r28, firmware r2)

- **Sensors work** (patch 0020, firmware r2): the SLPI was simply not enabled. Stock supplies:
  vdd_px = PM8994 LVS2 (fed from S4), vdd_cx via the power domain. The shared stock NON-HLOS
  holds slpi_a1/a4/a7; lithium's DT names **a4** (we had packaged a1, never loaded). The
  in-kernel sensor registry (`qcom_sns_reg`) serves this phone's `persist/sensors/sns.reg`
  as `qcom/sensors/sns.reg-xiaomi,lithium`; the tree's `qcom_smgr` then exposes
  `qcom-smgr-accel/gyro/mag/pressure` as IIO devices. iio-sensor-proxy finds the
  accelerometer and Plasma Mobile shows auto-rotate, which follows the phone. No light or
  proximity sensor on the SLPI (lithium's proximity is ultrasonic).
- **GPU faults found and fixed** (patch 0022, kernel r29): `msm_gem_close()` tore down an
  object's mapping in the closing context's VM. A5xx has no per-process address spaces, so
  that VM is the GPU's global one, and a buffer shared through dma-buf (a client's window
  in the compositor, frames between a browser's processes) was unmapped while the other
  process still used it at the old address. Seen as translation faults on every rotation
  and whenever a browser drew on the GPU (each faulting address inside a live buffer in one
  GEM-list snapshot, unmapped in the next), and as write-permission faults and misplaced
  page content once the stale address went to a new read-only buffer. Preemption was ruled
  out first (patch 0021, `msm.enable_preemption=0`: same faults). With 0022: 0 faults in 8
  rotations (20 in 4 before), 0 in three QtWebEngine-on-GPU runs and in Firefox. Device r14
  drops `--disable-gpu`: web views render on the GPU again.
- New this boot series, unexplained: two `pclk0_clk_src: rcg didn't update its configuration`
  warnings while the panel driver loads (screen works).

## Microphones and idle wake-ups (2026-10-19, kernel r30–r31, device r15–r16)

- **Microphones work** (patch 0024, UCM). Three faults stacked up:
  - Capture recorded digital zeros: only playback pulled in the codec MCLK (via RX_BIAS), so the
    decimators ran unclocked. The DT now routes `"AIF1 CAP", "MCLK"`.
  - A capture on MultiMedia1 stopped the speaker playback on the same front end (I/O error).
    Capture has its own front end now, MultiMedia3 (`hw:N,2`, capture only); MultiMedia1/2
    are playback only.
  - The mics are **ADC1 and ADC3** (AMIC1/AMIC3, MIC BIAS4), not the stock mixer's "main-mic"
    ADC4: with the speaker playing a 1 kHz tone, ADC1/ADC3 record RMS ~1300–1800, ADC4/ADC5
    stay at the noise floor. Both mics form one stereo source (SLIM TX7/TX8). The machine
    driver runs SLIMBUS_0_TX as stereo regardless, and with only one codec TX port behind it the
    DSP sometimes refused to start the port (`AFE enable for port 0x4001 failed`).
  - The codec TX routing is set for the whole UCM verb: PipeWire probes the PCM before any
    device EnableSequence runs.
- **q6asm-dai reopened a stopped stream** (patch 0023): TRIGGER_STOP marks the stream STOPPED
  but leaves it open in the DSP; `prepare()` only closed RUNNING streams, so stop → prepare
  (PipeWire suspending/resuming a node) opened it again and the DSP answered ADSP_EALREADY
  (error 9). Likely also behind the headphone-profile EINVAL seen with r23.
- **Idle wake-ups:** a measured idle lock screen draws almost nothing (KWin/locker/plasmashell
  ~0%); the 25% in the snapshot was the lock screen just appearing. Two constant sources:
  - The accelerometer streamed at 200 Hz around the clock (≈200 SLPI messages/s plus the
    kworker and schedutil wake-ups behind them): `qcom_smgr` ignored the requested rate and
    always used the sensor maximum. Patch 0025 keeps the requested rate; `92-lithium-sensors.rules`
    sets the accelerometer to 10 Hz before iio-sensor-proxy starts. Measured: 10 Hz, SLPI
    interrupts below 30/s.
  - On a wall charger (BC1.2 DCP) the USB gadget kept its pull-up on and dwc3 logged an
    "Erratic Error" event 229 times a second. `lithium-usb-current` now soft-disconnects the
    gadget on DCP and reconnects it otherwise: 0/s after replugging, charging unchanged.
- Venus decodes VP9 as well as H.264 (mpv: ~20% CPU against 85% in software for 720p30);
  `/etc/mpv/mpv.conf` (device r15) turns on `hwdec=v4l2m2m-copy` and skips AV1 for YouTube.
- Wi-Fi power save is already on (NetworkManager default).

## Modem bring-up and an IPA boot loop (2026-10-19, kernel r30–r32)

- **The modem boots and registers** (Movistar, PS attached):
  - TZ only assigns the modem its stock range (0x89c00000), so reserved memory follows stock (patch 0027).
  - rmtfs serves file copies of modemst1/modemst2/fsg (`rmtfs -s -o /var/lib/rmtfs`, never `-P`);
    the packaged `rmtfs.service` (`-r -P`) is masked.
  - The modem crashed ("fatal error without message") until a 1 KiB zero `modem_fsc` cookie existed:
    lithium has no fsc partition.
  - The USIM stays "detected" until a provisioning session is activated
    (`qmicli --uim-change-provisioning-session=...primary-gw-provisioning,aid=<USIM AID>`).
- **Boot loop with ipa2-lite** (kernel r32): every boot reset at about 20 s, before rmtfs starts the
  modem, with nothing in the persisted journal after about 19 s. The same image boots normally with
  `ipa2-lite` blacklisted, so loading the IPA v2.5 driver resets the SoC (likely an access to the IPA
  block without the bus votes stock makes). Recovered through stock fastboot (Volume Down + Power,
  product `MSM8996_A8`) by writing `artifacts/p6/boot-partition-r30.img`. ipa2-lite stays blacklisted
  (`/etc/modprobe.d/zz-no-ipa2-lite.conf`) until its probe is understood.
- **Cameras identified** (see docs/HARDWARE_COVERAGE.md): rear OV16880 (OFilm), front OV5675.

## IPA fixed, both cameras, colour tuning (2026-10-19, kernel r36, device r18, firmware r3)

- **The IPA boot loop was the BAM:** stock DT has `qcom,ipa-bam-remote-mode`, and downstream
  registers the IPA BAM as `SPS_BAM_MGR_DEVICE_REMOTE` (owned by the modem/TZ). ipa2-lite reset
  and reprogrammed the BAM's global registers, which resets the SoC. Patch 0033 adds
  `qcom,bam-remote-mode` (skip the BAM globals) and the IPA v2.5 header processing-context
  partition (zeroed, `IPA_LOCAL_PKT_PROC_CNTXT_BASE` = its offset, as downstream v2.5). The
  driver then probes and creates `rmnet_ipa0`; ModemManager builds the modem from qrtr0 and
  rmnet_ipa0.
- **ipa2-lite must load only while the modem runs:** loading it with the modem stopped resets
  the SoC (the BAM is unpowered). It stays blacklisted; `lithium-modem.service` (device r18)
  waits for the modem, activates the USIM provisioning session, loads ipa2-lite and restarts
  ModemManager. rmtfs runs file-backed through a drop-in on the packaged `rmtfs.service`;
  `lithium-rmtfs-setup` copies modemst1/modemst2/fsg once and creates the zero `modem_fsc`.
  Modem firmware and `modem_pr` are in firmware r3. Data itself is untested (no SIM inserted).
- **Front camera (OV5675):** mainline driver at 19.2 MHz MCLK; libcamera's simple pipeline with
  the GPU software ISP (patch 0028).
- **Rear camera (OV16880):** new driver (patch 0029). Rockchip's register set produced no frames
  on this module (no SOF at any lane rate); the stock library's tables do: init plus 2336x1752
  binned (768 Mbps/lane) and 4672x3504 (1272 Mbps/lane), 24 MHz MCLK, 4 lanes (patch 0030).
- **Focus motor:** DW9763, ID 0xf9, the DW9761 register map; dw9719 accepts it (patch 0031),
  stock SAC mode 4 and prescale 0x3c from DT (patch 0032), positions 0-1023. libcamera's simple
  pipeline has no autofocus algorithm.
- **Colour tuning** (`/usr/share/libcamera/ipa/simple/{ov16880,ov5675}.yaml`, device r17):
  black level 4096 (BLC target 0x40, confirmed by a dark rear frame: median 65), and the six
  colour matrices of each stock `libchromatix_*_default_preview_3a.so` (zones 7000/6500,
  6200/6100, 4600/4300, 2950/2700, 2400/2300 K).
- **Speed:** frames reach about 15 fps after the software ISP because the GPU cannot import the
  CAMSS buffers (`eglCreateImageKHR` fails on the 3240-byte stride); CAMSS writes RDI frames in
  frame-based mode, which has no stride, so a fix means line-based RDI in CAMSS.


## Torch and vibration (2026-10-19, kernel r40)

- **Torch:** PMI8994's flash block reports type 0x18, subtype 0x01: the first-generation
  register map, which mainline leds-qcom-flash (subtypes 0x03/0x04/0x07) does not drive. New
  `leds-qcom-flash-v1` (patch 0035) implements torch mode with the downstream sequence (secure
  unlock 0xd0 = 0xa5, torch 0xe4 = 0, channel current 0x42/0x43 at level 0-15, max current
  0x41, module enable 0x46 = 0x80, strobe 0x47); LED `white:torch`, which Plasma Mobile's
  flashlight finds by name. Verified with the face-down rear camera: raw mean 67 (black) with the
  torch off, saturated (p99 = 1023) with it on. The driver lives in `drivers/leds/flash/`, which
  is only built with `CONFIG_LEDS_CLASS_FLASH`: r37 dropped the module silently, r38 sets it to m.
- **Vibration:** the tree's `qcom-spmi-haptics` only accepted LRA actuators; lithium's is an
  ERM. Patch 0037 accepts ERM and limits the auto-resonance setup to LRAs; the DT (0038) takes
  stock's square wave, 5263 us play rate and brake pattern, in the driver's buffer mode. The
  driver's 400 mA current limit is too low for an ERM: its start-up current raised the
  short-circuit interrupt ~3000 times a second and the driver then disabled the module ("Short
  circuit persists"). r40 uses stock's 800 mA and caps vmax at stock's 3000 mV (the magnitude
  scale reached 3.6 V): a 2 s feedbackd vibration now raises 10 short-circuit-status interrupts,
  the normal ~50 ms status, and none at boot.

## Quick Charge groundwork and NFC (2026-10-19, kernel r42–r43)

- **PMI8994 ADC** (0040, stock vadc@3100): USB/DC input behind 1/20; the driver also needs the
  625 mV/1.25 V/GND/VDD reference channels ("Please define 1.25V channel" without them). USBIN
  reads 4.95 V on a 5 V DCP.
- **Charger** (0041): `voltage_now` on qcom-smbchg-usb from the "usbin" channel, looked up on first
  use so the built-in charger never waits for the ADC module; 2.5 s after a DCP the driver logs
  `USBIN_HVDCP_STS`. Also fixes the AICL warning printing an uninitialized error.
- **HVDCP state left by the bootloader**: `CHGPTH_CFG` 0x19 (HVDCP detection on, 9 V adapter
  selected), `USBIN_CHGR_CFG` 0x02 (5 V/9 V continuous allowed), `USBIN_HVDCP_STS` 0x00 with the
  current wall charger (a plain DCP). With a QC charger the PMIC may go to 9 V by itself; first
  test with the user present.
- **QC2 adapter found, and a trap** (r44): with the USB gadget kept off D+/D- (normally its pull-up
  spoils the handshake), a QC charger answered (`USBIN_HVDCP_STS` 0x12: HVDCP, 9 V selected) but the
  input stayed at 5 V and AICL settled at its lowest step (ICL 300 mA, battery -660 mA while
  plugged in). This PMIC needs downstream's `force_9v_hvdcp()`. 0041 now selects 5 V and reruns
  AICL by default (full-current DCP); `qcom_smbchg.hvdcp_9v=1` runs the downstream sequence and
  keeps 9 V only if USBIN measures 8.4–9.6 V. The check also runs at probe (charger present at boot).
- **Lifetime review** (r44): ipa2-lite leaked every TX packet it refused (IPv6 ND/MLD sent straight to
  rmnet_ipa0) and deleted NAPI contexts before unregister_netdev() (0043); OV16880 grabbed the
  flip controls even when stream start failed (0029); the smbchg HVDCP work was cancelled after the
  power supply it uses on teardown (0041).
- **NFC** (0042): PN548 on BLSP2 QUP2 (0x75b6000) at 0x28, IRQ GPIO 9, VEN 12, firmware 21 (pulled
  up as stock). `nxp-nci` binds; `nfctool -d nfc0 -1` powers it up (NCI init OK; MIFARE, FeliCa,
  ISO-DEP, Jewel, NFC-DEP). Left powered off.
- **Bluetooth address at boot** (device r21): the r20 script still failed at boot. systemd-rfkill
  restores a saved Bluetooth block while the script runs, after its one check, and btmgmt's error
  went to /dev/null. The unit now orders after systemd-rfkill, and the script rechecks the block
  and retries for 10 s, logging btmgmt's message on failure.

## GPU buffer leak (2026-10-19, kernel r41)

- Patch 0022 (r29) left global-VM mappings in place on handle close "until the object is freed",
  but each VMA holds a reference to its object, so no buffer drawn through the shared A5xx VM was
  ever freed: 15,442 objects / 4.5 GB after 30 min, 26,194 / 8.3 GB after an hour, swap (5.4 GB
  zram) full, 86 MB available. Browsing was sluggish from memory starvation, not CPU.
- r41 tears the global-VM mapping down in `msm_gem_vma_put()` when `vma_ref` (open handles,
  dma-buf exports, framebuffers) drops to zero, after waiting for the GPU. `scripts/soak.sh`
  (5 rounds of opening/closing pages in Angelfish) now holds GPU memory at 392–396 MB.
- The status-bar block corruption still appears on r41, so it is a separate bug. Under test: Mesa
  with UBWC off (`FD_MESA_DEBUG=noubwc` for plasmashell and its apps).

## Mobile data (2026-10-19, kernel r39–r40, device r19–r20)

- **Works**: Movistar Colombia (732123) over UMTS. NetworkManager profile with APN
  `internet.movistar.com.co` (user/password `movistar`) connects at boot; ping ~70 ms, a 10 MB
  download at 2.2 Mbit/s, browsing in Firefox and Angelfish.
- **QMAPv4**: ModemManager offers the modem QMAPv5, QMAPv4, QMAP in turn and this modem takes
  QMAPv4 (MAP checksum header on uplink, trailer on downlink). For IPA ports ModemManager takes
  the rmnet checksum flags from `device/feature/{rx,tx}_offload` (mainline ipa sysfs); ipa2-lite
  had none, so the link had no flags and the modem read the first 4 bytes of each IP packet as
  the checksum header (its tx counter: 1024 bytes per 1028-byte packet; nothing came back).
  Patch 0039 configures the endpoints as downstream rmnet_ipa does with checksums (uplink 8-byte
  header + CS offload UL, metadata offset 1 word; downlink CS offload DL) and reports `MAPv4`.
  Plain QMAP (forced with `qmicli --wda-set-data-format`) also worked, but ModemManager
  switches back to QMAPv4 at the first connection after it starts.
- **SIM slot**: lithium-modem provisions the USIM of whichever slot holds a card (it hard-coded
  slot 1; the SIM sat in slot 2) and waits up to 30 s for the card to be read.
- **LTE**: the modem prefers LTE, but LTE-only mode finds only Tigo (732103) cells; Movistar's
  LTE appears to be on bands this China-market model lacks (it has 1/3/5/7/8/38-41).
- **DNS over USB**: a hand-made `usb-internet.service` from early bring-up (not packaged) sent all
  DNS over usb0 with routing domain `~.`; with Wi-Fi off and the cable in, no name resolved.
  Disabled on the phone.
- **Bluetooth address**: with Bluetooth soft-blocked at boot the controller is not registered
  with mgmt and lithium-bt-address failed; it now unblocks for the moment and restores the block.

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
