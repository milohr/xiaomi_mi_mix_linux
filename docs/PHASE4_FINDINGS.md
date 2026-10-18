# Phase 4 findings — pmbootstrap packages and image (2026-10-18)

Status: **built, exported and audited offline.** Nothing was written to the phone. The one
gate still open is the package lint (`pmbootstrap lint` / pmaports CI checks), below.

## What was built

| Item | Value |
|---|---|
| pmbootstrap | `7d23010a` (pinned, `research/source-lock.json`) |
| pmaports | `dfb010f5` (pinned), with `packaging/pmaports/` staged in by `scripts/stage_pmaports.sh` |
| device package | `device-xiaomi-lithium-1-r0` (`packaging/pmaports/device/testing/device-xiaomi-lithium/`) |
| kernel package | shared `linux-postmarketos-qcom-msm8996` 6.19.5, bumped to **r1** with patch 0001 (the lithium DTS) |
| kernel build | cross-native, Alpine clang 23.1.3; 2 h 13 min on the 4-core laptop (abuild log: `artifacts/pmb-export/pmbootstrap.log`) |
| UI | `console` (no desktop): the image is for the diagnostic shell and USB networking |

`scripts/pmb_build.sh` runs build → install → export → audit. Its export loop used `cp -L`,
which refuses the `dtbs/` directory, so the first run stopped after copying `boot.img`; it now
uses `cp -rL`. The remaining export steps were run by hand with the same commands.

## Outputs (`artifacts/pmb-export/`, ignored by Git)

| File | Bytes | SHA-256 |
|---|---|---|
| `boot.img` | 23,908,352 | `c2f98e2b1727540e6c48378a38a576176a3b092cafb872c77de3b4b90b351272` |
| `p5-boot.img` | 23,908,352 | `af734348a19c1970d17a1c0432a923e1071132fbb6eeb304d500b8a7aa62a9c5` |
| `xiaomi-lithium.img` (rootfs with /boot and /) | 1,328,545,792 | `a120e324f1de4317f167c0e599cd98aa71eeb24ebcd7814bdbdb2f962a96e210` |
| `dtbs/msm8996pro-xiaomi-lithium.dtb` | 66,199 | `622ba9fa4316dc7086cfd2891cb37d7f2d57c88d7ead02e3aacfb2384faf4abf` |
| `vmlinuz` | 11,263,869 | `4aa7d9c5baf76b03922a3897195340c0cf3257a7f004875a8d6866ed6d08cef4` |
| `initramfs` | 12,569,253 | `05938d8a86ea94fe45b6adf0e44bf886dcc65cb3063538b45336380e11593062` |
| `linux-postmarketos-qcom-msm8996-6.19.5-r1.apk` | 26,679,079 | `4acdee5429d51fec08f03bd5e1cba9d8247ccf6ee01a33bc9da7431fada67e73` |
| `device-xiaomi-lithium-1-r0.apk` | 2,277 | `ddd9f0c3ddb603b926b62cd300bdec7d8c78f20ec860889efb555e6f9946eb87` |

The same list is in `artifacts/pmb-export/SHA256SUMS` and `research/pmb-build.json`.

## Checks

1. **`audit_bootimg.py boot.img deviceinfo`: all passed.** v0 header, page 4096, load addresses
   base + offsets as in the stock image, gzip arm64 Image (27,310,592 bytes unpacked) with
   exactly one appended FDT whose compatible is lithium's, ramdisk present, no second stage,
   35.6 % of the 64 MiB partition.
2. **The DTB in the image is the Phase 3 DTB, byte for byte** (`622ba9fa…`), both the
   exported `dtbs/` file and the one appended to the kernel in `p5-boot.img`.
3. **`p5-boot.img`** = `boot.img` with four arguments appended to the header command line
   (`scripts/make_p5_bootimg.py` asserts every other byte is unchanged). Its audit passes too.
   Command line:
   `lk2nd.pass-simplefb pmos_boot_uuid=6dc753a6-… pmos_root_uuid=0e93332f-… pmos_rootfsopts=defaults lk2nd.pass-ramoops=zap console=tty0 clk_ignore_unused pd_ignore_unused`.
4. **Kernel config.** The apk ships no `.config`, but the kernel embeds it
   (`CONFIG_IKCONFIG=y`); extracted from `vmlinuz` to `artifacts/pmb-export/kernel.config`.
   `check_kernel_config.py kernel/lithium.config`: 30/30. P5's needs are built in:
   `PSTORE_RAM`, `FB_SIMPLE`, `FRAMEBUFFER_CONSOLE`, `USB_DWC3_QCOM`, `PHY_QCOM_QUSB2`,
   `USB_CONFIGFS_RNDIS`, `USB_CONFIGFS_NCM`. Off by design: `DRM_SIMPLEDRM` (P5 uses simplefb),
   `TOUCHSCREEN_EDT_FT5X06` (touch is its own later change, docs/TOUCH.md). It differs from the
   offline P4 config only in the toolchain version and pahole detection lines.
5. **Initramfs** (unpacked from `boot.img`): has `unudhcpd`, a `telnetd`, and the
   `fail_halt_boot` → `debug_shell` path, so the first boot can end in the reachable debug
   shell that P5 expects.

Steps 1–5 are recorded with full command output in `artifacts/pmb-export/P5_PREP_REPORT.md`,
written by `scripts/p5_prep_check.sh`.

## Open

- **Package lint** (the P4 exit gate's "package lint"): not yet run.
- The `pmos_boot_uuid`/`pmos_root_uuid` refer to partitions inside `xiaomi-lithium.img`, which
  is not on the phone. That is intended for P5: the initramfs waits for them, gives up after
  about 30 s and opens the debug shell.
