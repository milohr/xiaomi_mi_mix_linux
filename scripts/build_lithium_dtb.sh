#!/bin/sh
set -eu

: "${KERNEL_SRC:?set KERNEL_SRC to the patched MSM8996 kernel checkout}"

PINNED_COMMIT=1aed438cb5f49d7a61593f764d4a82f83b14114f
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
OUT=${KERNEL_OUT:-"$PROJECT_ROOT/artifacts/build/kernel-phase3"}
TARGET=qcom/msm8996pro-xiaomi-lithium.dtb

test "$(git -C "$KERNEL_SRC" rev-parse HEAD)" = "$PINNED_COMMIT" || {
	echo "error: kernel checkout is not at the pinned commit" >&2
	exit 1
}

mkdir -p "$OUT"
make -C "$KERNEL_SRC" O="$OUT" ARCH=arm64 defconfig
make -C "$KERNEL_SRC" O="$OUT" ARCH=arm64 "$TARGET" -j"${JOBS:-4}"

if command -v dt-validate >/dev/null 2>&1; then
	make -C "$KERNEL_SRC" O="$OUT" ARCH=arm64 CHECK_DTBS=y \
		DT_SCHEMA_FILES=Documentation/devicetree/bindings/arm/qcom.yaml \
		"$TARGET"
else
	echo "warning: dt-validate unavailable; skipping schema validation" >&2
fi

DTB="$OUT/arch/arm64/boot/dts/qcom/msm8996pro-xiaomi-lithium.dtb"
sha256sum "$DTB"
stat -c '%n %s bytes' "$DTB"
