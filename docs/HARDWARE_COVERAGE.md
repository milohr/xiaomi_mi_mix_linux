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
| Rear camera 16 MP, PDAF | **OV16880** (OFilm module on this unit), EEPROM, VCM at 0x0c | ❌ no mainline sensor driver; see below |
| Front camera 5 MP | **OV5675**, CSI port 2, `qcom,camera@2` (:8246) | 🔧 mainline `ov5675` driver exists |
| Fingerprint (rear) | FPC1020, `fpc,fpc1020` | ❌ see below |
| Earpiece (piezo-ceramic), ultrasonic proximity | | ⏭️ calls only |

## Cameras

Identified on hardware (2026-10-19, kernel r32, test module `artifacts/camera/camprobe`):
powered in stock order (vdig, vana, vio, vaf; reset/standby high; MCLK 24 MHz) and read over CCI.

| Bus | Address | Answer | Device |
|---|---|---|---|
| CCI0 (rear) | 0x36 | 0x300a = `01 68 80` | **OV16880** |
| CCI0 | 0x58 | ack | module EEPROM of the OV16880/OFilm variant (stock 8-bit 0xb0); 0x50 (S5K3P3/Qtech) absent |
| CCI0 | 0x0c | ack | focus motor (VCM), model not read yet |
| CCI0 | 0x21 | ack | unknown |
| CCI1 (front) | 0x36 | 0x300b = `56 75` | **OV5675** |

Wiring (stock, verified by the probe): rear MCLK0 GPIO 13, reset GPIO 86, standby GPIO 30,
vdig L3 1.2 V, vana L17 2.95 V, vio LVS1 1.8 V, vaf L23 2.8 V, CSIPHY0; front MCLK2 GPIO 15,
reset GPIO 23, vdig L27 1.2 V, vana L29 2.7 V, vio LVS1, CSIPHY2. CCI reads are limited in
length (the 16-byte EEPROM reads were refused by the adapter quirk, not by the EEPROM).


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
