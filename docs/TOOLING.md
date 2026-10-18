# Host tools and usage

Run from this repository root. No script installs dependencies or changes device state.

```sh
python3 scripts/preflight.py
python3 -m unittest discover -s tests -v
python3 scripts/collect_device.py --serial YOUR_ADB_SERIAL
python3 scripts/parse_panel.py examples/panel-on.hex --format json
python3 scripts/parse_panel.py examples/panel-on.hex --format c
python3 scripts/hash_artifacts.py PATH_TO_STOCK_BOOT_IMAGE
```

Collection requires authorized USB debugging and an explicit serial. It verifies
`ro.product.device=lithium`, reads a narrow property allowlist and selected proc
files, and lists partition links. It does not read personal files or request root.
Permission failures are retained in its report, not bypassed. Output lives in an
ignored timestamped directory; review raw results before sharing.

Use distro-supported Android platform-tools, device-tree compiler and build tools.
Choose pmbootstrap and cross-toolchain versions after pinning the source baseline;
prefer pmbootstrap-managed build environments to guessed host cross-compilers.
The kernel build tool listing is preliminary, not a full dependency resolver.

## Matching stock archive

`python3 scripts/download_stock.py` resumes the verified-version Xiaomi download.
It checks full byte count and emits a SHA-256 manifest on completion. It does
not authenticate archive contents independently or extract/execute anything.
Incomplete `.partial` files are not usable recovery images.

## Full stock acquisition and audit

`python3 scripts/download_stock_ranges.py` uses Xiaomi's cdnorg HTTPS endpoint
with eight concurrent 4 MiB requests. Each response must have the exact expected
Content-Range and byte count. It resumes completed range files, assembles the
archive in order, and records a SHA-256 manifest. Range files are local staging
data, not authenticated recovery images.

`python3 scripts/audit_stock.py` checks archive length, reads the complete gzip
stream to verify integrity, lists tar members, and extracts only an explicit
allowlist into artifacts/stock/audit. Vendor shell files are retained as text
evidence and never executed. It validates image magic, component bounds and
partition fit, runs unpack_bootimg, and records compressed-kernel and DTB
locations. It does not flash, mount or boot any image.
