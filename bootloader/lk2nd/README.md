# Lithium lk2nd board entry

This directory holds the original lithium board match used with pinned lk2nd
commit `8b46487c4c76776c4f2f61468d44a74c69e6b9ea`.

Apply `0001-msm8996-add-xiaomi-lithium.patch` at the root of that checkout, then run
`scripts/build_lk2nd.sh`. The standalone DTS is retained for quick review. It is
an lk2nd board selector, not the Linux hardware-description DTS.

The match tuple was independently compiled and decoded before any device use.
The build artifact is ignored by Git and described by
`research/lk2nd-build.json`. Building this image does not authorize flashing it.

`0002-msm8996-xiaomi-lithium-select-panel.patch` is a **draft** on top of 0001.
It lets lk2nd map the stock `mdss_mdp.panel=` name to a Linux panel compatible.
It is not in the reviewed Phase 2 image. Its separate build and hashes are in
`research/display-draft-build.json`; see `docs/DISPLAY.md`.
