#!/bin/sh
# Offline P5 image audit. Never accesses a device or modifies build inputs.
set -u

ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
EXPORT="$ROOT/artifacts/pmb-export"
BOOT="$EXPORT/boot.img"
P5="$EXPORT/p5-boot.img"
DEVICEINFO="$ROOT/packaging/pmaports/device/testing/device-xiaomi-lithium/deviceinfo"
EXPECTED_DTB_SHA256=622ba9fa4316dc7086cfd2891cb37d7f2d57c88d7ead02e3aacfb2384faf4abf
TMP=$(mktemp -d "${TMPDIR:-/tmp}/p5-prep.XXXXXX") || exit 1
trap 'rm -rf "$TMP"' EXIT HUP INT TERM

extract_boot_parts() {
	python3 - "$1" "$2" "$3" <<'PY'
import struct, sys
src, kernel_out, ramdisk_out = sys.argv[1:]
image = open(src, "rb").read()
if image[:8] != b"ANDROID!":
    raise SystemExit("not an Android boot image")
kernel_size, ramdisk_size = struct.unpack_from("<II", image, 8)[0], struct.unpack_from("<I", image, 16)[0]
page = struct.unpack_from("<I", image, 36)[0]
align = lambda n: (n + page - 1) // page * page
kernel_off = page
ramdisk_off = page + align(kernel_size)
open(kernel_out, "wb").write(image[kernel_off:kernel_off + kernel_size])
open(ramdisk_out, "wb").write(image[ramdisk_off:ramdisk_off + ramdisk_size])
print(f"kernel: offset={kernel_off} size={kernel_size} output={kernel_out}")
print(f"ramdisk: offset={ramdisk_off} size={ramdisk_size} output={ramdisk_out}")
PY
}

extract_appended_dtb() {
	python3 - "$1" "$2" <<'PY'
import struct, sys, zlib
src, out = sys.argv[1:]
payload = open(src, "rb").read()
d = zlib.decompressobj(16 + zlib.MAX_WBITS)
raw = d.decompress(payload)
tail = d.unused_data
if tail[:4] != b"\xd0\x0d\xfe\xed":
    raise SystemExit("no FDT immediately after gzip stream")
size = struct.unpack_from(">I", tail, 4)[0]
if size != len(tail):
    raise SystemExit(f"appended data is not exactly one FDT: totalsize={size}, tail={len(tail)}")
open(out, "wb").write(tail)
print(f"gzip_uncompressed_size={len(raw)}")
print(f"appended_dtb_size={len(tail)}")
print(f"output={out}")
PY
}

if test "${1:-}" = "--self-test"; then
	P4_CONFIG="$ROOT/artifacts/build/kernel-p4/.config"
	P4_DTB="$ROOT/artifacts/build/kernel-p4/arch/arm64/boot/dts/qcom/msm8996pro-xiaomi-lithium.dtb"
	python3 -I "$ROOT/scripts/check_kernel_config.py" "$ROOT/kernel/lithium.config" "$P4_CONFIG" || exit 1
	test -f "$P4_DTB" || { echo "missing P4 lithium DTB: $P4_DTB" >&2; exit 1; }
	printf 'P5 extractor self-test payload\n' | gzip -c > "$TMP/synthetic-Image.gz"
	cat "$P4_DTB" >> "$TMP/synthetic-Image.gz"
	extract_appended_dtb "$TMP/synthetic-Image.gz" "$TMP/extracted.dtb" || exit 1
	cmp "$P4_DTB" "$TMP/extracted.dtb" || exit 1
	sha256sum "$P4_DTB" "$TMP/extracted.dtb"
	echo "self-test passed: extracted DTB is byte-identical to the P4 lithium DTB"
	exit 0
fi

test -f "$BOOT" || { echo "error: missing $BOOT; wait for scripts/pmb_build.sh to finish" >&2; exit 2; }
mkdir -p "$EXPORT"
REPORT="$EXPORT/P5_PREP_REPORT.md"
: > "$REPORT"

log_command() {
	label=$1
	shift
	{
		printf '\n#### `%s`\n\n```text\n' "$label"
		printf '$'
		printf ' %s' "$@"
		printf '\n'
	} >> "$REPORT"
	"$@" > "$TMP/command.out" 2>&1
	rc=$?
	cat "$TMP/command.out" >> "$REPORT"
	printf '\n[exit status: %s]\n```\n' "$rc" >> "$REPORT"
	return "$rc"
}

