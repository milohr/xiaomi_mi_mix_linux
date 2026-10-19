# Hardware acceleration review (2026-10-19)

Which fixed-function blocks of the Snapdragon 821 are used, and how to use the rest.

| Block | Kernel | Used by today | Gap | Plan, effort |
|---|---|---|---|---|
| **Video decoder** (Venus 3.43): H.264, VP9, HEVC, VP8, VC-1, MPEG-2/4, H.263 -> NV12 or UBWC NV12 | venus, `/dev/video7` | mpv (`hwdec=v4l2m2m-copy`) | Browsers decode on the CPU | **Firefox**: needs FFmpeg's v4l2m2m decoders to return DRM PRIME frames (out-of-tree drmprime patches; build started earlier, parked), then Firefox's V4L2 pref; YouTube must serve VP9/H.264, not AV1 (Venus has no AV1). Medium. **Angelfish/QtWebEngine**: Chromium in QtWebEngine only knows VA-API on Linux; a V4L2 decoder means rebuilding QtWebEngine with Chromium's V4L2 path. Very large; use Firefox or PlasmaTube for video. **PlasmaTube** (libmpv): verify it asks for hwdec (libmpv ignores /etc/mpv/mpv.conf unless told). Small |
| **Video encoder** (Venus): H.264, HEVC, VP8, MPEG-4, H.263 from NV12 | venus, `/dev/video6` | nothing | H.264 encoding failed on HFI 3xx (8x8 transform property); patch 0044 fixes it: 720p in 6.2 s per 10 s (libx264 10 s, CPU-bound) | FFmpeg asks for headers in a separate buffer; Venus 3xx emits none then (the driver default, joined with the first frame, works): select joined mode for HFI 3xx in the driver or in FFmpeg. Then camera recording (Qt Multimedia / Kamoso) can use it. Also: inputs must be 32-line aligned or FFmpeg's copy overruns (1280x720 crashed, 1280x704 works). Small-medium |
| **Camera ISP** (CAMSS VFE) | qcom-camss: raw (RDI) path only for Bayer sensors | libcamera simple pipeline + GPU software ISP | No hardware demosaic/AWB/denoise in mainline | Keep the GPU ISP; fix the RDI stride so frames import into the GPU without a CPU copy (~15 fps now), add autofocus. Medium |
| **JPEG encoder** | none for MSM8996 | — | — | Not worth it; libjpeg-turbo with NEON is fast enough |
| **GPU** (Adreno 530) | msm + Mesa freedreno | everything | Binning-overflow workaround costs ~20 % in 3D; no Vulkan (turnip starts at a6xx), no OpenCL (rusticl freedreno is a6xx+) | Fix the a5xx visibility-stream overflow in Mesa, then drop `nobin`/`sysmem`. Large |
| **Display controller** (MDP5 planes) | msm | KWin, primary plane | Unverified whether KWin scans out fullscreen video directly (saves GPU composition power) | Check KWin's plane use during fullscreen mpv. Small |
| **DSPs**: aDSP, SLPI, modem | remoteproc | audio, sensors, modem | No general compute offload on Linux (FastRPC userspace) | — |
| **Crypto engine** (qcrypto) | `qcrypto: Failed to get TX DMA channel`, deferred | — | Hardware AES not bound | Low value: Kryo's ARMv8 crypto instructions are faster for disk/TLS. Optional DT fix |

Order by daily impact: Firefox hardware decode (YouTube on CPU heats the phone) → encoder headers
+ camera recording → camera GPU import / autofocus → Mesa overflow fix → KWin direct scanout check.
