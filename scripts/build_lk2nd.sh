#!/bin/sh
set -eu

: "${LK2ND_SRC:?set LK2ND_SRC to the patched lk2nd checkout}"
: "${TOOLCHAIN_PREFIX:?set TOOLCHAIN_PREFIX, including the arm-none-eabi- suffix}"
: "${DTC_DIR:?set DTC_DIR to the directory containing dtc}"

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
OUT=${LK2ND_OUT:-"$PROJECT_ROOT/artifacts/build/lk2nd-gcc"}

test "$(git -C "$LK2ND_SRC" rev-parse HEAD)" = \
    "8b46487c4c76776c4f2f61468d44a74c69e6b9ea" || {
	echo "error: lk2nd checkout is not at the pinned commit" >&2
	exit 1
}
test -x "${TOOLCHAIN_PREFIX}gcc"
test -x "$DTC_DIR/dtc"

mkdir -p "$OUT"
PATH="$DTC_DIR:/usr/bin:/bin" \
	make -C "$LK2ND_SRC" \
	BOOTLOADER_OUT="$OUT" \
	TOOLCHAIN_PREFIX="$TOOLCHAIN_PREFIX" \
	lk2nd-msm8996 -j"${JOBS:-4}"

IMAGE="$OUT/build-lk2nd-msm8996/lk2nd.img"
DTB="$OUT/build-lk2nd-msm8996/lk2nd/device/dts/msm8996/msm8996pro-xiaomi-lithium.dtb"
sha256sum "$IMAGE" "$DTB"
stat -c '%n %s bytes' "$IMAGE" "$DTB"
