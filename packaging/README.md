# Packaging implementation gate

No fake APKBUILD or flash metadata is supplied. In P4 create a real pmaports
package against the pinned tree's conventions:

- `device-xiaomi-lithium/APKBUILD`: real sources, checksums, license, dependencies.
- `device-xiaomi-lithium/deviceinfo`: verified aarch64 target, DTB path, boot
  image format and supported boot method. `deviceinfo` is the conventional
  metadata filename; a `.device` file is not assumed to be the package format.
- Shared MSM8996 kernel integration with original lithium DTS and panel patches;
  use a separate kernel APKBUILD only when justified by the baseline audit.
- Verified config fragment and dependency on appropriate firmware packages only
  after provenance/licensing and exact hardware identification.

Acceptance: package lint, clean build, DT binding checks, image size/header audit,
and hashed output manifest. Build success does not mark hardware support working.
