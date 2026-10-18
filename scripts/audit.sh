#!/bin/sh
# Offline static audit of everything this port writes (kernel patches and C, the
# lithium DTB, shell, Python, APKBUILDs). Usage: sh scripts/audit.sh
# Needs the audit worktree and tools under artifacts/ (see artifacts/p10/REVIEW.md);
# exits non-zero on errors or on warnings new since the stored baselines.
set -u

ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
OUT=${AUDIT_OUT:-"$ROOT/artifacts/p10"}
WT="$OUT/linux-wt"
LOG="$OUT/logs"
BUILD="$OUT/build/audit"
DATE=${AUDIT_DATE:-$(date +%F)}
REPORT="$OUT/audit-$DATE.md"
ROWS="$OUT/.audit-rows"
FAIL=0
mkdir -p "$LOG" "$BUILD"
: >"$ROWS"
PATH="$ROOT/artifacts/toolchain/venv-audit/bin:$ROOT/artifacts/toolchain/sparse-src:$ROOT/artifacts/toolchain/bc/usr/bin:$ROOT/artifacts/toolchain/lld/bin:$ROOT/artifacts/toolchain/lld/usr/bin:$PATH"
export PATH

run_log() {
	name=$1
	shift
	printf '+ %s\n' "$*" >"$LOG/$name.log"
	"$@" >>"$LOG/$name.log" 2>&1
	rc=$?
	printf '\nexit status: %s\n' "$rc" >>"$LOG/$name.log"
	return "$rc"
}

count_errors() { grep -Eic '(^ERROR:|: error:|^FAIL|Error [0-9])' "$1" 2>/dev/null || true; }
count_warnings() { grep -Eic '(^WARNING:|: warning:|^Warning:)' "$1" 2>/dev/null || true; }
row() {
	tool=$1 files=$2 log=$3 state=$4
	err=$(count_errors "$log")
	warn=$(count_warnings "$log")
	printf '| %s | %s | %s | %s | %s |\n' "$tool" "$files" "$err" "$warn" "$state" >>"$ROWS"
}

