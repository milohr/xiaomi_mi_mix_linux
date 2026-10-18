# Recovery readiness checklist

Before proposing any live boot experiment, record:

- Exact device identity, current unlock state, partition map and boot image limits.
- User-data backup status and a matching stock boot/recovery source with hashes.
- Physical key combinations and the currently working recovery/fastboot path.
- Whether temporary boot is supported by this exact bootloader; unlocked does not imply it.
- Expected partition effects, rollback instructions and observable success criteria.
- A reviewed image hash and explicit user authorization for the concrete experiment.

Do not modify primary bootloader, GPT, modem calibration, persist or security
partitions. EDL availability and an authenticated programmer are not assumed.
The repository has no flash, erase, unlock, reboot or partition-write script.
