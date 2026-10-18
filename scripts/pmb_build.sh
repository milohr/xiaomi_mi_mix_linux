#!/bin/sh
# Build the lithium packages and image with the pinned pmbootstrap/pmaports.
# Needs root through sudo (pmbootstrap chroots) and kpartx on the host. It asks
# for the new device user's password during install. It writes nothing to the
# phone. Outputs are copied to artifacts/pmb-export and audited.
set -eu

PROJECT_ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
PMB="$PROJECT_ROOT/sources/pmbootstrap/pmbootstrap.py"
WORK=${PMB_WORK:-"$HOME/.local/var/pmbootstrap-lithium"}
CFG="$WORK.cfg"
EXPORT="$PROJECT_ROOT/artifacts/pmb-export"

test "$(git -C "$PROJECT_ROOT/sources/pmbootstrap" rev-parse HEAD)" = \
	"7d23010a125ca7386fec4e390d14128b6c24d266" || {
	echo "error: pmbootstrap checkout is not at the pinned commit" >&2
	exit 1
}
command -v kpartx >/dev/null || {
	echo "error: install kpartx first (Arch: multipath-tools)" >&2
	exit 1
}

sh "$PROJECT_ROOT/scripts/stage_pmaports.sh"
# pmbootstrap reads channels.cfg from origin/main; keep it at the pin.
git -C "$PROJECT_ROOT/sources/pmaports" update-ref refs/remotes/origin/main \
	dfb010f5b9885d185d089b6e1e493030062f9756

# A new work folder gets the version stamp 'pmbootstrap init' would write
# (pmb/config/init.py); an existing one is left to pmbootstrap's own checks.
if [ ! -e "$WORK/version" ] && [ -z "$(ls -A "$WORK" 2>/dev/null)" ]; then
	mkdir -p "$WORK"
	echo 8 > "$WORK/version"
fi
cat > "$CFG" <<EOF
[pmbootstrap]
aports = $PROJECT_ROOT/sources/pmaports
work = $WORK
device = xiaomi-lithium
ui = console
user = user
hostname = lithium
EOF

pmb() { python3 "$PMB" -c "$CFG" "$@"; }

# --kernel: rebuild only the kernel and device packages (no image, no install) and copy them out.
if [ "${1:-}" = --kernel ]; then
	pmb build --force linux-postmarketos-qcom-msm8996 device-xiaomi-lithium
	mkdir -p "$PROJECT_ROOT/artifacts/kernel-build"
	cp "$WORK"/packages/*/aarch64/linux-postmarketos-qcom-msm8996-*.apk \
		"$WORK"/packages/*/aarch64/device-xiaomi-lithium-*.apk \
		"$PROJECT_ROOT/artifacts/kernel-build/"
	cp "$WORK/log.txt" "$PROJECT_ROOT/artifacts/kernel-build/pmbootstrap.log"
	(cd "$PROJECT_ROOT/artifacts/kernel-build" && sha256sum ./*.apk)
	exit 0
fi

pmb build --force linux-postmarketos-qcom-msm8996 device-xiaomi-lithium
pmb install
rm -rf "$EXPORT"
mkdir -p "$EXPORT"
pmb export "$EXPORT/links"
# Copy the real files out of the work directory, then drop the symlinks.
for f in "$EXPORT"/links/*; do
	cp -rL "$f" "$EXPORT/"
done
rm -r "$EXPORT/links"
cp "$WORK"/packages/*/aarch64/device-xiaomi-lithium-*.apk \
	"$WORK"/packages/*/aarch64/linux-postmarketos-qcom-msm8996-6.19.5-r1.apk "$EXPORT/"

cp "$WORK/log.txt" "$EXPORT/pmbootstrap.log"
(cd "$EXPORT" && sha256sum ./*.apk ./*.img ./*.img.* 2>/dev/null > SHA256SUMS || true)
python3 -I "$PROJECT_ROOT/scripts/audit_bootimg.py" "$EXPORT/boot.img" \
	"$PROJECT_ROOT/packaging/pmaports/device/testing/device-xiaomi-lithium/deviceinfo"
cat "$EXPORT/SHA256SUMS"
