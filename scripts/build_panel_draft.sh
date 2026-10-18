#!/bin/sh
# Regenerate, assemble, compile-test and verify the FTE716 panel driver draft.
# Offline only. Produces no image and touches no device.
set -eu

PROJECT_ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
KERNEL_SRC=${KERNEL_SRC:-"$PROJECT_ROOT/sources/linux-msm8996"}
LMDPDG=${LMDPDG:-"$PROJECT_ROOT/sources/lmdpdg"}
PYTHON=${LMDPDG_PYTHON:-"$PROJECT_ROOT/artifacts/toolchain/venv-lmdpdg/bin/python"}
STOCK_DTB=${STOCK_DTB:-"$PROJECT_ROOT/artifacts/stock/audit/boot.img.dtb-5"}
KOUT=${KERNEL_OUT:-"$PROJECT_ROOT/artifacts/build/kernel-panel"}
GEN="$PROJECT_ROOT/build/panel-lmdpdg"
MOD="$PROJECT_ROOT/build/panel-module"
DRAFT="$PROJECT_ROOT/kernel/panel-draft"

# Rootless host tools unpacked from Arch packages (see docs/DISPLAY.md).
PATH="$PROJECT_ROOT/artifacts/toolchain/lld/bin:$PROJECT_ROOT/artifacts/toolchain/bc/usr/bin:$PATH"
export PATH

test "$(git -C "$KERNEL_SRC" rev-parse HEAD)" = \
	"1aed438cb5f49d7a61593f764d4a82f83b14114f" || {
	echo "error: kernel checkout is not at the pinned commit" >&2
	exit 1
}
test "$(git -C "$LMDPDG" rev-parse HEAD)" = \
	"28c4df25628f6241ce925af15637a443ea2b3bb5" || {
	echo "error: lmdpdg checkout is not at the pinned commit" >&2
	exit 1
}
echo "a2968fa1b189c5e73bbd89a578575ce7cf0a42f2bc31968265260b362f49ce01  $STOCK_DTB" |
	sha256sum -c --quiet

rm -rf "$GEN" && mkdir -p "$GEN"
(cd "$GEN" && "$PYTHON" "$LMDPDG/lmdpdg.py" --dumb-dcs "$STOCK_DTB" >/dev/null 2>&1) || true
# The stock DTB also carries Qualcomm reference panels; keep lithium's two.
find "$GEN" -mindepth 1 -maxdepth 1 -type d ! -name '*_fte716_1080p_video' -exec rm -r {} +
for variant in sharp auo; do
	test -f "$GEN/${variant}_fte716_1080p_video/panel-${variant}-fte716.c"
done

python3 -I "$PROJECT_ROOT/scripts/assemble_panel_draft.py" "$GEN" \
	"$DRAFT/panel-xiaomi-lithium-fte716.c.in" "$DRAFT/panel-xiaomi-lithium-fte716.c"
python3 -I "$PROJECT_ROOT/scripts/verify_panel_draft.py"

if [ ! -f "$KOUT/Module.symvers" ] && [ ! -f "$KOUT/scripts/mod/modpost" ]; then
	mkdir -p "$KOUT"
	make -C "$KERNEL_SRC" O="$KOUT" ARCH=arm64 LLVM=1 defconfig
	"$KERNEL_SRC/scripts/config" --file "$KOUT/.config" -m DRM_MSM -e DRM_MIPI_DSI -e DRM_PANEL
	make -C "$KERNEL_SRC" O="$KOUT" ARCH=arm64 LLVM=1 olddefconfig
	make -C "$KERNEL_SRC" O="$KOUT" ARCH=arm64 LLVM=1 -j"${JOBS:-4}" modules_prepare
fi

rm -rf "$MOD" && mkdir -p "$MOD"
cp "$DRAFT/panel-xiaomi-lithium-fte716.c" "$MOD/"
echo 'obj-m += panel-xiaomi-lithium-fte716.o' > "$MOD/Kbuild"
# No vmlinux was linked, so modpost cannot resolve exports: warnings only.
make -C "$KOUT" ARCH=arm64 LLVM=1 W=1 KBUILD_MODPOST_WARN=1 M="$MOD" modules
perl "$KERNEL_SRC/scripts/checkpatch.pl" --no-tree -f "$DRAFT/panel-xiaomi-lithium-fte716.c"
sha256sum "$DRAFT/panel-xiaomi-lithium-fte716.c" "$MOD/panel-xiaomi-lithium-fte716.ko"
