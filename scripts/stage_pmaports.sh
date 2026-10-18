#!/bin/sh
# Stage the lithium packages onto the pinned pmaports checkout for pmbootstrap.
# Offline; touches only sources/pmaports. Usage: stage_pmaports.sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PMAPORTS=${PMAPORTS:-"$PROJECT_ROOT/sources/pmaports"}
OVERLAY="$PROJECT_ROOT/packaging/pmaports"
KPKG=device/testing/linux-postmarketos-qcom-msm8996
DPKG=device/testing/device-xiaomi-lithium

test "$(git -C "$PMAPORTS" rev-parse HEAD)" = \
	"dfb010f5b9885d185d089b6e1e493030062f9756" || {
	echo "error: pmaports checkout is not at the pinned commit" >&2
	exit 1
}

# The packaged patch must be the Phase 3 patch, byte for byte.
cmp "$PROJECT_ROOT/kernel/patches/0001-arm64-dts-qcom-add-xiaomi-mi-mix.patch" \
	"$OVERLAY/$KPKG/0001-arm64-dts-qcom-add-xiaomi-mi-mix.patch"

# Reset the two package directories, then copy the overlay on top.
git -C "$PMAPORTS" checkout -q -- "$KPKG"
rm -rf "${PMAPORTS:?}/$DPKG"
mkdir -p "$PMAPORTS/$DPKG"
cp "$OVERLAY/$DPKG/"* "$PMAPORTS/$DPKG/"
cp "$OVERLAY/$KPKG/"* "$PMAPORTS/$KPKG/"

python3 -I "$PROJECT_ROOT/scripts/verify_apkbuild_checksums.py" \
	"$PMAPORTS/$DPKG" "$PMAPORTS/$KPKG"
git -C "$PMAPORTS" status --short
