#!/bin/sh
# Leak soak test, run on the phone as the desktop user (needs sudo for debugfs):
#   sh soak.sh [ROUNDS]
# Each round opens a few web pages in Angelfish, closes it, lets things settle,
# then samples GPU buffers, kernel memory and faults. A leak shows as a value
# that keeps climbing round after round instead of returning to its baseline.
set -u
rounds=${1:-5}
export XDG_RUNTIME_DIR=/run/user/$(id -u) WAYLAND_DISPLAY=wayland-1 QT_QPA_PLATFORM=wayland
export DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus
pages="https://en.wikipedia.org/wiki/Xiaomi_Mi_MIX https://www.kde.org https://www.youtube.com"

sample() {
	gem=$(sudo cat /sys/kernel/debug/dri/0/gem | awk '/^Total:/{printf "%d %d", $2, $4/1048576}')
	slab=$(awk '/^Slab:/{print int($2/1024)}' /proc/meminfo)
	avail=$(awk '/^MemAvailable:/{print int($2/1024)}' /proc/meminfo)
	swap=$(awk '/^SwapTotal:/{t=$2} /^SwapFree:/{f=$2} END{print int((t-f)/1024)}' /proc/meminfo)
	faults=$(sudo dmesg | grep -ciE "gpu fault|iommu.*fault")
	warns=$(sudo dmesg | grep -cE "WARNING:|BUG:|Oops")
	printf "%-6s gem_objs=%-6s gem_MB=%-5s slab_MB=%-4s avail_MB=%-5s swap_MB=%-5s faults=%s warns=%s\n" \
		"$1" ${gem% *} ${gem#* } "$slab" "$avail" "$swap" "$faults" "$warns"
}

pkill -x angelfish; sleep 3
sample base
for r in $(seq 1 "$rounds"); do
	for u in $pages; do
		(setsid angelfish "$u" >/dev/null 2>&1 &)
		sleep 12
	done
	pkill -x angelfish; sleep 8
	sample "r$r"
done
