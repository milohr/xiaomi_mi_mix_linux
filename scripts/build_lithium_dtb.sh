#!/bin/sh
set -eu

# bc for kernel prepare, unpacked rootless (see docs/DISPLAY.md).
PATH="$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)/artifacts/toolchain/bc/usr/bin:$PATH"
export PATH

: "${KERNEL_SRC:?set KERNEL_SRC to the patched MSM8996 kernel checkout}"

PINNED_COMMIT=1aed438cb5f49d7a61593f764d4a82f83b14114f
PROJECT_ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
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
	# Full schema check. The SoC/PMIC includes carry known warnings that the
	# upstream scorpio board shares; docs/PHASE3_FINDINGS.md lists them.
	make -C "$KERNEL_SRC" O="$OUT" ARCH=arm64 CHECK_DTBS=y "$TARGET" 2>&1 |
		tee "$OUT/dtbs_check.log"
else
	echo "warning: dt-validate unavailable; skipping schema validation" >&2
fi

DTB="$OUT/arch/arm64/boot/dts/qcom/msm8996pro-xiaomi-lithium.dtb"
VENV_PY="$PROJECT_ROOT/artifacts/toolchain/venv-lmdpdg/bin/python"
if [ -x "$VENV_PY" ]; then
	"$VENV_PY" -I "$PROJECT_ROOT/scripts/verify_lithium_dtb.py" "$DTB" \
		"$PROJECT_ROOT/artifacts/stock/audit/boot.img.dtb-5"
else
	echo "warning: no pylibfdt venv; skipping stock evidence check" >&2
fi
sha256sum "$DTB"
stat -c '%n %s bytes' "$DTB"
