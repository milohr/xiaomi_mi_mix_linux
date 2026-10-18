# Phased execution plan

Each phase has explicit inputs, outputs and an exit gate. A phase is complete only when its evidence is recorded; compilation alone is not hardware validation.

## P0 — Evidence and host readiness

Status: **complete**. Dependencies: None.

1. Refresh restricted ADB inventory; retain failures as evidence.
2. Check host tools and record versions; identify exact Android incremental build and RAM/storage SKU.
3. Keep device identity and stock facts separate from marketing and sibling assumptions.

**Deliverables:** Private raw inventory with timestamp and hashes; Reviewed research/project.json update.

**Exit gate:** Identity lithium and current boot state corroborated; missing/denied reads recorded.

## P1 — Recovery baseline and stock artifacts

Status: **complete**. Dependencies: P0.

1. Locate exact lithium firmware matching the incremental build; verify provenance and digest.
2. Inventory boot/recovery partitions and sizes read-only; inspect boot headers, DTB placement and cmdline offline.
3. Confirm user-data backup and documented stock recovery path; never assume EDL is a usable fallback.
4. Record a concrete restore procedure and image hashes; do not run vendor flash-all scripts.

**Deliverables:** Artifact manifest; Boot-layout report; Recovery checklist.

**Exit gate:** Matching restoration artifacts and a reviewed recovery procedure exist before any boot experiment.

## P2 — Pin source and boot-path baselines

Status: **complete**. Dependencies: P0; P1 before live experiments.

1. Pin Linux, pmaports and pmbootstrap revisions and inspect scorpio packages.
2. Compare shared MSM8996 support and lithium downstream source; build a component support matrix.
3. Audit lk2nd source targets and board matching; add lithium to the existing MSM8996 target from verified stock DTB IDs.
4. Build and inspect the lithium lk2nd image, then retain recovery as the selected first-stage path; do not flash a sibling image.

**Deliverables:** Source lock JSON with full commits; Scorpio/lithium comparison; Boot-path decision record.

**Exit gate:** A supported or explicitly scoped experimental boot path and kernel baseline are chosen with evidence.

## P3 — Hardware map and minimal DTS

Status: **complete** (offline gate; see PHASE3_FINDINGS.md). Dependencies: P1, P2.

1. Extract DTB and panel evidence offline; retain source locations and hashes.
2. Map DRAM, reserved-memory, firmware carveouts, PSCI, interrupt controller, clocks, regulators, USB and storage.
3. Author lithium DTS against upstream bindings; enable only evidenced nodes.
4. Treat simple-framebuffer as bootloader-initialized scanout: verify address, size, stride, format, power retention and non-overlap.
5. Map TLMM separately from PMIC GPIO/MPP and PON keys; verify interrupts, polarity, bias and debounce.

**Deliverables:** Hardware mapping JSON; Original lithium DTS patch; Minimal kernel configuration fragment.

**Exit gate:** DTS compiles and applicable dtbs_check passes; every enabled node has traceable hardware evidence.

## P4 — Reproducible pmbootstrap packages

Status: **pending**. Dependencies: P2, P3.

1. Use pinned pmaports conventions to generate device-xiaomi-lithium/APKBUILD and deviceinfo.
2. Prefer the verified shared MSM8996 kernel package; create a separate kernel package only if justified.
3. Set DTB name, architecture, image packing and flash metadata from the boot-layout audit.
4. Build a minimal rootfs with diagnostic shell and USB networking; record package checksums and build logs.

**Deliverables:** Device package; Kernel patches/config; Reproducible image manifest.

**Exit gate:** Package lint and build pass; kernel/DTB/image fit verified constraints; no placeholder values remain.

## P5 — First recoverable native boot

Status: **pending**. Dependencies: P1, P4.

1. Present exact image hashes, boot method, expected behavior and recovery steps before changing device state.
2. Prefer a validated temporary boot path; keep internal filesystems unmounted or read-only initially.
3. Capture early console, USB diagnostics or pstore where actually available.
4. Establish boot to shell and return to Android; investigate one failure at a time.

**Deliverables:** Boot log; Recovery result; Updated feature matrix.

**Exit gate:** Native Linux reaches a diagnostic shell and the tested recovery path restores normal operation.

## P6 — Display, input and essential power

Status: **pending**. Dependencies: P5.

1. Identify actual panel variant and parse complete downstream commands with transport metadata.
2. Implement panel supply/reset timing and DRM modes; simple framebuffer success does not prove native DSI support.
3. Enable touch and keys from verified bus/GPIO mappings; test full 1080x2040 input coordinates.
4. Validate battery reporting, charging, thermal limits and clean poweroff before sustained use.

**Deliverables:** Panel driver and binding; Input patches; Power validation logs.

**Exit gate:** Stable display and input with monitored safe thermal and charging behavior.

## P7 — Connectivity and acceleration

Status: **pending**. Dependencies: P6.

1. Bring up Wi-Fi/Bluetooth with identified legally usable firmware and calibration data.
2. Validate GPU, audio, sensors and suspend/resume separately.
3. Treat modem, calls and cameras as independent later work; record unsupported features explicitly.

**Deliverables:** Firmware inventory; Feature tests and logs.

**Exit gate:** Chosen usable-device feature set is repeatable; missing functions are documented.

## P8 — Reproducibility and upstream review

Status: **pending**. Dependencies: P7.

1. Rebuild from pinned sources on a clean host and compare artifacts where deterministic.
2. Review DTS bindings, driver style, licensing and package submissions.
3. Publish installation/recovery instructions only for tested variants and methods.

**Deliverables:** Release manifest; Maintainer documentation; Upstream-ready patches.

**Exit gate:** A second clean build and documented repeatable install/recovery validate the milestone.

## Working cadence

For each experiment record question, input hashes, source revisions, exact commands, expected result, actual result and next decision. Keep one hardware change per experiment. Stop dependent work when a gate fails; continue independent source review and host tooling.