{
	echo '# P5 preparation report'
	echo
	echo 'Offline host-side audit. No ADB, Fastboot, or USB access was used.'
} >> "$REPORT"

# Step 1: derive P5 image and audit both images.
step1=PASS
log_command "create p5-boot.img" python3 -I "$ROOT/scripts/make_p5_bootimg.py" "$BOOT" "$P5" \
	lk2nd.pass-ramoops=zap console=tty0 clk_ignore_unused pd_ignore_unused || step1=FAIL
log_command "audit boot.img" python3 -I "$ROOT/scripts/audit_bootimg.py" "$BOOT" "$DEVICEINFO" || step1=FAIL
if test -f "$P5"; then
	log_command "audit p5-boot.img" python3 -I "$ROOT/scripts/audit_bootimg.py" "$P5" "$DEVICEINFO" || step1=FAIL
else
	step1=FAIL
	printf '\n#### `audit p5-boot.img`\n\n```text\nSKIPPED: p5-boot.img was not created\n[exit status: 1]\n```\n' >> "$REPORT"
fi

{
	echo
	echo '## Image sizes and hashes'
	echo
	echo '```text'
	for image in "$BOOT" "$P5"; do
		if test -f "$image"; then
			stat -c '%n  %s bytes' "$image"
			sha256sum "$image"
		else
			echo "$image  MISSING"
		fi
	done
	echo '```'
} >> "$REPORT"

# Step 2: split p5 image and pull the DTB appended to its gzip kernel.
step2=PASS
if test -f "$P5"; then
	log_command "extract kernel and ramdisk from p5-boot.img" extract_boot_parts "$P5" "$TMP/p5-kernel" "$TMP/p5-ramdisk" || step2=FAIL
	log_command "extract appended DTB from p5 kernel" extract_appended_dtb "$TMP/p5-kernel" "$TMP/p5.dtb" || step2=FAIL
	if test -f "$TMP/p5.dtb"; then
		dtb_sha=$(sha256sum "$TMP/p5.dtb" | awk '{print $1}')
		{
			echo
			echo '#### `sha256sum extracted-p5.dtb`'
			echo
			echo '```text'
			echo "$dtb_sha  extracted-p5.dtb"
			echo "expected  $EXPECTED_DTB_SHA256"
			echo '```'
		} >> "$REPORT"
		test "$dtb_sha" = "$EXPECTED_DTB_SHA256" || step2=FAIL
	else
		step2=FAIL
	fi
else
	step2=FAIL
fi

# Step 3: extract and check the packaged kernel configuration.
step3=PASS
apk=$(find "$EXPORT" -maxdepth 1 -type f -name 'linux-postmarketos-qcom-msm8996-*.apk' -print | sort | head -1)
if test -n "$apk"; then
	bsdtar -tf "$apk" > "$TMP/apk.list" 2>&1
	rc=$?
	{
		echo
		echo '#### `bsdtar -tf linux-postmarketos-qcom-msm8996 APK`'
		echo
		echo '```text'
		cat "$TMP/apk.list"
		echo "[exit status: $rc]"
		echo '```'
	} >> "$REPORT"
	test "$rc" -eq 0 || step3=FAIL
	config_member=$(rg '(^|/)config-postmarketos-qcom-msm8996$|(^|/)\.config$' "$TMP/apk.list" | head -1 || true)
	if test -n "$config_member" && bsdtar -xOf "$apk" "$config_member" > "$TMP/kernel.config" 2> "$TMP/config-extract.err"; then
		{
			echo
			echo '#### `bsdtar -xOf APK <kernel-config-member>`'
			echo
			echo '```text'
			cat "$TMP/config-extract.err"
			echo "extracted $config_member to temporary kernel.config ($(wc -c < "$TMP/kernel.config") bytes)"
			echo '[exit status: 0]'
			echo '```'
		} >> "$REPORT"
		log_command "check packaged kernel config" python3 -I "$ROOT/scripts/check_kernel_config.py" "$ROOT/kernel/lithium.config" "$TMP/kernel.config" || step3=FAIL
		{
			echo
			echo '#### Requested packaged configuration options'
			echo
			echo '```text'
			for opt in PSTORE_RAM FB_SIMPLE DRM_SIMPLEDRM FRAMEBUFFER_CONSOLE USB_DWC3_QCOM PHY_QCOM_QUSB2 USB_CONFIGFS_RNDIS USB_CONFIGFS_NCM TOUCHSCREEN_EDT_FT5X06; do
				rg "^(CONFIG_${opt}=|# CONFIG_${opt} is not set)" "$TMP/kernel.config" || echo "CONFIG_${opt}: MISSING"
			done
			echo '```'
		} >> "$REPORT"
	else
		step3=FAIL
		printf '\n```text\nFAIL: kernel config member not found or extraction failed\n```\n' >> "$REPORT"
	fi
