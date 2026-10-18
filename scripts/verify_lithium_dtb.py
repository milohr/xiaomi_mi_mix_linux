#!/usr/bin/env python3
"""Check the built lithium Linux DTB against lithium's stock DTB.

Read-only and offline. Each check pairs a node of the built mainline DTB with
the stock node it was derived from and compares the hardware values:
identity, reserved memory coverage, the voltage of every rail per consumer,
the console UART, and the keys. Exits 1 on any mismatch.
Usage: verify_lithium_dtb.py BUILT_DTB STOCK_DTB
Needs pylibfdt (artifacts/toolchain/venv-lmdpdg).
"""
import struct
import sys

import libfdt

NF = (libfdt.NOTFOUND,)

# (built node, built supply, stock node, stock supply)
SUPPLIES = [
    ("/soc@0/ufshc@624000", "vcc-supply", "/soc/ufshc@624000", "vcc-supply"),
    ("/soc@0/ufshc@624000", "vccq-supply", "/soc/ufshc@624000", "vccq-supply"),
    ("/soc@0/ufshc@624000", "vccq2-supply", "/soc/ufshc@624000", "vccq2-supply"),
    ("/soc@0/phy@627000", "vdda-phy-supply", "/soc/ufsphy@627000", "vdda-phy-supply"),
    ("/soc@0/phy@627000", "vdda-pll-supply", "/soc/ufsphy@627000", "vdda-pll-supply"),
    ("/soc@0/phy@7411000", "vdda-pll-supply", "/soc/qusb@7411000", "vdda18-supply"),
    ("/soc@0/phy@7411000", "vdda-phy-dpdm-supply", "/soc/qusb@7411000", "vdda33-supply"),
]
# (built node, property, stock node, property)
CURRENTS = [
    ("/soc@0/ufshc@624000", p, "/soc/ufshc@624000", p)
    for p in ("vcc-max-microamp", "vccq-max-microamp", "vccq2-max-microamp")
]

failures = 0


def check(ok, label, detail=""):
    global failures
    failures += 0 if ok else 1
    print(f"{'ok  ' if ok else 'FAIL'} {label}{': ' + detail if detail else ''}")


class Tree:
    def __init__(self, path):
        self.fdt = libfdt.Fdt(open(path, "rb").read())
        self.phandles = {}
        self._walk(0, "")

    def _walk(self, off, path):
        ph = self.raw(off, "phandle")
        if ph is not None:
            self.phandles[self.u32(ph)[0]] = off
        child = self.fdt.first_subnode(off, quiet=NF)
        while child >= 0:
            self._walk(child, f"{path}/{self.fdt.get_name(child)}")
            child = self.fdt.next_subnode(child, quiet=NF)

    def raw(self, off, name):
        try:
            return self.fdt.getprop(off, name)
        except libfdt.FdtException:
            return None

    @staticmethod
    def u32(raw):
        return list(struct.unpack(f">{len(raw) // 4}I", bytes(raw)))

    def node(self, path):
        return self.fdt.path_offset(path)

    def prop_u32(self, path, name):
        raw = self.raw(self.node(path), name)
        return None if raw is None else self.u32(raw)

    def text(self, off, name):
        raw = self.raw(off, name)
        return None if raw is None else bytes(raw).rstrip(b"\0").decode()

    def supply_voltage(self, path, name):
        ph = self.prop_u32(path, name)
        if ph is None:
            return None
        reg = self.phandles[ph[0]]
        lo, hi = self.raw(reg, "regulator-min-microvolt"), self.raw(reg, "regulator-max-microvolt")
        return (self.u32(lo)[0], self.u32(hi)[0]) if lo is not None else None

    def static_reserved(self):
        regions = []
        rm = self.node("/reserved-memory")
        child = self.fdt.first_subnode(rm, quiet=NF)
        while child >= 0:
            reg = self.raw(child, "reg")
            if reg is not None and self.text(child, "status") in (None, "okay", "ok"):
                cells = self.u32(reg)
                regions.append(((cells[0] << 32) | cells[1], (cells[2] << 32) | cells[3],
                                self.fdt.get_name(child)))
            child = self.fdt.next_subnode(child, quiet=NF)
        return regions


def covered(start, size, regions):
    pos, end = start, start + size
    for base, length, _ in sorted(regions):
        if base <= pos < base + length:
            pos = base + length
        if pos >= end:
            return True
    return pos >= end


def main():
    built, stock = Tree(sys.argv[1]), Tree(sys.argv[2])

    for prop in ("qcom,board-id", "qcom,pmic-id"):
        check(built.prop_u32("/", prop) == stock.prop_u32("/", prop), f"identity {prop}",
              str(built.prop_u32("/", prop)))
    check(built.prop_u32("/", "qcom,msm-id") == stock.prop_u32("/", "qcom,msm-id"),
          "identity qcom,msm-id", str(built.prop_u32("/", "qcom,msm-id")))

    ours = built.static_reserved()
    stock_regions = stock.static_reserved()
    for base, size, name in stock_regions:
        check(covered(base, size, ours), f"stock reservation {name} kept",
              f"{base:#x}+{size:#x}")
    for base, size, name in ours:
        inside = covered(base, size, stock_regions)
        check(inside, f"built reservation {name} inside a stock reservation",
              f"{base:#x}+{size:#x}")

    for bnode, bsup, snode, ssup in SUPPLIES:
        b, s = built.supply_voltage(bnode, bsup), stock.supply_voltage(snode, ssup)
        check(b is not None and b == s, f"{bnode} {bsup} voltage", f"built {b} stock {s}")
    for bnode, bprop, snode, sprop in CURRENTS:
        b, s = built.prop_u32(bnode, bprop), stock.prop_u32(snode, sprop)
        check(b == s, f"{bnode} {bprop}", f"built {b} stock {s}")

    stdout = built.text(built.node("/chosen"), "stdout-path").split(":")[0]
    uart = built.text(built.node("/aliases"), stdout)
    uart_reg = built.prop_u32(uart, "reg")
    stock_uart = stock.prop_u32("/soc/serial@075b0000", "reg")
    check(stock.text(stock.node("/soc/serial@075b0000"), "status") in ("ok", "okay")
          and uart_reg == stock_uart, "console UART is the enabled stock lsuart",
          f"{uart} reg {uart_reg}")
    pins = built.phandles[built.prop_u32(uart, "pinctrl-0")[0]]
    pin_list = bytes(built.raw(pins, "pins")).split(b"\0")
    check(b"gpio4" in pin_list and b"gpio5" in pin_list
          and built.text(pins, "function") == "blsp_uart8", "console UART pins gpio4/5 blsp_uart8")

    key = built.node("/gpio-keys/key-volume-up")
    gp = built.u32(built.raw(key, "gpios"))
    skey = stock.node("/soc/gpio_keys/vol_up")
    sgp = stock.u32(stock.raw(skey, "gpios"))
    check(gp[1:] == sgp[1:] and built.u32(built.raw(key, "linux,code")) == stock.u32(stock.raw(skey, "linux,code")),
          "volume up: PMIC GPIO, polarity and code", f"gpio {gp[1:]} code 115")
    resin = built.node("/soc@0/spmi@400f000/pmic@0/pon@800/resin")
    check(built.u32(built.raw(resin, "linux,code"))[0] == 114
          and built.text(resin, "status") in (None, "okay"), "volume down on PON resin (stock pon_2 code 114)")

    print(f"{'all checks passed' if not failures else f'{failures} check(s) failed'}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
