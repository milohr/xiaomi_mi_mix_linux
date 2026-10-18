# Touchscreen (prepares P6)

Status: **device tree written and validated offline; not booted.** It is kept
out of the P4 image on purpose: [`kernel/patches/0002-arm64-dts-qcom-xiaomi-lithium-add-touchscreen.patch`](../kernel/patches/0002-arm64-dts-qcom-xiaomi-lithium-add-touchscreen.patch)
applies on top of 0001. Test it as its own change after the first P5 boot.

## Hardware (evidence)

| Item | Value | Source |
|---|---|---|
| Controller | FocalTech **FTE8716**, in-cell (touch built into the panel's driver IC) | stock DTB `fw-upgrade-id1 = 0xe7` = `FTE716_UPGRADE_ID_1` in the downstream driver |
| Bus | `i2c@75ba000` (BLSP2 QUP6, mainline `blsp2_i2c6`), 400 kHz, pins gpio87/88 | stock DTB, `qcom,clk-freq-out = 400000` |
| Address | `0x38` | stock DTB |
| Interrupt | TLMM **125**, **falling edge** | stock `ft5x46_i2c,irq-gpio`; driver `gpio_to_irq(irq_gpio)` + hard-coded `IRQF_TRIGGER_FALLING` |
| Reset | TLMM **89**, active low | stock `ft5x46_i2c,reset-gpio`; driver holds it low, then high |
| Supplies | vdd and vddio: PM8994 **L14**, 1.8 V; the driver also enables PMI8994 LAB/IBB | stock DTB, driver `ft5x46_power_on` |
| Interrupt pin | active: gpio, pull-up, 16 mA; suspend: no bias, 2 mA | stock `ts_active` / `ts_suspend` |
| Size | 1080 × 2040 | stock `x-max` / `y-max` |
| Firmware | stays in the controller's flash; Android reflashes only when the version differs (four files for AUO/Sharp × biel/lens panels) | driver `ft8716_load_firmware` |

**Trap:** the stock node also has `interrupts = <105 …>`. That value is stale and
the stock driver never reads it (gpio105 is an ADV7533 switch pin). Use 125.

Downstream evidence: LineageOS `android_kernel_xiaomi_msm8996` at
`4aa1814c63b82ce67d0ef0434ca510be94bb8284` (source-lock), files read:
`drivers/input/touchscreen/ft5x46/ft5x46_ts.c` (sha256 `84630a91…483f`),
`ft5x46_ts_i2c.c` (`8e443a37…8601`), `include/linux/input/ft5x46_ts.h` (`81ecdac9…c5bc`).
Not kept in Git.

## Mainline

- Driver: `edt-ft5x06` already supports `focaltech,ft8716` (generic FocalTech
  register layout, 10 points). No new driver and no firmware file needed.
- Close mainline example: `sdm845-xiaomi-beryllium-ebbg.dts` (FT8719 in-cell).
- **Kernel config gap:** the pinned pmaports `linux-postmarketos-qcom-msm8996`
  config has `# CONFIG_TOUCHSCREEN_EDT_FT5X06 is not set`. Touch needs it
  (`=m` is enough), so the kernel package config has to change; see
  [`kernel/touch.config`](../kernel/touch.config).

## What patch 0002 adds

- `blsp2_i2c6` enabled at 400 kHz with `touchscreen@38`: interrupt, reset,
  supplies, pin states and size as in the table.
- PM8994 **L14** described at 1.8 V and `regulator-always-on`. P3 left L14 out
  so nothing could switch it off under the bootloader splash; always-on keeps
  that promise. LAB/IBB stay undescribed (mainline has no PMI8994 LAB/IBB
  driver), so they remain as the bootloader left them.
- `ts-int-default-state` / `ts-int-sleep-state` for gpio125. The stock DTB has
  no pin state for the reset line, so none is added.

## Validation (offline, 2026-10-18)

- `git apply --check` on the pinned tree with 0001: clean.
- `scripts/build_lithium_dtb.sh` with KERNEL_OUT=`artifacts/build/kernel-touch`:
  DTB `a5cd319af4619892d267aa12db1ad0cb5888a374b581563c163a65b1ad4a6355`,
  66,840 bytes. `CHECK_DTBS`: the same 8 warnings as P3 (SoC/PMIC includes),
  none from the touch nodes. The P3 verifier still passes.
- `scripts/verify_touch_dtb.py BUILT STOCK`: 14/14 checks against the stock
  DTB; fails on the P3 DTB (no touch), as it should.
- Patch 0002 sha256 `ec43e0a30b23809f97c0d2518a11f3582b40d61a859778e7da73ad6d5f23e488`.
- The source tree was returned to the P3 state afterwards.

## Risks and how to test (P5/P6)

1. In-cell touch scans only while the panel runs. lk2nd's framebuffer keeps the
   panel on, so touch should work before the panel driver exists; if it reads
   nothing, that is the first suspect.
2. The driver pulses reset at probe. Android does the same while its splash is
   up, so the screen should survive; watch for a blank screen at probe.
3. Test order: P4 image boots (P5) → add 0002 + the config option → check
   `dmesg | grep -i edt`, `/proc/bus/input/devices`, then `evtest` corners
   (0,0) and (1079,2039).
4. Suspend: with a reset GPIO the driver cuts its supplies on suspend; L14 is
   always-on so the rail stays up. Revisit with the panel driver.
