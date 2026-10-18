# Project execution rules

Work on lithium only; never reuse flare hardware addresses, modules or images.
Read docs/HANDOFF.md and research/project.json before continuing.
Distinguish live observation, source evidence, user report and hypothesis.
Record URL, commit, SHA-256 and acquisition date for inputs; do not invent pins.
Author DTS against bindings and verified evidence; do not transplant vendor DTS.
Keep raw device dumps, proprietary blobs and source checkouts out of Git.
Prefer read-only collection and offline builds. No device writes, reboots or boot
experiments are authorized merely by preparing this repository. Review a concrete
image and recovery plan with the user before device-changing experiments.
Do not fabricate memory addresses, GPIO assignments, panel sequences or timings.
Update phase gates and handoff after meaningful progress. Run parser tests after
parser changes. Do not label illustrative files as working device support.
