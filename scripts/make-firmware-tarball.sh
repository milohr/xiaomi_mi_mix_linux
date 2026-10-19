#!/bin/sh
set -eu

root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
stamp=${FIRMWARE_DATE:-20261018}
name="firmware-lithium-$stamp"
out=${1:-"$root/packaging/pmaports/device/testing/firmware-xiaomi-lithium/$name.tar.gz"}
stage="$root/artifacts/p9/.firmware-stage"
stock="$root/artifacts/firmware-dump/stock"
system_img="$root/artifacts/p8/extract/system.raw.img"

[ -f "$stock/wlan/bdwlan30.bin" ]
[ -f "$stock/adsp/adsp.mdt" ]
[ -f "$stock/slpi/slpi_a1.mdt" ]
[ -f "$stock/venus/venus.mdt" ]
[ -f "$system_img" ]
command -v debugfs >/dev/null

rm -rf "$stage"
mkdir -p "$stage/$name/firmware/postmarketos/ath10k/QCA6174/hw3.0"
mkdir -p "$stage/$name/firmware/qcom/msm8996/lithium"

install -m644 "$stock/wlan/bdwlan30.bin" \
  "$stage/$name/firmware/postmarketos/ath10k/QCA6174/hw3.0/board.bin"

# MDT loaders accept the metadata file under the DTS-requested .mbn name and
# derive the adjacent .bNN segment names from it.
install -m644 "$stock/adsp/adsp.mdt" \
  "$stage/$name/firmware/qcom/msm8996/lithium/adsp.mbn"
for src in "$stock"/adsp/adsp.b??; do
  install -m644 "$src" "$stage/$name/firmware/qcom/msm8996/lithium/$(basename "$src")"
done
install -m644 "$stock/slpi/slpi_a1.mdt" \
  "$stage/$name/firmware/qcom/msm8996/lithium/slpi.mbn"
for src in "$stock"/slpi/slpi_a1.b??; do
  dst=$(basename "$src" | sed 's/^slpi_a1/slpi/')
  install -m644 "$src" "$stage/$name/firmware/qcom/msm8996/lithium/$dst"
done

install -m644 "$stock/venus/venus.mdt" \
  "$stage/$name/firmware/qcom/msm8996/lithium/venus.mbn"
for src in "$stock"/venus/venus.b??; do
  install -m644 "$src" "$stage/$name/firmware/qcom/msm8996/lithium/$(basename "$src")"
done

for file in a530_zap.mdt a530_zap.b00 a530_zap.b01 a530_zap.b02; do
  tmp="$stage/$file"
  debugfs -R "dump /vendor/firmware/$file $tmp" "$system_img" >/dev/null 2>&1
  case "$file" in
    *.mdt) dst=a530_zap.mbn ;;
    *) dst=$file ;;
  esac
  install -m644 "$tmp" "$stage/$name/firmware/qcom/msm8996/lithium/$dst"
  rm "$tmp"
done

(
  cd "$stage/$name"
  find firmware -type f -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
)
mkdir -p "$(dirname -- "$out")"
GZIP=-n tar --sort=name --mtime='UTC 2026-10-18' --owner=0 --group=0 --numeric-owner \
  -C "$stage" -czf "$out" "$name"
sha256sum "$out"
