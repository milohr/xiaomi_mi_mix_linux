# Xiaomi Mi MIX native Linux port

Target: **original Xiaomi Mi MIX (`lithium`)**, Qualcomm MSM8996 family.
Goal: reproducible native Linux boot, then display, input, storage and networking,
using pmbootstrap packaging. A lithium lk2nd board selector and Linux DTS now
build, but have not yet been validated on hardware.
This repository is independent of the MediaTek Redmi `flare` project.

## Start here

1. Read [device evidence](docs/DEVICE.md) and [phased plan](docs/PLAN.md).
2. Run `python3 scripts/preflight.py` and `python3 -m unittest discover -s tests -v`.
3. Run `python3 scripts/collect_device.py --serial YOUR_ADB_SERIAL` for a fresh,
   restricted read-only inventory of an authorized Android device.
4. Review [source acquisition](docs/SOURCES.md) and pin candidate revisions.
5. Use [handoff](docs/HANDOFF.md) to resume work and record phase evidence.

[research/project.json](research/project.json) records facts, provenance, unknowns,
source leads and phase gates. It is the machine-readable project inventory.

## Layout

| Path | Purpose |
|---|---|
| `docs/` | Engineering plan, device facts, recovery and packaging requirements |
| `research/` | Reviewed JSON evidence and source inventory |
| `scripts/` | Host checks, read-only ADB collection, builds, panel decoding, hashing |
| `bootloader/` | Original lithium lk2nd selector and reviewable source patch |
| `tests/` | Parser bounds, packet preservation and malformed-input tests |
| `examples/` | Synthetic panel data, explicitly not device initialization data |
| `packaging/` | Package implementation requirements, pending verified baseline |
| `kernel/` | DTS/driver/config work area with evidence requirements |
| `sources/` | Ignored external source checkouts |
| `artifacts/` | Ignored device dumps, firmware, logs and manifests |
| `build/` | Ignored generated outputs |

## Current status

Live ADB and Fastboot evidence identifies `lithium`, confirms an unlocked
bootloader, and establishes matching stock recovery artifacts. Phase 1 is
complete. Phase 2 pinned the MSM8996 kernel baseline, added a lithium selector
to lk2nd, and produced a reproducible 372,752-byte image. Phase 3 is complete
offline: a lithium DTS (console, UFS, USB peripheral, keys, reserved memory)
checked against the stock DTB, plus a kernel config fragment; see
[Phase 3 findings](docs/PHASE3_FINDINGS.md). Phase 4 (packaging) is next.
Hardware validation is still pending. Mainline boot has **not** been demonstrated. No flash commands
are automated.

The project patch adds lithium to lk2nd's MSM8996 bundle from verified stock DTB
IDs. The existing scorpio image is not a lithium image. See
[Phase 2 findings](docs/PHASE2_FINDINGS.md) and
[boot-path decision](docs/BOOT_PATH.md).

A parallel display track has an offline, compile-tested panel driver draft and
an lk2nd panel-selection draft, neither hardware tested. See
[display status](docs/DISPLAY.md).
