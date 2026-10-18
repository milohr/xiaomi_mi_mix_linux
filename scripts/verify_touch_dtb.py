#!/usr/bin/env python3
"""Check the touchscreen of a built lithium DTB against lithium's stock DTB.

Read-only and offline. Pairs the mainline touchscreen@38 (patch 0002) with the
stock ft5x46_i2c@38 node: the bus, the address, the interrupt and reset GPIOs
(the stock driver reads irq-gpio, not the node's stale "interrupts"), the
supply voltage and the panel size. Exits 1 on any mismatch.
Usage: verify_touch_dtb.py BUILT_DTB STOCK_DTB
Needs pylibfdt (artifacts/toolchain/venv-lmdpdg).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_lithium_dtb as v  # noqa: E402

BUILT_BUS = "/soc@0/i2c@75ba000"
STOCK_BUS = "/soc/i2c@75ba000"
STOCK_TS = STOCK_BUS + "/ft5x46_i2c@38"
IRQ_TYPE_EDGE_FALLING = 2
GPIO_ACTIVE_LOW = 1


def main():
    built, stock = v.Tree(sys.argv[1]), v.Tree(sys.argv[2])
    ts = built.node(BUILT_BUS + "/touchscreen@38")
    sts = stock.node(STOCK_TS)

    check = v.check
    check(built.text(built.node(BUILT_BUS), "status") == "okay", "i2c@75ba000 enabled")
    check(built.prop_u32(BUILT_BUS, "reg")[0] == stock.prop_u32(STOCK_BUS, "reg")[0],
          "same bus as stock", hex(built.prop_u32(BUILT_BUS, "reg")[0]))
    freq = built.prop_u32(BUILT_BUS, "clock-frequency")
    check(freq == stock.prop_u32(STOCK_BUS, "qcom,clk-freq-out"), "bus clock", str(freq))
    check(built.u32(built.raw(ts, "reg")) == stock.u32(stock.raw(sts, "reg")), "address 0x38")
    check(built.text(ts, "compatible") == "focaltech,ft8716", "compatible focaltech,ft8716")

    irq = built.u32(built.raw(ts, "interrupts-extended"))
    stock_irq = stock.u32(stock.raw(sts, "ft5x46_i2c,irq-gpio"))
    check(irq[1] == stock_irq[1], "interrupt on the stock irq-gpio", f"gpio {irq[1]}")
    check(irq[2] == IRQ_TYPE_EDGE_FALLING, "falling edge, as the stock driver requests it")
    reset = built.u32(built.raw(ts, "reset-gpios"))
    stock_reset = stock.u32(stock.raw(sts, "ft5x46_i2c,reset-gpio"))
    check(reset[1] == stock_reset[1] and reset[2] == GPIO_ACTIVE_LOW,
          "reset on the stock reset-gpio, active low", f"gpio {reset[1]}")

    for bsup, ssup in (("vcc-supply", "vdd-supply"), ("iovcc-supply", "vddio-supply")):
        b = built.supply_voltage(BUILT_BUS + "/touchscreen@38", bsup)
        s = stock.supply_voltage(STOCK_TS, ssup)
        check(b is not None and b == s, f"{bsup} voltage", f"built {b} stock {s}")
    ph = built.prop_u32(BUILT_BUS + "/touchscreen@38", "vcc-supply")[0]
    check(built.raw(built.phandles[ph], "regulator-always-on") is not None,
          "L14 kept on (the bootloader splash shares it)")

    pins = built.phandles[built.u32(built.raw(ts, "pinctrl-0"))[0]]
    check(built.text(pins, "pins") == "gpio125" and built.raw(pins, "bias-pull-up") is not None
          and built.u32(built.raw(pins, "drive-strength"))[0] == 16,
          "interrupt pin: gpio125, pull-up, 16 mA (stock ts_active)")

    for axis, stock_prop in (("x", "ft5x46_i2c,x-max"), ("y", "ft5x46_i2c,y-max")):
        b = built.u32(built.raw(ts, f"touchscreen-size-{axis}"))[0]
        s = stock.u32(stock.raw(sts, stock_prop))[0]
        check(b == s, f"touchscreen-size-{axis}", f"built {b} stock {s}")

    print(f"{'all checks passed' if not v.failures else f'{v.failures} check(s) failed'}")
    sys.exit(1 if v.failures else 0)


if __name__ == "__main__":
    main()
