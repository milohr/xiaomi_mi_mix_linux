# Panel translation workflow

`python3 scripts/parse_panel.py examples/panel-on.hex --format json`

The input must be one raw byte block or one DTS assignment containing a single
bracketed byte block. Qualcomm records are: type, last, virtual channel, ACK,
delay in milliseconds, big-endian 16-bit payload length, then payload.

The parser preserves all headers, payload bytes and source offsets. It rejects
truncated headers/payloads and malformed byte tokens. It does not normalize
short-packet padding, interpret vendor opcodes, or assume all packets are DCS.
Use `--format c` for a local audit-table structure; this is not an executable
DRM panel driver or a standard upstream `mipi_dsi_dcs_cmd` type.

Before converting to upstream helpers, check DCS versus generic packet types,
short-packet padding, last-command grouping, virtual channel, ACK behavior and
on/off command-state LP/HS properties. Payload length alone may not preserve
an explicitly requested packet type. Include supply/reset sequencing and delays
from surrounding source. Identify the actual panel variant before use.

The bundled input is synthetic, never a sequence to send to this device.
