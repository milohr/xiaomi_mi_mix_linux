# Source acquisition and provenance

- [linux](https://github.com/torvalds/linux): Upstream comparison pinned in `research/source-lock.json`; not the selected build kernel.
- [scorpio-dts](https://raw.githubusercontent.com/torvalds/linux/master/arch/arm64/boot/dts/qcom/msm8996pro-xiaomi-scorpio.dts): Retrieved 2026-10-17; exists, detailed comparison pending.
- [lithium-downstream-device](https://github.com/LineageOS/android_device_xiaomi_lithium): Repository retrieved; not proof of native Linux support.
- [msm8996-downstream-kernel](https://github.com/LineageOS/android_kernel_xiaomi_msm8996): Source lead; exact stock correspondence unverified.
- [lk2nd](https://github.com/msm8916-mainline/lk2nd): Pinned source has an MSM8996 target; the project adds the absent lithium selector.
- [lk2nd-device-list](https://raw.githubusercontent.com/msm8916-mainline/lk2nd/main/Documentation/devices.md): Retrieved 2026-10-17; incomplete for MSM8996 compared with source.
- [pmaports](https://gitlab.postmarketos.org/postmarketOS/pmaports): Pinned canonical package source; scorpio and MSM8996 kernel packages audited.
- [pmbootstrap](https://gitlab.postmarketos.org/postmarketOS/pmbootstrap): Pinned canonical build-tool source.
- [drm-api](https://github.com/torvalds/linux/blob/master/include/drm/drm_mipi_dsi.h): Reviewed; no standard struct mipi_dsi_dcs_cmd.
- [porting-guide](https://wiki.postmarketos.org/wiki/Porting_to_a_new_device): Fetch redirected to wiki.nura.eco and anti-bot page; substantive contents not retrieved.

## Pinning procedure

Clone reviewed repositories into `sources/`; choose a revision intentionally.
Record `git rev-parse HEAD`, remote URL and local patch status in project.json.
Use `scripts/hash_artifacts.py` to hash downloaded inputs and build outputs.
Never use a moving branch as a release pin. External source code retains its
original license. Track original patches, not copied repository snapshots.

The active immutable Phase 2 pins are recorded in
[source-lock.json](../research/source-lock.json). The selected build kernel is
the MSM8996 package tag from pinned pmaports; upstream Linux master is an audit
reference and is not silently substituted for that package source.

## Evidence hierarchy

Prefer current device observations and exact stock artifacts, then corresponding
source, then shared-platform references. A sibling DTS is a hypothesis source,
not proof of lithium wiring. URLs are leads unless the assessment says retrieved.
