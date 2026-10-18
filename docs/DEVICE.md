# Device evidence

## Previously observed through ADB

These values are transcribed from successful collection in this conversation;
the original raw log is not stored here. Refresh using the collector before a
boot experiment. Serial numbers are intentionally omitted from tracked files.

| Property | Observed value |
|---|---|
| Manufacturer / model | Xiaomi / MIX |
| Device / product | lithium / lithium |
| Board platform / hardware | msm8996 / qcom |
| Android / MIUI | 8.0.0 / V11 |
| Security patch | 2018-10-01 |
| Build display ID | OPR1.170623.032 |
| Kernel | 3.18.71-perf-g5edcf86, aarch64 |
| Kernel build date | Wed Oct 23 19:27:12 CST 2019 |
| MemTotal | 3801116 kB |
| ro.boot.flash.locked | 0 |
| ro.boot.verifiedbootstate | orange |
| ro.boot.veritymode | eio |
| ro.oem_unlock_supported | true |
| sys.oem_unlock_allowed | 0 |

The boot properties support an actually unlocked bootloader. The OEM-unlock
setting is a separate policy value. MemTotal is usable RAM, not a physical DRAM
map; it cannot be converted directly into a DTS memory region.

## Phase 3 live corroboration

Read-only live DT and sysfs inspection identifies SoC ID 305, revision 1.1,
`MSM8996pro`, board ID 38 (`0x26`) and PMI8996. The stock bootloader selected
the Sharp FTE716 1080p video panel variant on this unit. Physical DRAM banks and
reserved-memory ranges are recorded in `research/hardware-map.json`.

The stock console UART is `serial@075b0000` on gpio4/5 (not BLSP1 UART2 at
0x7570000, which stock disables as a console). Its external accessibility,
the lk2nd-measured framebuffer values, the populated Type-C chip and the
mainline panel implementation remain unknown. UFS, USB and key wiring are
mapped in `research/hardware-map.json`.

## Main constraints

Scorpio shares a platform but its panel, touch, GPIOs and reserved memory must
not be assumed identical. The project now carries original lithium lk2nd and
Phase 3 Linux DTS patches; neither has been boot-tested on hardware.
