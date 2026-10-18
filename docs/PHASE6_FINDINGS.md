# Phase 6 findings — storage, USB, the installed system (2026-10-18, in progress)

Status: **postmarketOS is installed on `userdata` and boots by itself at power-on** (lk2nd in
the boot partition, the kernel after it). Storage and USB networking work; ssh as `user` at
172.16.42.1. The rest of P6 (display driver, touch, power) follows. Raw logs: `artifacts/p6/` (ignored). Live partition map:
`research/live-partitions-p6.json`.

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
2. Copy `persist` (`sda12`) read-only; fix the GPT backup header; set the time.
3. Touch (patch 0002, `artifacts/p6/touch-test.sh`), power (`artifacts/p6/lithium-power.dtsi`),
   display (`artifacts/p6/display-plan.md`).
4. Before any `apk upgrade` of the kernel on the phone: check how pmOS's `boot-deploy` writes
   the boot partition on an lk2nd layout, so it doesn't overwrite lk2nd's first 512 KiB.
