# Hardware coverage: Xiaomi Mi MIX (lithium) features against the port (2026-10-19)

The phone's advertised features (GSMArena, launch press), the chips the stock device tree
names (`artifacts/p3/stock-dtb5.dts`, line numbers below), and where the port stands.
✅ works · 🔧 in progress · ❌ missing · ⏭️ not wanted (calls)

| Feature | Hardware (stock) | Status |
|---|---|---|
| CPU, Snapdragon 821, up to 2.35 GHz | MSM8996 Pro, speed bin 0 | ✅ all OPPs (P13 audit) |
| GPU, Adreno 530 | | ✅ (patch 0022); icon/status-bar garbage during video still open |
| Display 6.4" 1080×2040, touch | | ✅ |
| Speaker, 3.5 mm jack | TFA9891, WCD9335 | ✅ |
| Microphones | WCD9335 ADC1/ADC3 | ✅ |
| Headset microphone | WCD9335 MBHC | ❌ jack detected as headphones only (`mech_only`) |
| Wi-Fi ac, Bluetooth 4.2 | QCA6174 | ✅ |
| USB-C, OTG | TUSB320L | ✅ |
| Video decode | Venus | ✅ (mpv); Firefox needs the drmprime FFmpeg |
| Accelerometer, gyroscope, compass, barometer | SLPI | ✅ |
| Light sensor | none | — not fitted; no auto-brightness |
| Battery 4400 mAh, charging | PMI8994 | ✅ up to 3 A at 5 V |
| Quick Charge 3.0 (18 W) | PMI8994 HVDCP | ❌ no fully sourced register sequence (`artifacts/p11/hvdcp-gap-analysis.md`) |
| LTE, dual nano-SIM | modem (MSS) | 🔧 modem boots, registers; data path (IPA v2.5, ipa2-lite) in progress |
| GPS / GLONASS / BeiDou | inside the modem | ❌ reachable through ModemManager once the modem runs |
| NFC | NXP PN548, `nxp,nfc-548` | ❌ mainline `nxp-nci` covers PN54x; tags only on Linux |
| Vibration | PMI8994 haptics, ERM, `qcom,qpnp-haptic` (:17839) | ❌ no mainline PMI8994 haptics driver |
| Flash / torch | PMI8994 flash LED, `qcom,qpnp-flash-led` | ❌ no mainline driver for this PMIC's flash |
| Rear camera 16 MP, PDAF | OV16880 (OFilm) or S5K3P3 (Qtech) variant, EEPROM (:8276, :8319), VCM | ❌ see below |
| Front camera 5 MP | CSI port 2, `qcom,camera@2` (:8246); model unknown | ❌ |
| Fingerprint (rear) | FPC1020, `fpc,fpc1020` | ❌ see below |
| Earpiece (piezo-ceramic), ultrasonic proximity | | ⏭️ calls only |

## Cameras

- CAMSS supports MSM8996 in mainline. libcamera's software ISP can turn raw frames into images.
  No mainline driver exists for the hardware ISP, so expect modest preview resolution and frame
  rate, no 4K.
- Missing pieces:
  - Sensor drivers: neither OV16880 nor S5K3P3 is in mainline, and the front sensor is unidentified.
  - Lithium DT nodes: CCI, the rails `cam_vana/vdig/vio/vaf`, reset GPIOs, MCLK and CSI lanes.
  - The VCM (focus) driver.
- Which rear variant a unit carries is decided at boot. Read the sensor chip-ID registers
  over CCI to find out.
- The vendor extract in `artifacts/p8` holds generic Qualcomm camera libraries, not lithium's
  OV16880/S5K3P3 ones. Register settings would need a full stock vendor image.

## Fingerprint

- Linux never reads this sensor, even on Android:
  - `fpc_fpc1020` is a platform device with only an IRQ GPIO, an ID GPIO and power rails.
  - The SPI connection belongs to the secure side: `qcom,fingerprint-sensor-ssc-spi-conn` names
    `ssc-subsys-id = 5`, SPI port 2, and `tz-subsys-id = 1`.
  - Capture and matching run in TrustZone apps shipped in NON-HLOS: `fingerpr.mdt`,
    `fpca4.mdt`, `fpca8.mdt`.
- Paths on Linux:
  - Talking to the TrustZone app needs a QSEECOM-style interface (none for this SoC in mainline)
    and FPC's undocumented protocol.
  - Reading the sensor directly needs the SPI bus not to be TZ-locked, a new libfprint driver,
    and matching that copes with a small sensor area.
- Cheapest check that would close or open the question: whether Linux can access that SPI
  controller at all. Ranked last among the missing features.
