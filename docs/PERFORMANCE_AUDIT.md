# Performance audit (2026-10-19, kernel r44, device r22)

Measured on the phone over SSH with the session idle unless noted. Tools: `systemd-analyze`,
`dd`, UFS sysfs, `/proc` sampling, a KWin script logging `windowAdded` times, `perf record`
(test install), glmark2 (test install).

| Area | Finding | Verdict |
|---|---|---|
| Storage (UFS 2.0) | Idles at HS-G1 (power saving); under load HS-G3, 1 lane (stock DT: `lanes-per-direction = 1`). 461 MB/s sequential read, 4 KiB random QD1 26 MB/s (~6,300 IOPS) | fine |
| Root filesystem | ext4 on a loop device over userdata (`sda15`), direct I/O, `mq-deadline` on the disks | fine |
| Memory | 3.6 GB; zram swap compressing 5.7:1, swappiness 180, page-cluster 0. Earlier pressure came from the GPU leak (fixed r41) and 18 browser tabs | fine |
| GPU | Mesa a5xx binning overflow corrupted other buffers; worked around with `nobin` (+ `sysmem` for browsers). glmark2 146/116/75 (normal/nobin/sysmem), 2D desktop scene 46/46/55 fps | fixed (workaround) |
| App launch | Clock 2.0–2.9 s, Dolphin 2.1–2.5 s, Calculator 3.5–4.2 s to the first window; warm launches are not faster. Calculator: 4.19 s CPU for 4.19 s wall, big core at 2.34 GHz throughout; perf: musl dynamic linker 20 %, kernel (page faults) 22 %, Qt QML+Core 31 % | CPU-bound; ~40 % is library loading/relocation under musl. No device-side fix |
| Boot | 14.5 s kernel+initramfs + 10.4 s to graphical. The kernel is done at ~2.5 s; the initramfs spends ~3.9 s before looking for root (udev settle, splash, a `check_keys` loop that polls in 1 s steps) and ~6 s after (e2fsck + resize2fs on the 114 GB root every boot, mount). `lithium-modem` (36 s) runs in the background | improvable (~5 s), low priority |
| Idle CPU | `lithium-usb-current` started as a systemd unit on every USB power-supply change (34 times in 10 min while charging) and rewrote the gadget state each time. Now a udev RUN with state memory: systemd 30 ticks/20 s -> 1 tick/30 s | fixed (device r22) |
| Interrupts at idle | arch timer ~300/s, IPIs (call/work/resched) ~770/s, RPM glink 19/s, ath10k 10/s | normal |

Still to look at: audio `q6asm CMD 10bcd timeout` at boot; power-supply change events every
few seconds while charging (charger IRQ handlers call `power_supply_changed`).
