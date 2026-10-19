# Lithium firmware map

The local package contains only files that are specific to this Xiaomi Mi MIX.
Generic firmware stays owned by the pinned postmarketOS packages listed below.

| Driver request (relative to `/lib/firmware`) | Local source | Package decision |
|---|---|---|
| `ath10k/QCA6174/hw3.0/board.bin` | `artifacts/firmware-dump/stock/wlan/bdwlan30.bin` | Install in pmOS overlay as `postmarketos/ath10k/QCA6174/hw3.0/board.bin`; proven on hardware. |
| `qca/rampatch_00130302.bin` | stock `bt/btfw32.tlv` maps by Rome 3.2 role | Use `linux-firmware-qca`; its generic file already exists. Do not duplicate. |
| `qca/nvm_00130302.bin` | stock `bt/btnv32.bin` maps by Rome 3.2 role; `btnv32.b15` remains an unselected alternate | Use `linux-firmware-qca`; its generic file already exists. Runtime controller revision still must confirm the mapping. |
| `qcom/a530_pm4.fw` | stock system image has same requested class | Use `linux-firmware-qcom`; pinned scorpio split list assigns it there. |
| `qcom/a530_pfp.fw` | stock system image | Use `linux-firmware-qcom`. |
| `qcom/a530v3_gpmu.fw2` | stock system image | Use `linux-firmware-qcom`. |
| `qcom/msm8996/lithium/a530_zap.mbn` + `.b00`–`.b02` | stock system image `/vendor/firmware/a530_zap.mdt/.b00/.b01/.b02` | Package locally; rename only MDT to the DTS-requested `.mbn`. |
| `qcom/msm8996/lithium/adsp.mbn` + `adsp.bNN` | `artifacts/firmware-dump/stock/adsp/` | Package locally; rename only `adsp.mdt` to `.mbn`. |
| `qcom/msm8996/lithium/venus.mbn` + `venus.bNN` | `artifacts/firmware-dump/stock/venus/` (from stock `NON-HLOS.bin` `/image`, via `mcopy`) | Package locally; rename only `venus.mdt` to `.mbn`. Video codec (Venus). |
| `qcom/sensors/sns.reg-xiaomi,lithium` | `artifacts/firmware-dump/stock/sensors/sns.reg` (from `persist` `/sensors/sns.reg`, read-only via `debugfs`) | Package locally. Sensor registry served to the SLPI by `qcom_sns_reg`; this unit's calibration. |
| `qcom/msm8996/lithium/slpi.mbn` + `slpi.bNN` | `artifacts/firmware-dump/stock/slpi_a4/slpi_a4.*` (stock `NON-HLOS.bin` `/image`, via `mcopy`) | Package locally; basename normalized to `slpi`. Stock NON-HLOS holds `slpi_a1`/`a4`/`a7`; lithium's stock DT (`qcom,msm-ssc-sensors`) names **a4**. Tested: SLPI boots, sensors appear. |

`linux-firmware-ath10k`, `linux-firmware-qca`, and `linux-firmware-qcom` are package
names observed in pinned pmaports commit `dfb010f5b9885d185d089b6e1e493030062f9756`.
The A530 ownership evidence is `device/testing/device-xiaomi-scorpio/30-gpu-firmware.files`.
