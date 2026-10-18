# P5 — first native boot: review packet

Status: **draft for review. Nothing here is authorized yet and no device write
has been made.** Each step marked ⚠ needs the user's explicit go at the time it
runs. Image hashes marked _pending_ are filled in once the P4 build is exported
and audited (`artifacts/pmb-export`).

The plan follows [BOOT_PATH.md](BOOT_PATH.md): lk2nd goes into the **recovery**
partition, Android's **boot** partition is never written, and Linux runs from
RAM only. Every claim about lk2nd and the pmOS initramfs below was read from the
pinned sources (lk2nd `8b46487c`, pmaports `dfb010f5`); references at the end.

## What changes on the phone

| Partition | Change | Undo |
|---|---|---|
| recovery (64 MiB) | ⚠ stock recovery → lk2nd | Step R: write the stock recovery image back |
| boot, system, userdata, everything else | **nothing** | — |

Linux is loaded into RAM over USB. Its startup ramdisk only reads partition
labels; with no pmOS partitions present it mounts nothing.

## Images

| Image | Size | SHA-256 | Role |
|---|---|---|---|
| `artifacts/build/lk2nd-gcc/build-lk2nd-msm8996/lk2nd.img` | 372,752 | `b845d9b612bc08e457b9aa89b23850620e3284467fde4deef999955dac19444d` | P2-reviewed lk2nd, goes into recovery |
| `artifacts/pmb-export/p5-boot.img` | _pending_ | _pending_ | Linux, booted from RAM only |
| `artifacts/stock/audit/recovery.img` | 29,406,542 | `1c22cdc539f975333dfda9fbeda568dc2e84b01d00120f2d9d7872af70e09abd` | stock recovery, for Step R |
| `artifacts/stock/audit/boot.img` | — | `fe99b14be190522ab185726c6ae62317f68c5bb6c7e0cd4a2af318d861978f17` | stock boot; only if boot were ever written (it is not) |

**Recommendation: use the P2 lk2nd above, not the display track's panel-select
draft** (`artifacts/build/lk2nd-panel`, `2fd4f27a…`). The draft only renames
the panel for a future Linux panel driver; simplefb doesn't need it, and one
change per experiment keeps a failure readable.

### Building `p5-boot.img`

It is the audited pmbootstrap `boot.img` with four debug arguments appended to
the header command line. Nothing else changes; the script checks that every
byte outside the command-line field is identical.

```sh
python3 -I scripts/make_p5_bootimg.py artifacts/pmb-export/boot.img \
    artifacts/pmb-export/p5-boot.img \
    lk2nd.pass-ramoops=zap console=tty0 clk_ignore_unused pd_ignore_unused
python3 -I scripts/audit_bootimg.py artifacts/pmb-export/p5-boot.img \
    packaging/pmaports/device/testing/device-xiaomi-lithium/deviceinfo
```

| Argument | Why |
|---|---|
| `lk2nd.pass-ramoops=zap` | lk2nd adds a ramoops region to Linux's device tree and clears it first. After a crash, lk2nd hands back the dead kernel's console (`fastboot oem ramoops console`). The kernel config has `PSTORE_RAM=y`. |
| `console=tty0` | kernel messages on the screen; the console UART is not reachable |
| `clk_ignore_unused pd_ignore_unused` | lk2nd's simplefb node lists no clocks or power domains, and the multimedia clock controller is enabled in the SoC tree. Without these, Linux turns the "unused" display clocks off a few seconds in and the picture freezes. |

## Never, during P5

- **Never hold Volume Up and Volume Down together at power-on.** lk2nd reads that
  as the emergency download (EDL) key sequence and reboots into it.
- **No `flash`, `erase` or `oem reboot-edl` in lk2nd's fastboot.** lk2nd maps the
  first 512 KiB of **boot** as its own `lk2nd` partition and the rest as `boot`,
  even while running from recovery: a flash there writes into Android's boot image.
- No `flash_all*`, no `flashing lock`, no GPT, boot, persist or modem writes.
- Always pass `-s 13a20a34`, so a command can't reach another device.

## Host preparation (no device change)

1. Verify every hash in the table: `sha256sum`.
2. `adb devices` shows `13a20a34` (stock Android, as now).
3. Have a camera or phone ready to photograph the screen at each step.

## Step A — ⚠ lk2nd into recovery

```sh
adb -s 13a20a34 reboot bootloader                 # or Volume Down + Power
fastboot -s 13a20a34 getvar product               # expect MSM8996_A8 (stock fastboot)
fastboot -s 13a20a34 flash recovery artifacts/build/lk2nd-gcc/build-lk2nd-msm8996/lk2nd.img
```

Then enter recovery **without booting Android first**: hold Power until the
phone turns off (about 10 s), then hold **Volume Up + Power**, the key path
already tested in P1. Release the keys when the screen lights up.

Booting Android in between is not dangerous, but MIUI may restore its stock
recovery from the boot image at boot (common Android behaviour; not verified on
this unit). If lk2nd is gone afterwards, that is a restore, and Step A repeats.

**Expected:** lk2nd starts. With no key held it scans for an `extlinux.conf`
(read-only), finds the stock Android image does not start at boot + 512 KiB, and
stops in its own fastboot. The screen may show the lk2nd menu or stay on the
splash.

