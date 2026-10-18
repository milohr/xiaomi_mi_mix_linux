# Kernel work area

- `msm8996pro-xiaomi-lithium.dts`: the Phase 3 board DTS. `patches/0001-…` carries
  the same content plus the Makefile and binding lines for the pinned kernel.
  Build and check it with `scripts/build_lithium_dtb.sh`, which runs the full schema
  check and `scripts/verify_lithium_dtb.py` against the stock DTB.
- `lithium.config`: the options this DTS needs; check a config with
  `scripts/check_kernel_config.py`.
- `panel-draft/`: Phase 6 panel driver draft (display track).

Document every memory region, GPIO, regulator and panel parameter in
`research/hardware-map.json` before adding it. Do not transplant Android DTS
or sibling-board values.
