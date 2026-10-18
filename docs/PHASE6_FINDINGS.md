# Phase 6 findings — storage, USB (2026-10-18, in progress)

Status: **UFS storage and USB networking work together** (boot U9). The rest of P6 (display
driver, touch, power) follows. Raw logs: `artifacts/p6/` (ignored). Live partition map:
`research/live-partitions-p6.json`.

## UFS: the link needed load votes on its rails

P5 ended with the UFS link down (`dl_err` storm, no disks). The other agent's audit
(`artifacts/p6/ufs-audit.md`) found our regulators lacked `regulator-allow-set-load`, which
`msm8996-xiaomi-common.dtsi` and the OnePlus tree set on every UFS rail. With the flag the
UFS driver may vote the high-power mode on the rails, and the link comes up at once: six LUNs,
`TOSHIBA THGBF7T0L8LBATAB`, `sda` 123 GB (userdata `sda15`, 114 GiB), the small LUNs with
`system`, `boot`, `modem`, `persist`, `recovery`, `cache` among the 68 labelled partitions.

Kept in the DTS: the flag on **L20 (vcc) and L25 (vccq)** only. L28 and L12 are shared with
the USB PHY; the flag there was tested (U1, U2) and made no difference to UFS.

## USB: a race with UFS's first idle, fixed by holding the reference clock

With UFS working, the USB gadget died in every run (`dwc3: failed to enable ep0out`,
`No resource for ep0out`, endpoint commands timing out), and with it the debug shell. Bisected
over nine RAM-only boots, one change each:

| Boot | Change | UFS | USB |
|---|---|---|---|
| P5 | — (UFS failing) | no | yes |
| U1 | allow-set-load on L20 L25 S4 L28 L12 | yes | no |
| U2 | … on L20 L25 L28 | yes | no |
| U3 | … on L20 L25 | yes | no |
| U4 | U3 + `initcall_blacklist=ufs_qcom_pltform_init` | off | yes |
| U5 | U3 + `snps,usb2-gadget-lpm-disable` | yes | no |
| U7 | U3 + USB PHY `vdd-supply` L28 | yes | no |
| U8 | U3 + `tp_printk trace_event=…` (slower boot) | yes | **yes** |
| U9 | U3 + `&usb3` holds `RPM_SMD_LN_BB_CLK` | yes | **yes** |

U8's trace shows what UFS switches off when it idles at 4–7 s: its own clocks, its PHY's symbol
clocks, the 0.925 V rail, and **`ln_bb_clk`**, the RPM's low-noise XO buffer, whose prepare
count reached zero three times. The USB PHY's reference (`GCC_RX1_USB2_CLKREF_CLK`) is derived
from that buffer (`gcc`'s `cxo2` input is `RPM_SMD_LN_BB_CLK`), yet nothing on this board held
it: the working siblings enable PCIe for Wi-Fi, whose PHY also uses `ln_bb_clk`, so it never
turns off for them. The failure is a race: the initramfs starts the gadget at about 6.5 s,
inside UFS's idle transition; whenever the start fell outside that window (P5 at 9.5 s, U4 without
UFS, U8 slowed by tracing) USB worked.

Fix (U9, now in the DTS and patch 0001): the `qcom,msm8996-dwc3` glue lists
`<&rpmcc RPM_SMD_LN_BB_CLK>` as a sixth clock, so `dwc3-qcom` (`clk_bulk_get_all`) keeps it on
while USB is active. The binding's schema allows five clocks, so the schema check reports the
extra entry; it is a board-level workaround. A proper fix (keeping the buffer on in
`clk-smd-rpm`, or a PHY/glue ordering fix) is being researched (`artifacts/p6/usb-ufs-race.md`
when done).

Verified on U9: the gadget started at 6.67 s, inside the old failure window, and works.

## Procedure lessons

- `scripts/swap_bootimg_dtb.py` made each DTS experiment a 2-minute build instead of a 2-hour
  package build. The final state still needs a real package build (kernel r2 carries the fix).
- `tp_printk trace_event=…` on the command line, read back through lk2nd's ramoops, gave the
  decisive evidence without a serial console.
- The ramoops console holds about 45 s of a verbose boot; filter the events.

## Next

1. Rootfs on `userdata` (runbook in `artifacts/p6/rootfs-runbook.md` when done; the user has
   allowed erasing Android), then the first boot into the installed system.
2. Touch (patch 0002, `artifacts/p6/touch-test.sh`), power (`artifacts/p6/lithium-power.dtsi`),
   display (`artifacts/p6/display-plan.md`).
3. Full package build (kernel r2 + the P6 config: `artifacts/p6/config-…aarch64.p6`).