```sh
fastboot devices                                  # serial listed
fastboot -s 13a20a34 getvar lk2nd:compatible      # expect xiaomi,lithium
fastboot -s 13a20a34 getvar lk2nd:version
fastboot -s 13a20a34 getvar lk2nd:panel           # names the panel variant (P6)
fastboot -s 13a20a34 oem log && fastboot -s 13a20a34 get_staged p5-lk2nd.log
```

If the serial differs in lk2nd, use the one `fastboot devices` shows. If
`fastboot devices` is empty, check `lsusb` for `18d1:d00d` (lk2nd) and the host's
udev permissions before anything else.

**Failure:** black screen and no fastboot, or a reboot loop → hold Power until
off → **Volume Down + Power** → stock fastboot → Step R.

## Step B — ⚠ Linux from RAM

From lk2nd's fastboot:

```sh
fastboot -s 13a20a34 boot artifacts/pmb-export/p5-boot.img
```

**Expected, in order:**

1. lk2nd adds the simplefb and ramoops nodes and starts the kernel. The splash
   stays on and kernel text appears on it (simplefb + fbcon).
2. Within a few seconds a USB network interface appears on the host and gets
   172.16.42.2 (pmOS `unudhcpd`). Check with `ip -br addr`.
3. The ramdisk waits about 30 s for a pmOS boot partition, shows **"boot
   partition not found!"**, and starts its debug shell. This is the expected end
   point: it meets P5's "diagnostic shell" gate.

```sh
telnet 172.16.42.1        # pmOS debug shell
```

Collect in the shell (copy the output off the telnet session):
`cat /proc/cmdline`, `dmesg`, `cat /proc/device-tree/model`,
`ls /sys/bus/platform/drivers/simple-framebuffer`, `cat /proc/fb`,
`ls /dev/sd*`, `cat /sys/kernel/debug/regulator/regulator_summary` (if debugfs
is mounted), `ls /sys/fs/pstore`.

**Failure modes:**

| Seen | Meaning | Next |
|---|---|---|
| back in lk2nd fastboot at once | lk2nd refused the image | `oem log` + `get_staged`; no reboot needed |
| text appears, then freezes or black | kernel crash or hang | photo; wait 60 s; hold Power until it restarts, then Volume Up + Power → lk2nd → `fastboot oem ramoops console` + `get_staged p5-console.txt` |
| black screen from the start, no USB | early crash or display lost | same as above (ramoops survives a warm restart) |
| shell on screen, no USB network | gadget/PHY issue | photo of the screen; `dmesg` on screen if a keyboard-less shell allows; then Step C |

Investigate one failure at a time; change one thing per attempt.

## Step C — back to Android

In the debug shell `reboot -f`, or hold Power until it restarts. The boot
partition was never touched, so the stock bootloader starts Android. Confirm:

```sh
adb -s 13a20a34 wait-for-device
adb -s 13a20a34 shell getprop sys.boot_completed    # 1
adb -s 13a20a34 shell getprop ro.build.version.incremental   # V11.0.2.0.OAHMIXM
```

## Step R — ⚠ restore stock recovery

When the experiment ends, or if lk2nd misbehaves:

```sh
sha256sum artifacts/stock/audit/recovery.img      # must match the table
adb -s 13a20a34 reboot bootloader                 # or Volume Down + Power
fastboot -s 13a20a34 getvar product               # MSM8996_A8
fastboot -s 13a20a34 flash recovery artifacts/stock/audit/recovery.img
fastboot -s 13a20a34 reboot
```

Then confirm the stock recovery menu once with Volume Up + Power and reboot to
system, as in P1. This step is the reason P1 kept the exact stock image.

## Decisions for the user

1. Authorize Step A (the only partition write).
2. Keep lk2nd in recovery between sessions, or run Step R after each one.
3. Later, not now: where the pmOS root filesystem lives. A booting system needs
   a partition, and every option wipes something (userdata or system). P5 only
   needs the debug shell above.

## Evidence

- Keys and EDL: lk2nd `app/aboot/aboot.c` (`aboot_init`, both volume keys →
  `EMERGENCY_DLOAD`; Volume Up → recovery; Volume Down → fastboot).
- Boot split: lk2nd `lk2nd/project/lk2nd.mk` (`LK2ND_PARTITION_BASE = boot`, 512 KiB).
- No-key path: `lk2nd/boot/boot.c` (extlinux scan) then `boot_linux_from_mmc`,
  falling back to fastboot.
- Reboot reason read and cleared: `platform/msm_shared/reboot.c`
  (`check_hard_reboot_mode`, `USE_PON_REBOOT_REG=1` for msm8996).
- Ramoops: `lk2nd/ramoops/ramoops.c` (`lk2nd.pass-ramoops`, `oem ramoops console`);
  logs: `lk2nd/fastboot/misc.c` (`oem log`); identity: `lk2nd/device/device.c`.
- Download limit 512 MiB: `target/msm8996/meminfo.c`.
- Initramfs: pmaports `main/postmarketos-initramfs/init.sh` and
  `init_functions.sh` (`setup_usb_network`, `wait_partition` 30 × 1 s,
  `fail_halt_boot` → `debug_shell`, telnetd on 172.16.42.1:23).
- Stock bootloader has no `boot` command: [PHASE2_FINDINGS.md](PHASE2_FINDINGS.md).