else
	step3=FAIL
	printf '\n```text\nFAIL: linux-postmarketos-qcom-msm8996 APK not found\n```\n' >> "$REPORT"
fi

# Step 4: unpack the boot ramdisk and find the requested programs/code.
step4=PASS
log_command "extract kernel and ramdisk from boot.img" extract_boot_parts "$BOOT" "$TMP/boot-kernel" "$TMP/boot-ramdisk" || step4=FAIL
mkdir -p "$TMP/initramfs"
case $(od -An -tx1 -N6 "$TMP/boot-ramdisk" | tr -d ' \n') in
	1f8b*) gzip -dc "$TMP/boot-ramdisk" > "$TMP/initramfs.cpio" 2> "$TMP/ramdisk-decompress.err" ;;
	28b52ffd*) zstd -dc "$TMP/boot-ramdisk" > "$TMP/initramfs.cpio" 2> "$TMP/ramdisk-decompress.err" ;;
	fd377a585a00*) xz -dc "$TMP/boot-ramdisk" > "$TMP/initramfs.cpio" 2> "$TMP/ramdisk-decompress.err" ;;
	04224d18*) lz4 -dc "$TMP/boot-ramdisk" > "$TMP/initramfs.cpio" 2> "$TMP/ramdisk-decompress.err" ;;
	*) cp "$TMP/boot-ramdisk" "$TMP/initramfs.cpio"; : > "$TMP/ramdisk-decompress.err" ;;
esac
decomp_rc=$?
(cd "$TMP/initramfs" && cpio -idm --no-absolute-filenames < "$TMP/initramfs.cpio") > "$TMP/cpio.out" 2>&1
cpio_rc=$?
{
	echo
	echo '#### `decompress ramdisk; cpio -idm --no-absolute-filenames`'
	echo
	echo '```text'
	cat "$TMP/ramdisk-decompress.err"
	cat "$TMP/cpio.out"
	echo "[decompress exit status: $decomp_rc]"
	echo "[cpio exit status: $cpio_rc]"
	echo '```'
} >> "$REPORT"
test "$decomp_rc" -eq 0 && test "$cpio_rc" -eq 0 || step4=FAIL
for needle in unudhcpd telnetd fail_halt_boot debug_shell; do
	{
		echo
		echo "#### Search: \`$needle\`"
		echo
		echo '```text'
	} >> "$REPORT"
	find "$TMP/initramfs" -type f -o -type l | sort | while IFS= read -r path; do
		case ${path##*/} in *"$needle"*) echo "path: ${path#"$TMP/initramfs"/}";; esac
	done > "$TMP/path-hits"
	rg -a -n --glob '!*.ko' "$needle" "$TMP/initramfs" > "$TMP/content-hits" 2>&1 || true
	cat "$TMP/path-hits" "$TMP/content-hits" >> "$REPORT"
	if test -s "$TMP/path-hits" || test -s "$TMP/content-hits"; then
		echo "FOUND: $needle" >> "$REPORT"
	else
		echo "MISSING: $needle" >> "$REPORT"
		step4=FAIL
	fi
	echo '```' >> "$REPORT"
done

{
	echo
	echo '## Results'
	echo
	echo "Step 1: $step1 — create and audit both boot images."
	echo "Step 2: $step2 — extract and match the appended P3 DTB."
	echo "Step 3: $step3 — extract and validate the packaged kernel configuration."
	echo "Step 4: $step4 — unpack initramfs and locate the requested networking/debug components."
} >> "$REPORT"

echo "wrote $REPORT"
test "$step1$step2$step3$step4" = PASSPASSPASSPASS
