# FTE716 panel driver draft (Phase 6 preparation)

**Draft. Not hardware tested. Not wired into any DTS or kernel build.**

- `panel-xiaomi-lithium-fte716.c.in`: the original driver around generated tables.
- `panel-xiaomi-lithium-fte716.c`: the assembled output. Do not edit it by hand;
  edit the template and run `scripts/build_panel_draft.sh`.

The command tables are lmdpdg `--dumb-dcs` output from stock `boot.img.dtb-5`.
`scripts/verify_panel_draft.py` checks every packet against the audited stock
streams. Status, open questions and next steps: [docs/DISPLAY.md](../../docs/DISPLAY.md).