: >"$LOG/checkpatch.log"
# The patches carry no Signed-off-by until the owner signs them: that error is
# expected and does not fail the audit; every other checkpatch error does.
for p in "$ROOT"/kernel/patches/*.patch; do
	printf '\n## %s\n' "$p" >>"$LOG/checkpatch.log"
	perl "$WT/scripts/checkpatch.pl" --strict "$p" >>"$LOG/checkpatch.log" 2>&1
done
for c in "$ROOT"/kernel/panel-draft/*.c; do
	printf '\n## %s\n' "$c" >>"$LOG/checkpatch.log"
	perl "$WT/scripts/checkpatch.pl" --strict --file "$c" >>"$LOG/checkpatch.log" 2>&1
done
grep '^ERROR:' "$LOG/checkpatch.log" | grep -v 'Missing Signed-off-by' >"$LOG/checkpatch-errors.log" || :
if [ -s "$LOG/checkpatch-errors.log" ]; then FAIL=1; fi

cp "$ROOT/packaging/pmaports/device/testing/linux-postmarketos-qcom-msm8996/config-postmarketos-qcom-msm8996.aarch64" "$BUILD/.config"
run_log olddefconfig make -C "$WT" O="$BUILD" ARCH=arm64 LLVM=1 olddefconfig || FAIL=1
CTARGETS='drivers/gpu/drm/panel/panel-xiaomi-lithium-fte716.o drivers/gpu/drm/msm/disp/mdp5/mdp5_plane.o drivers/gpu/drm/msm/disp/mdp5/mdp5_pipe.o drivers/power/supply/qcom-smbchg.o drivers/power/supply/qcom_fg.o sound/soc/codecs/tfa989x.o sound/soc/qcom/apq8096.o drivers/clk/qcom/gcc-msm8996.o'
for obj in $CTARGETS; do rm -f "$BUILD/$obj"; done
# shellcheck disable=SC2086
run_log kernel-w1 make -C "$WT" O="$BUILD" ARCH=arm64 LLVM=1 W=1 $CTARGETS || FAIL=1
W1BASE="$OUT/kernel-w1-baseline.log"
[ -e "$W1BASE" ] || cp "$LOG/kernel-w1.log" "$W1BASE"
# Host tools under scripts/ (modpost, fixdep) rebuild at will; they are not ours.
grep -Ei 'warning:|error:' "$W1BASE" | grep -v '/linux-wt/scripts/' | sort -u >"$LOG/kernel-w1-baseline.sorted" || :
grep -Ei 'warning:|error:' "$LOG/kernel-w1.log" | grep -v '/linux-wt/scripts/' | sort -u >"$LOG/kernel-w1-current.sorted" || :
comm -13 "$LOG/kernel-w1-baseline.sorted" "$LOG/kernel-w1-current.sorted" >"$LOG/kernel-w1-new.log" || :
if [ -s "$LOG/kernel-w1-new.log" ]; then FAIL=1; fi

SPARSE=$(command -v sparse 2>/dev/null || true)
[ -n "$SPARSE" ] || SPARSE=$(find "$ROOT/artifacts/toolchain" -type f -name sparse -perm -111 2>/dev/null | head -n 1)
if [ -n "$SPARSE" ]; then
	# shellcheck disable=SC2086
	run_log sparse make -C "$WT" O="$BUILD" ARCH=arm64 LLVM=1 C=2 CHECK="$SPARSE" $CTARGETS || FAIL=1
else
	printf 'MISSING: sparse (offline run; install rootlessly under artifacts/toolchain)\n' >"$LOG/sparse.log"
fi

SPATH=$(command -v spatch 2>/dev/null || true)
[ -n "$SPATH" ] || SPATH=$(find "$ROOT/artifacts/toolchain" -type f -name spatch -perm -111 2>/dev/null | head -n 1)
if [ -n "$SPATH" ]; then
	run_log coccicheck make -C "$WT" O="$BUILD" ARCH=arm64 LLVM=1 coccicheck MODE=report M=drivers/gpu/drm/panel COCCI="$SPATH" || FAIL=1
else
	printf 'MISSING: spatch/coccinelle (offline run; install rootlessly under artifacts/toolchain)\n' >"$LOG/coccicheck.log"
fi

DTPATH="$ROOT/artifacts/toolchain/venv-dtschema/bin:$PATH"
PATH=$DTPATH run_log dtbs make -C "$WT" O="$BUILD" ARCH=arm64 LLVM=1 CHECK_DTBS=y qcom/msm8996pro-xiaomi-lithium.dtb || FAIL=1
grep -E 'msm8996pro-xiaomi-lithium|qcom,haptics|fuel-gauge@4000' "$LOG/dtbs.log" >"$LOG/dtbs-lithium.log" || :
BASE="$OUT/dtbs-known-warnings.txt"
[ -e "$BASE" ] || printf 'qcom,haptics\nfuel-gauge@4000\n' >"$BASE"
DIAGBASE="$OUT/dtbs-baseline.log"
[ -e "$DIAGBASE" ] || cp "$LOG/dtbs-lithium.log" "$DIAGBASE"
sort -u "$DIAGBASE" >"$LOG/dtbs-baseline.sorted"
sort -u "$LOG/dtbs-lithium.log" >"$LOG/dtbs-current.sorted"
comm -13 "$LOG/dtbs-baseline.sorted" "$LOG/dtbs-current.sorted" | grep -Evf "$BASE" >"$LOG/dtbs-new-warnings.log" || :
if [ -s "$LOG/dtbs-new-warnings.log" ]; then FAIL=1; fi

STOCK="$ROOT/artifacts/stock/audit/boot.img.dtb-5"
DTB="$BUILD/arch/arm64/boot/dts/qcom/msm8996pro-xiaomi-lithium.dtb"
VENV="$ROOT/artifacts/toolchain/venv-lmdpdg/bin/python"
[ -x "$VENV" ] || VENV=python3
run_log verify-dtb "$VENV" "$ROOT/scripts/verify_lithium_dtb.py" "$DTB" "$STOCK" || FAIL=1

SHELLCHECK=$(command -v shellcheck 2>/dev/null || true)
if [ -n "$SHELLCHECK" ]; then
	# Only scripts this project wrote: not the kernel, lk2nd or downstream trees.
	find "$ROOT/scripts" "$ROOT/artifacts" -type f -name '*.sh' \
		-not -path '*/linux-wt/*' -not -path '*/build/*' -not -path '*/downstream/*' \
		-not -path '*/toolchain/*' -not -path '*/sources/*' -not -path '*/superseded/*' \
		-not -path '*/extract/*' -not -path '*/stock/*' \
		-print >"$LOG/shell-files.txt"
	# shellcheck disable=SC2046
	run_log shellcheck "$SHELLCHECK" -S warning -f gcc $(cat "$LOG/shell-files.txt") || FAIL=1
else
	printf 'MISSING: shellcheck\n' >"$LOG/shellcheck.log"
fi

RUFF=$(command -v ruff 2>/dev/null || true)
[ -n "$RUFF" ] || RUFF=$(find "$ROOT/artifacts/toolchain" -type f -name ruff -perm -111 2>/dev/null | head -n 1)
if [ -n "$RUFF" ]; then
	# Bug-class rules only (pyflakes, syntax errors, bugbear; B023 misfires on
	# lambdas used within the iteration); prefixed so the
	# report counts each finding as a warning.
	run_log ruff sh -c '"$1" check --select F,E9,B --ignore B023,B905 --output-format concise "$2" | sed -n "/:[0-9]*:[0-9]*: /s/^/warning: /p"' \
		ruff "$RUFF" "$ROOT/scripts"
	grep -q '^warning: .*:[0-9]*:[0-9]*: ' "$LOG/ruff.log" && FAIL=1
else
	printf 'MISSING: ruff (install into a rootless artifacts/toolchain venv)\n' >"$LOG/ruff.log"
fi

APK=$(command -v apkbuild-lint 2>/dev/null || true)
[ -n "$APK" ] || APK="$ROOT/artifacts/toolchain/atools/usr/bin/apkbuild-lint"
if [ -x "$APK" ]; then
	find "$ROOT/packaging/pmaports" -type f -name APKBUILD -print >"$LOG/apkbuild-files.txt"
	if "$APK" --help >/dev/null 2>&1; then
		# shellcheck disable=SC2046
		run_log apkbuild-lint "$APK" $(cat "$LOG/apkbuild-files.txt") || FAIL=1
	elif [ -x "$ROOT/artifacts/toolchain/atools/lib/ld-musl-x86_64.so.1" ]; then
		# shellcheck disable=SC2046
		run_log apkbuild-lint "$ROOT/artifacts/toolchain/atools/lib/ld-musl-x86_64.so.1" \
			--library-path "$ROOT/artifacts/toolchain/atools/lib" "$APK" \
			$(cat "$LOG/apkbuild-files.txt") || FAIL=1
	else
		printf 'MISSING: runnable apkbuild-lint; main session command: pmbootstrap lint\n' >"$LOG/apkbuild-lint.log"
	fi
else
	printf 'MISSING: apkbuild-lint; main session command: pmbootstrap lint\n' >"$LOG/apkbuild-lint.log"
fi

cat >"$REPORT" <<EOF
# Phase 10 static audit — $DATE

Pinned kernel: \`$(git -C "$WT" rev-parse HEAD)\`

| Tool | Files/scope | Errors | Warnings | New since baseline/status |
|---|---|---:|---:|---|
EOF
row checkpatch 'kernel patches, panel C' "$LOG/checkpatch.log" "$(wc -l <"$LOG/checkpatch-errors.log") errors besides Missing Signed-off-by"
row 'kernel W=1' 'project C objects' "$LOG/kernel-w1.log" "$(wc -l <"$LOG/kernel-w1-new.log") new output lines"
row sparse 'project C objects' "$LOG/sparse.log" "$([ -n "$SPARSE" ] && printf executed || printf MISSING)"
row coccicheck 'panel directory' "$LOG/coccicheck.log" "$([ -n "$SPATH" ] && printf executed || printf MISSING)"
row CHECK_DTBS 'lithium DTB' "$LOG/dtbs-lithium.log" "$(wc -l <"$LOG/dtbs-new-warnings.log") new warning lines"
row verify_lithium_dtb 'built DTB vs stock DTB 5' "$LOG/verify-dtb.log" 'stock evidence'
row shellcheck 'project shell scripts' "$LOG/shellcheck.log" "$([ -n "$SHELLCHECK" ] && printf executed || printf MISSING)"
row ruff 'scripts/*.py recursively' "$LOG/ruff.log" "$([ -n "$RUFF" ] && printf executed || printf MISSING)"
row apkbuild-lint 'packaging APKBUILDs' "$LOG/apkbuild-lint.log" "$([ -x "$APK" ] && printf executed || printf MISSING)"
cat "$ROWS" >>"$REPORT"

cat >>"$REPORT" <<EOF

Raw logs are in \`artifacts/p10/logs/\`. Known inherited DT warnings are patterns in
\`artifacts/p10/dtbs-known-warnings.txt\`; only unmatched lithium warning lines make the
DT schema row fail. Missing optional host tools are reported explicitly and do not by
themselves change the exit status.
EOF

exit "$FAIL"
