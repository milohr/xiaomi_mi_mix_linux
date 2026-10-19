# Sensors and auto-rotation: plan (2026-10-18)

Goal: Plasma Mobile's auto-rotate works. Plasma shows the toggle and rotates when
iio-sensor-proxy finds an accelerometer, which it reads from an IIO device.

## Where the sensors are

No accelerometer, gyroscope, light or proximity sensor is on an I2C bus the
application CPU controls: the stock device tree has none. All sensors belong to the
**SLPI** (Sensor Low Power Island, the sensor DSP). Its firmware already loads
(`qcom/msm8996/lithium/slpi.mbn`, firmware-xiaomi-lithium).

The SLPI needs two things from Linux before it serves sensors:

1. **Sensor Registry** (QMI service 271): the SLPI asks the application CPU for its
   sensor configuration and calibration. Our pinned kernel has an in-kernel server,
   `drivers/soc/qcom/qcom_sns_reg.c` (Alexey Minnekhanov, after Yassine Oudjana's
   userspace `sns-reg`), started with the DSP. It requests
   `qcom/sensors/sns.reg-<board compatible>` then `qcom/sensors/sns.reg`; today both
   fail (-2) because no file is installed.
2. **A Sensor Manager (SMGR) client**: the SLPI then serves the sensors over QMI
   ("Sensor Manager"). Yassine Oudjana's series "[PATCH 0/3] QRTR bus and Qualcomm
   Sensor Manager IIO drivers" (linux-iio/linux-arm-msm, 2025-04-06) turns them into IIO
   devices (accel, gyro, magnetometer, proximity, pressure). It names MSM8996 among its
   targets. Not in our tree. Patches: (1) net: qrtr: Turn QRTR into a bus; (2) net: qrtr:
   macro for QMI version/instance to QRTR instance; (3) iio: Add Qualcomm Sensor Manager
   drivers. Review (Luca Weiss, 2025-06) found a NULL deref for unknown sensor types
   (type 0) with a follow-up fix. Testing notes: postmarketOS pmaports MR 4118.

## Lithium's registry

The phone's own registry is on persist: `/persist/sensors/sns.reg`, 25 468 bytes,
sha256 `979459f8…`, extracted read-only from `artifacts/persist/persist-sda12.img` to
`artifacts/firmware-dump/stock/sensors/sns.reg` (ignored; device data, never committed).

## Steps

1. Package `sns.reg` as `qcom/sensors/sns.reg-xiaomi,lithium` in
   firmware-xiaomi-lithium (make-firmware-tarball.sh). Check on hardware: no -2 at boot,
   the registry server answers the SLPI (dmesg), SLPI stays up.
2. Fetch the SMGR series exactly (lore mbox, b4) into `artifacts/downstream/` (ignored),
   plus Luca Weiss's fix; check it applies to the pinned 6.19 tree; patches 0020+.
   Kernel config: QRTR, the new IIO SMGR options as modules.
3. Boot: `/sys/bus/iio/devices/*` show the sensors; read raw accelerometer values while
   turning the phone.
4. Mount matrix: the accelerometer axes relative to the screen. From stock if the
   registry or HAL config holds an orientation; else measure (phone flat, upright,
   on its side) and set `mount-matrix` / the IIO attribute so iio-sensor-proxy reports
   the right orientation.
5. Userspace: `iio-sensor-proxy` installed and running; `monitor-sensor` shows
   orientation changes; Plasma Mobile's auto-rotate toggle appears and works.
6. Later from the same path: proximity (screen off in calls), light (auto-brightness),
   compass.

## Risks

- The series is not merged; review changes may follow. Keep it as separate patches.
- A wrong registry can leave the SLPI without sensors; the registry is read-only data
  from this phone, so it should match the firmware exactly.
- SLPI crashes would show as remoteproc recovery in dmesg; the rest of the system is
  unaffected.
