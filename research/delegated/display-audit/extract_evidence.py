#!/usr/bin/env python3
"""Regenerate the lithium display evidence from pinned sources and stock DTBs.

Read-only: it reads the three pinned LineageOS checkouts, the pinned MSM8996
mainline tree and the extracted stock DTBs, and writes JSON next to itself.
Standard library only.

    python3 -I extract_evidence.py \
        --kernel-src  <android_kernel_xiaomi_msm8996 @ 4aa1814c...> \
        --device-src  <android_device_xiaomi_lithium @ bac0b4e1...> \
        --common-src  <android_device_xiaomi_msm8996-common @ 7486d07e...> \
        --mainline-src <msm8996-mainline/linux @ 1aed438c...> \
        --stock-dir   artifacts/stock/audit
"""
import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

PINS = {
    "kernel": ("https://github.com/LineageOS/android_kernel_xiaomi_msm8996.git",
               "lineage-18.1", "4aa1814c63b82ce67d0ef0434ca510be94bb8284"),
    "device": ("https://github.com/LineageOS/android_device_xiaomi_lithium.git",
               "lineage-19.1", "bac0b4e18fc2c6d86d7c79b2764c6e575ad140ec"),
    "common": ("https://github.com/LineageOS/android_device_xiaomi_msm8996-common.git",
               "lineage-19.1", "7486d07ec3f7d5413a53009d63fe98c783667d15"),
    "mainline": ("https://gitlab.com/msm8996-mainline/linux.git",
                 "refs/tags/v6.19.5-msm8996", "1aed438cb5f49d7a61593f764d4a82f83b14114f"),
}

QCOM = "arch/arm/boot/dts/qcom/"
MDSS = "drivers/video/msm/mdss/"

# Stock DTBs whose qcom,board-id is <38 0> (lithium).
LITHIUM_DTBS = ["boot.img.dtb-4", "boot.img.dtb-5",
                "recovery.img.dtb-4", "recovery.img.dtb-5"]

VARIANTS = {
    "sharp": {"file": QCOM + "dsi-panel-sharp-fte716-1080p-video.dtsi",
              "node": "qcom,mdss_dsi_sharp_fte716_1080p_video",
              "label": "dsi_sharp_fte716_1080p_video",
              "out": "panel-sharp-fte716-1080p-video.json"},
    "auo": {"file": QCOM + "dsi-panel-auo-fte716-1080p-video.dtsi",
            "node": "qcom,mdss_dsi_auo_fte716_1080p_video",
            "label": "dsi_auo_fte716_1080p_video",
            "out": "panel-auo-fte716-1080p-video.json"},
}

STREAMS = [
    ("on_command", "qcom,mdss-dsi-on-command", "qcom,mdss-dsi-on-command-state"),
    ("off_command", "qcom,mdss-dsi-off-command", "qcom,mdss-dsi-off-command-state"),
    ("displayon_command", "qcom,mdss-dsi-displayon-command",
     "qcom,mdss-dsi-displayon-command-state"),
    ("displayoff_command", "qcom,mdss-dsi-displayoff-command",
     "qcom,mdss-dsi-displayoff-command-state"),
]

# Data types from drivers/video/msm/mdss/mdss_dsi_cmd.h:47-70 (downstream).
DTYPES = {
    0x05: ("DTYPE_DCS_WRITE", "dcs", "short", 0),
    0x15: ("DTYPE_DCS_WRITE1", "dcs", "short", 1),
    0x39: ("DTYPE_DCS_LWRITE", "dcs", "long", None),
    0x06: ("DTYPE_DCS_READ", "dcs", "short", 0),
    0x03: ("DTYPE_GEN_WRITE", "generic", "short", 0),
    0x13: ("DTYPE_GEN_WRITE1", "generic", "short", 1),
    0x23: ("DTYPE_GEN_WRITE2", "generic", "short", 2),
    0x29: ("DTYPE_GEN_LWRITE", "generic", "long", None),
    0x04: ("DTYPE_GEN_READ", "generic", "short", 0),
    0x14: ("DTYPE_GEN_READ1", "generic", "short", 1),
    0x24: ("DTYPE_GEN_READ2", "generic", "short", 2),
    0x37: ("DTYPE_MAX_PKTSIZE", "control", "short", None),
}

# MIPI DCS opcodes (include/video/mipi_display.h names).
DCS = {
    0x10: "MIPI_DCS_ENTER_SLEEP_MODE", 0x11: "MIPI_DCS_EXIT_SLEEP_MODE",
    0x28: "MIPI_DCS_SET_DISPLAY_OFF", 0x29: "MIPI_DCS_SET_DISPLAY_ON",
    0x2A: "MIPI_DCS_SET_COLUMN_ADDRESS", 0x2B: "MIPI_DCS_SET_PAGE_ADDRESS",
    0x35: "MIPI_DCS_SET_TEAR_ON", 0x38: "MIPI_DCS_EXIT_IDLE_MODE",
    0x39: "MIPI_DCS_ENTER_IDLE_MODE", 0x51: "MIPI_DCS_SET_DISPLAY_BRIGHTNESS",
    0x53: "MIPI_DCS_WRITE_CONTROL_DISPLAY", 0x55: "MIPI_DCS_WRITE_POWER_SAVE",
}

VSYNC_PERIOD_MS = 17  # drivers/video/msm/mdss/mdss_dsi_host.c:33


# --------------------------------------------------------------------------
# provenance helpers

def git_head(path):
    return subprocess.run(["git", "-C", path, "rev-parse", "HEAD"], check=True,
                          capture_output=True, text=True).stdout.strip()


class Repo:
    def __init__(self, rid, root):
        self.id, self.root = rid, root
        self.url, self.ref, self.commit = PINS[rid]
        head = git_head(root)
        if head != self.commit:
            sys.exit("%s: checkout is %s, pin is %s" % (rid, head, self.commit))

    def lines(self, rel):
        with open(os.path.join(self.root, rel), encoding="utf-8", errors="replace") as f:
            return f.read().split("\n")

    def find(self, rel, needle, after=None, regex=False):
        """1-based line of the first match of needle (after the line matching `after`)."""
        lines = self.lines(rel)
        start = 0
        if after is not None:
            start = self.find(rel, after, regex=regex)
        for i in range(start, len(lines)):
            hit = re.search(needle, lines[i]) if regex else needle in lines[i]
            if hit:
                return i + 1
        raise LookupError("%s: %r not found in %s" % (self.id, needle, rel))

    def ref_(self, rel, needle, after=None, end=None):
        line = self.find(rel, needle, after)
        r = {"repository": self.url, "commit": self.commit, "path": rel, "line": line}
        if end is not None:
            r["line_end"] = self.find(rel, end, after=needle if after is None else after)
        return r


# --------------------------------------------------------------------------
# flattened device tree reader

def fdt_parse(blob):
    magic, _total, off_struct, off_strings = struct.unpack_from(">4I", blob, 0)
    if magic != 0xD00DFEED:
        raise ValueError("bad FDT magic")
    strings = blob[off_strings:]
    pos, path, stack, node = off_struct, [], [], None
    root = {"name": "", "props": {}, "children": [], "path": "/"}
    while True:
        (tok,) = struct.unpack_from(">I", blob, pos)
        pos += 4
        if tok == 1:
            end = blob.index(b"\0", pos)
            name = blob[pos:end].decode("ascii", "replace")
            pos = (end + 4) & ~3
            if node is None:
                node = root
            else:
                child = {"name": name, "props": {}, "children": []}
                node["children"].append(child)
                stack.append(node)
                node = child
            path.append(name)
            node["path"] = "/" + "/".join(p for p in path if p)
        elif tok == 2:
            path.pop()
            node = stack.pop() if stack else node
        elif tok == 3:
            length, nameoff = struct.unpack_from(">II", blob, pos)
            pos += 8
            pname = strings[nameoff:strings.index(b"\0", nameoff)].decode()
            node["props"][pname] = blob[pos:pos + length]
            pos = (pos + length + 3) & ~3
        elif tok == 4:
            continue
        elif tok == 9:
            return root
        else:
            raise ValueError("bad FDT token %d" % tok)


def fdt_walk(node):
    yield node
    for c in node["children"]:
        yield from fdt_walk(c)


def u32s(v):
    return list(struct.unpack(">%dI" % (len(v) // 4), v))


def strs(v):
    return v.rstrip(b"\0").decode("ascii", "replace").split("\0")


class StockDtb:
    def __init__(self, stock_dir, name):
        self.name = name
        blob = open(os.path.join(stock_dir, name), "rb").read()
        self.sha256 = hashlib.sha256(blob).hexdigest()
        self.root = fdt_parse(blob)
        self.by_path = {n["path"]: n for n in fdt_walk(self.root)}
        self.by_phandle = {}
        for n in fdt_walk(self.root):
            if "phandle" in n["props"]:
                self.by_phandle[u32s(n["props"]["phandle"])[0]] = n
        img, idx = name.split(".dtb-")
        self.image, self.index = img, int(idx)

    def node(self, name):
        hits = [n for n in fdt_walk(self.root) if n["name"] == name]
        return hits[0] if hits else None

    def node_prefix(self, prefix):
        hits = [n for n in fdt_walk(self.root) if n["name"].startswith(prefix)]
        return hits[0] if hits else None

    def ref(self, node, prop=None):
        r = {"artifact": "artifacts/stock/audit/" + self.name, "sha256": self.sha256,
             "image": self.image, "dtb_index": self.index, "node": node["path"]}
        if prop:
            r["property"] = prop
        return r


# --------------------------------------------------------------------------
# DTSI property extraction (only the literal forms used by the panel files)

def dtsi_node_body(lines, node_name):
    """Return [(lineno, text)] for the body of the node whose header names node_name."""
    start = None
    for i, l in enumerate(lines):
        if re.search(r"\b" + re.escape(node_name) + r"\s*\{", l):
            start = i
            break
    if start is None:
        raise LookupError(node_name)
    depth, body = 0, []
    for i in range(start, len(lines)):
        l = re.sub(r"//.*", "", lines[i])
        depth += l.count("{") - l.count("}")
        body.append((i + 1, lines[i]))
        if depth == 0 and i > start:
            break
    return body


def dtsi_props(body):
    """Map property -> {line, line_end, raw, tokens:[(line, token)]} for depth-1 props."""
    props, cur, depth = {}, None, 0
    for lineno, raw in body[1:-1]:
        text = re.sub(r"//.*", "", raw)
        if cur is None:
            if depth == 0:
                m = re.match(r"\s*([#\w,.\-]+)\s*(=\s*(.*?))?\s*(;)?\s*$", text)
                if m and m.group(1) and "{" not in text:
                    name = m.group(1)
                    cur = {"line": lineno, "raw": text.strip(), "lines": [(lineno, m.group(3) or "")]}
                    if m.group(2) is None or text.rstrip().endswith(";"):
                        cur["line_end"] = lineno
                        props[name] = cur
                        cur = None
                    else:
                        cur["name"] = name
            depth += text.count("{") - text.count("}")
        else:
            cur["lines"].append((lineno, text))
            cur["raw"] += "\n" + text.strip()
            if text.rstrip().endswith(";"):
                cur["line_end"] = lineno
                props[cur.pop("name")] = cur
                cur = None
    return props


def dtsi_value_bytes(prop):
    """Encode a literal DTS value to the bytes dtc would emit; None for phandle refs."""
    text = " ".join(t for _, t in prop["lines"]).strip().rstrip(";").strip()
    if text == "":
        return b""
    if "&" in text:
        return None
    out = b""
    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"|<([^>]*)>|\[([^\]]*)\]', text):
        if m.group(1) is not None:
            out += m.group(1).encode() + b"\0"
        elif m.group(2) is not None:
            for cell in m.group(2).split():
                out += struct.pack(">I", int(cell, 0) & 0xFFFFFFFF)
        else:
            out += bytes(int(t, 16) for t in m.group(3).split())
    return out


def stream_tokens(prop):
    """[(source_line, byte)] for a bracketed byte-array property."""
    toks, inside = [], False
    for lineno, text in prop["lines"]:
        for ch_tok in re.finditer(r"\[|\]|[0-9A-Fa-f]{2}\b|\S+", text):
            t = ch_tok.group(0)
            if t == "[":
                inside = True
            elif t == "]":
                inside = False
            elif inside:
                if not re.fullmatch(r"[0-9A-Fa-f]{2}", t):
                    raise ValueError("malformed byte token %r at line %d" % (t, lineno))
                toks.append((lineno, int(t, 16)))
    return toks


# --------------------------------------------------------------------------
# packet decoding (layout proven by struct dsi_ctrl_hdr, mdss_dsi_cmd.h:84-91,
# and mdss_dsi_parse_dcs_cmds, mdss_dsi_panel.c:1098-1184)

HDR = 7


def decode_stream(toks):
    data = bytes(b for _, b in toks)
    packets, anomalies, off, batch, batch_start = [], [], 0, 0, 0
    batches = []
    while len(data) - off >= HDR:
        dtype, last, vc, ack, wait = data[off:off + 5]
        dlen = (data[off + 5] << 8) | data[off + 6]
        if dlen > len(data) - off - HDR:
            anomalies.append({"offset": off, "issue": "payload length exceeds remaining bytes"})
            break
        payload = data[off + HDR: off + HDR + dlen]
        name, family, size, nparams = DTYPES.get(dtype, ("UNKNOWN", "unknown", "unknown", None))
        p = {
            "index": len(packets), "byte_offset": off, "source_line": toks[off][0],
            "header_hex": data[off:off + HDR].hex(" "),
            "dtype": dtype, "dtype_hex": "0x%02x" % dtype, "dtype_name": name,
            "class": family, "packet_size": size,
            "last": last, "vc": vc, "ack": ack, "wait_ms": wait, "dlen": dlen,
            "payload_hex": payload.hex(" "), "batch": batch,
        }
        notes = []
        if family == "dcs" and payload:
            p["dcs_opcode"] = "0x%02x" % payload[0]
            p["dcs_name"] = DCS.get(payload[0], "vendor/unknown DCS opcode")
            if dtype == 0x05:
                p["transmitted_on_wire"] = "short packet 0x05, data0=0x%02x, data1=0x00" % payload[0]
                if dlen != 1:
                    notes.append("dlen=%d but DTYPE_DCS_WRITE transmits only payload[0]; "
                                 "data1 forced to 0 (mdss_dsi_cmd.c:293-297); "
                                 "payload[1:]=%s is not sent" % (dlen, payload[1:].hex(" ")))
            elif dtype == 0x15:
                p["transmitted_on_wire"] = "short packet 0x15, data0=0x%02x, data1=0x%02x" % (payload[0], payload[1])
        if family == "generic":
            p["transmitted_on_wire"] = ("long packet 0x29, word count %d, payload padded with 0xff "
                                        "to a 4-byte multiple in the host DMA buffer only "
                                        "(mdss_dsi_cmd.c:105-118)" % dlen)
            if payload[:1] in (b"\x2a", b"\x2b"):
                notes.append("payload starts with DCS opcode 0x%02x but is sent as GENERIC long "
                             "write 0x29, not DCS long write 0x39" % payload[0])
            if dlen <= 2:
                notes.append("mainline mipi_dsi_generic_write() would send %d-byte payload as "
                             "short packet 0x%02x, not long 0x29 (drm_mipi_dsi.c:744-770)"
                             % (dlen, {0: 0x03, 1: 0x13, 2: 0x23}[dlen]))
        if wait and not last:
            notes.append("wait=%d ms on a last=0 packet is ignored by mdss_dsi_cmds2buf_tx "
                         "(mdss_dsi_host.c:1675-1695)" % wait)
        if notes:
            p["notes"] = notes
        packets.append(p)
        off += HDR + dlen
        if last:
            batches.append({"batch": batch, "packets": [batch_start, len(packets) - 1],
                            "wait_after_ms": wait,
                            "wait_applied": ("always" if wait > VSYNC_PERIOD_MS else
                                             "only when video engine was idle (wait <= VSYNC_PERIOD 17)"
                                             if wait else "no wait")})
            batch += 1
            batch_start = len(packets)
    if off != len(data):
        anomalies.append({"offset": off, "issue": "%d trailing bytes do not form a packet header"
                          % (len(data) - off)})
    if packets and not packets[-1]["last"]:
        anomalies.append({"packet": packets[-1]["index"],
                          "issue": "stream ends with last=0; trailing batch would never be "
                                   "transmitted by mdss_dsi_cmds2buf_tx"})
    return data, packets, batches, anomalies


def rebuild(packets):
    out = bytearray()
    for p in packets:
        payload = bytes.fromhex(p["payload_hex"])
        out += bytes([p["dtype"], p["last"], p["vc"], p["ack"], p["wait_ms"]])
        out += struct.pack(">H", p["dlen"]) + payload
    return bytes(out)


# --------------------------------------------------------------------------

def fact(value, status, *refs, note=None):
    f = {"value": value, "status": status, "evidence": [r for r in refs if r]}
    if note:
        f["note"] = note
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kernel-src", required=True)
    ap.add_argument("--device-src", required=True)
    ap.add_argument("--common-src", required=True)
    ap.add_argument("--mainline-src", required=True)
    ap.add_argument("--stock-dir", required=True)
    ap.add_argument("--out", default=HERE)
    a = ap.parse_args()

    k = Repo("kernel", a.kernel_src)
    dev = Repo("device", a.device_src)
    com = Repo("common", a.common_src)
    ml = Repo("mainline", a.mainline_src)
    dtbs = [StockDtb(a.stock_dir, n) for n in LITHIUM_DTBS]
    for d in dtbs:
        bid = u32s(d.root["props"]["qcom,board-id"])
        if bid != [38, 0]:
            sys.exit("%s is not a lithium DTB (board-id %s)" % (d.name, bid))

    panels = {}
    for vid, v in VARIANTS.items():
        body = dtsi_node_body(k.lines(v["file"]), v["node"])
        props = dtsi_props(body)
        node_line = body[0][0]
        # Property-by-property comparison against every lithium stock DTB.
        comparison = []
        stock_nodes = {d.name: d.node(v["node"]) for d in dtbs}
        for pname, pr in props.items():
            src = dtsi_value_bytes(pr)
            row = {"property": pname, "source_line": pr["line"]}
            for d in dtbs:
                sn = stock_nodes[d.name]
                if sn is None or pname not in sn["props"]:
                    row[d.name] = "missing_in_stock"
                elif src is None:
                    row[d.name] = "phandle_reference_not_compared"
                else:
                    row[d.name] = "identical" if sn["props"][pname] == src else "different"
            comparison.append(row)
        stock_only = sorted({p for d in dtbs if stock_nodes[d.name]
                             for p in stock_nodes[d.name]["props"]} - set(props) - {"phandle", "linux,phandle"})

        streams = {}
        for sid, key, state_key in STREAMS:
            pr = props[key]
            toks = stream_tokens(pr)
            data, packets, batches, anomalies = decode_stream(toks)
            assert rebuild(packets) == data
            stock = {}
            for d in dtbs:
                sv = stock_nodes[d.name]["props"].get(key)
                stock[d.name] = {"dtb_sha256": d.sha256,
                                 "identical_to_source": sv == data,
                                 "property_sha256": hashlib.sha256(sv).hexdigest() if sv else None}
            state = strs(dtsi_value_bytes(props[state_key]))[0]
            streams[sid] = {
                "property": key,
                "source": {"repository": k.url, "commit": k.commit, "path": v["file"],
                           "line": pr["line"], "line_end": pr["line_end"]},
                "command_state": {"value": state, "property": state_key,
                                  "line": props[state_key]["line"],
                                  "meaning": "CMD_REQ_LP_MODE" if state == "dsi_lp_mode" else "CMD_REQ_HS_MODE",
                                  "parser": k.ref_(MDSS + "mdss_dsi_panel.c", "Set default link state to LP Mode"),
                                  "consumer": k.ref_(MDSS + "mdss_dsi_panel.c", "if (pcmds->link_state == DSI_LP_MODE)")},
                "byte_length": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "original_hex": data.hex(" "),
                "packet_count": len(packets),
                "batch_count": len(batches),
                "stock_dtb_corroboration": stock,
                "packets": packets,
                "batches": batches,
                "anomalies": anomalies,
            }
        not_decoded = []
        for pname, pr in props.items():
            if pname.endswith("-command") and pname not in [s[1] for s in STREAMS]:
                b = dtsi_value_bytes(pr)
                not_decoded.append({"property": pname, "line": pr["line"], "byte_length": len(b),
                                    "sha256": hashlib.sha256(b).hexdigest()})
        panels[vid] = {
            "schema_version": 1,
            "variant": vid,
            "downstream_node": v["node"],
            "downstream_label": v["label"],
            "panel_name": strs(dtsi_value_bytes(props["qcom,mdss-dsi-panel-name"]))[0],
            "source": {"repository": k.url, "commit": k.commit, "path": v["file"], "node_line": node_line},
            "stock_dtbs": [{"artifact": "artifacts/stock/audit/" + d.name, "sha256": d.sha256,
                            "node_present": stock_nodes[d.name] is not None} for d in dtbs],
            "encoding": {
                "header_bytes": HDR,
                "fields": ["dtype u8", "last u8", "vc u8", "ack u8", "wait u8 (ms)", "dlen u16 big-endian"],
                "struct": k.ref_(MDSS + "mdss_dsi_cmd.h", "struct dsi_ctrl_hdr {", end="} __packed;"),
                "parser": k.ref_(MDSS + "mdss_dsi_panel.c", "static int mdss_dsi_parse_dcs_cmds(",
                                 end="exit_free:"),
                "dlen_byteorder": k.ref_(MDSS + "mdss_dsi_panel.c", "dchdr->dlen = ntohs(dchdr->dlen);"),
                "batching": k.ref_(MDSS + "mdss_dsi_host.c", "static int mdss_dsi_cmds2buf_tx(",
                                   end="return tot;"),
                "dtype_table": k.ref_(MDSS + "mdss_dsi_cmd.h", "#define DTYPE_DCS_WRITE\t", end="#define DTYPE_PERIPHERAL_ON"),
                "round_trip": "dtype,last,vc,ack,wait_ms,dlen>>8,dlen&0xff,payload... concatenated over packets",
            },
            "streams": streams,
            "other_command_properties_not_decoded": not_decoded,
            "property_comparison_vs_stock": comparison,
            "stock_only_properties": stock_only,
        }

    for vid, pj in panels.items():
        with open(os.path.join(a.out, VARIANTS[vid]["out"]), "w") as f:
            json.dump(pj, f, indent=2)
            f.write("\n")

    with open(os.path.join(a.stock_dir, "emmc_appsboot.mbn"), "rb") as f:
        aboot_sha256 = hashlib.sha256(f.read()).hexdigest()
    ev = build_evidence(k, dev, com, ml, dtbs, panels, aboot_sha256)
    with open(os.path.join(a.out, "display-evidence.json"), "w") as f:
        json.dump(ev, f, indent=2)
        f.write("\n")
    print("wrote", ", ".join([v["out"] for v in VARIANTS.values()] + ["display-evidence.json"]))


def build_evidence(k, dev, com, ml, dtbs, panels, aboot_sha256):
    d5 = dtbs[1]  # boot.img.dtb-5: MSM8996 Pro, the live SoC
    sh, au = VARIANTS["sharp"]["file"], VARIANTS["auo"]["file"]
    shn, aun = VARIANTS["sharp"]["node"], VARIANTS["auo"]["node"]
    common = QCOM + "msm8996-xiaomi-common.dtsi"
    a8 = QCOM + "a8-msm8996-mtp.dtsi"
    panels_x = QCOM + "msm8996-mdss-panels-xiaomi.dtsi"
    mdss = QCOM + "msm8996-mdss.dtsi"
    soc = QCOM + "msm8996.dtsi"
    pinc = QCOM + "msm8996-pinctrl.dtsi"
    pmi = QCOM + "msm-pmi8994.dtsi"
    pmi96 = QCOM + "msm-pmi8996.dtsi"
    reg = QCOM + "msm8996-regulator.dtsi"

    def dref(d, nodename, prop=None, prefix=False):
        n = d.node_prefix(nodename) if prefix else d.node(nodename)
        return d.ref(n, prop) if n else None

    def both(path, prop, after_key):
        """same property in both panel files"""
        return [k.ref_(path, prop, after=after_key)]

    def pv(prop, conv=lambda b: u32s(b)[0], file=sh, node=shn):
        body = dtsi_node_body(k.lines(file), node)
        return conv(dtsi_value_bytes(dtsi_props(body)[prop]))

    def panel_fact(prop, conv=lambda b: u32s(b)[0], status="source_evidence", note=None):
        vals = {}
        refs = []
        for vid, f, n in (("sharp", sh, shn), ("auo", au, aun)):
            vals[vid] = pv(prop, conv, f, n)
            refs.append(k.ref_(f, prop + " ", after=n) if (prop + " ") in "\n".join(k.lines(f))
                        else k.ref_(f, prop, after=n))
            for d in dtbs:
                refs.append(dref(d, n, prop))
        same = vals["sharp"] == vals["auo"]
        return fact(vals["sharp"] if same else vals, status, *refs,
                    note=(note or "") + ("" if same else " Values differ per variant."))

    # Overlap check for the splash reservation against every stock reserved-memory node.
    rm = d5.by_path["/reserved-memory"]
    regions = []
    for c in rm["children"]:
        if "reg" in c["props"]:
            cells = u32s(c["props"]["reg"])
            base, size = (cells[0] << 32) | cells[1], (cells[2] << 32) | cells[3]
            regions.append({"node": c["path"], "base": hex(base), "size": hex(size),
                            "end_exclusive": hex(base + size)})
    sp = next(r for r in regions if "cont_splash_mem@" in r["node"])
    sb, se = int(sp["base"], 16), int(sp["end_exclusive"], 16)
    overlaps = [r["node"] for r in regions if r is not sp
                and int(r["base"], 16) < se and sb < int(r["end_exclusive"], 16)]
    adjacent = [r["node"] for r in regions if r is not sp
                and (int(r["end_exclusive"], 16) == sb or int(r["base"], 16) == se)]

    dsi0 = d5.node_prefix("qcom,mdss_dsi_ctrl0")

    def gpio(prop):
        c = u32s(dsi0["props"][prop])
        return {"controller": d5.by_phandle[c[0]]["path"], "gpio": c[1], "flags": c[2]}

    vddr = d5.by_phandle[u32s(dsi0["props"]["vddr-supply"])[0]]
    wled = d5.node_prefix("qcom,leds@d800")

    hfp, hbp, hpw = pv("qcom,mdss-dsi-h-front-porch"), pv("qcom,mdss-dsi-h-back-porch"), pv("qcom,mdss-dsi-h-pulse-width")
    vfp, vbp, vpw = pv("qcom,mdss-dsi-v-front-porch"), pv("qcom,mdss-dsi-v-back-porch"), pv("qcom,mdss-dsi-v-pulse-width")
    w, h, fps = pv("qcom,mdss-dsi-panel-width"), pv("qcom,mdss-dsi-panel-height"), pv("qcom,mdss-dsi-panel-framerate")
    htot, vtot = w + hfp + hbp + hpw, h + vfp + vbp + vpw
    pclk = htot * vtot * fps

    s = lambda b: strs(b)[0]
    flag = lambda b: True

    ev = {
        "schema_version": 1,
        "generated_by": "research/delegated/display-audit/extract_evidence.py",
        "scope": "Read-only clean-room display evidence audit for xiaomi-lithium (Mi MIX). "
                 "No hardware validation.",
        "status_vocabulary": ["observed", "source_evidence", "inferred", "conflicting", "unknown"],
        "inputs": {
            "repositories": [{"id": r.id, "url": r.url, "ref": r.ref, "commit": r.commit}
                             for r in (k, dev, com, ml)],
            "stock_dtbs": [{"artifact": "artifacts/stock/audit/" + d.name, "sha256": d.sha256,
                            "board_id": u32s(d.root["props"]["qcom,board-id"]),
                            "msm_id": u32s(d.root["props"]["qcom,msm-id"]),
                            "model": s(d.root["props"]["model"])} for d in dtbs],
            "stock_aboot": {"artifact": "artifacts/stock/audit/emmc_appsboot.mbn",
                            "sha256": aboot_sha256},
            "live_observation": {"path": "research/hardware-map.json",
                                 "key": "live_observations.selected_panel"},
        },
        "panel_selection": {
            "installed_variant_on_audited_unit": fact(
                "qcom,mdss_dsi_sharp_fte716_1080p_video", "observed",
                {"path": "research/hardware-map.json", "key": "live_observations.selected_panel",
                 "source": "/proc/device-tree/chosen/bootargs (stock Android, read-only)"},
                note="Observed on one unit only. Other lithium units may carry the AUO panel."),
            "mechanism": fact(
                "Bootloader detects the panel and passes mdss_mdp.panel=<lk_cfg>:dsi:0:<node-name>; "
                "the kernel matches the DT node name. qcom,mdss-dsi-panel-id is not parsed by the "
                "downstream MDSS driver.", "source_evidence",
                k.ref_(MDSS + "mdss_dsi.c", "static struct device_node *mdss_dsi_find_panel_of_node("),
                k.ref_(MDSS + "mdss_mdp.c", "module_param_string(panel, mdss_mdp_panel"),
                {"artifact": "artifacts/stock/audit/emmc_appsboot.mbn", "string_offsets": {
                    "0x79fc0": " mdss_mdp.panel=",
                    "0x7a600": "lcd 3state id = %d",
                    "0x7a6e4": "Sharp/Fte716 FHD panel detected",
                    "0x7a708": "AUO/Fte716 FHD panel detected",
                    "0x7a728": "Defalut Sharp/Fte716 FHD panel",
                    "0x7a88c": "qcom,mdss_dsi_sharp_fte716_1080p_video",
                    "0x7a8b4": "qcom,mdss_dsi_auo_fte716_1080p_video",
                    "0x82c78": "DEBUG: panel ID is 0x%x",
                    "0x82cac": "Panel ID read error"}}),
            "bootloader_detection_input": fact(
                None, "unknown",
                {"artifact": "artifacts/stock/audit/emmc_appsboot.mbn", "string_offset": "0x7a600"},
                note="The 'lcd 3state id' string suggests a tri-state GPIO ID read with Sharp as "
                     "the default fallback (inferred). The GPIO number and the ID-to-variant table "
                     "were not recovered; aboot was not disassembled."),
            "dt_default_panel": fact(
                "dsi_lgd_sw43101_fhd_video", "source_evidence",
                k.ref_(a8, "qcom,dsi-pref-prim-pan"),
                d5.ref(dsi0, "qcom,dsi-pref-prim-pan"),
                note="A8 DT default is an LG SW43101 panel, overridden at runtime by the "
                     "bootloader command line. The DT default does NOT identify the lithium panel."),
            "downstream_panel_id_property": panel_fact(
                "qcom,mdss-dsi-panel-id",
                note="Informational only; no reader in drivers/video/msm/mdss at the pinned commit."),
        },
        "variants": {},
        "board_wiring": {
            "dsi_controller": fact("mdss_dsi0 (DSI0, 0x994000), hw-config single_dsi", "source_evidence",
                                   k.ref_(mdss, "mdss_dsi0: qcom,mdss_dsi_ctrl0@994000"),
                                   k.ref_(a8, 'hw-config = "single_dsi"'), d5.ref(dsi0)),
            "reset_gpio": fact(gpio("qcom,platform-reset-gpio"), "source_evidence",
                               k.ref_(a8, "qcom,platform-reset-gpio", after="&mdss_dsi0 {"),
                               *[dref(d, "qcom,mdss_dsi_ctrl0", "qcom,platform-reset-gpio", True) for d in dtbs],
                               note="TLMM gpio8. Polarity is not encoded (flags 0); the downstream "
                                    "driver drives the raw level from qcom,mdss-dsi-reset-sequence."),
            "enable_gpio": fact(gpio("qcom,platform-enable-gpio"), "source_evidence",
                                k.ref_(a8, "qcom,platform-enable-gpio", after="&mdss_dsi0 {"),
                                *[dref(d, "qcom,mdss_dsi_ctrl0", "qcom,platform-enable-gpio", True) for d in dtbs],
                                note="TLMM gpio47 (disp_en_gpio): driven high before reset, low on off. "
                                     "Its electrical function (bias enable vs. other) is not documented."),
            "backlight_enable_gpio": fact(gpio("qcom,platform-bklight-en-gpio"), "source_evidence",
                                          k.ref_(a8, "qcom,platform-bklight-en-gpio", after="&mdss_dsi0 {"),
                                          *[dref(d, "qcom,mdss_dsi_ctrl0", "qcom,platform-bklight-en-gpio", True) for d in dtbs],
                                          note="TLMM gpio48: driven high after the reset sequence, low on off."),
            "te_gpio": fact(gpio("qcom,platform-te-gpio"), "source_evidence",
                            k.ref_(a8, "qcom,platform-te-gpio", after="&mdss_dsi0 {"),
                            k.ref_(pinc, "mdss_te_active: mdss_te_active"),
                            *[dref(d, "qcom,mdss_dsi_ctrl0", "qcom,platform-te-gpio", True) for d in dtbs],
                            note="TLMM gpio10, function mdp_vsync, 2 mA, pull-down."),
            "reset_pinctrl": fact({"pin": "gpio8", "active": "gpio, 8 mA, bias-disable",
                                   "sleep": "gpio, 2 mA, pull-down"}, "source_evidence",
                                  k.ref_(pinc, "mdss_dsi_active: mdss_dsi_active"),
                                  k.ref_(pinc, "mdss_dsi_suspend: mdss_dsi_suspend"),
                                  dref(d5, "mdss_dsi_active")),
            "vddr_gpio_regulator": fact(
                {"regulator": "disp_vddr_vreg (regulator-fixed)", "gpio": "TLMM gpio40",
                 "enable_active_high": True, "regulator_boot_on": True, "startup_delay_us": 4000,
                 "pinctrl_active": "gpio40 output-high, 8 mA, bias-disable",
                 "pinctrl_sleep": "gpio40 2 mA, pull-down"},
                "source_evidence",
                k.ref_(common, "disp_vddr_vreg: disp_vddr_vreg1_6"),
                k.ref_(common, "mdss_vddr_active: mdss_vddr_active"),
                k.ref_(a8, "pinctrl-0 = <&mdss_dsi_active &mdss_te_active &mdss_vddr_active>;"),
                d5.ref(vddr), d5.ref(dsi0, "vddr-supply"),
                note="Name implies a 1.6 V 'VDDR' rail (node name disp_vddr_vreg1_6); the voltage "
                     "is not stated in DT (inferred). The FTE716 panel supply list does not "
                     "reference it; it is held on through pinctrl output-high."),
            "vddr_supply_on_dsi_ctrl": fact(
                "vddr-supply = <&disp_vddr_vreg> on mdss_dsi_ctrl0", "conflicting",
                d5.ref(dsi0, "vddr-supply"),
                {"repository": k.url, "commit": k.commit, "path": a8,
                 "note": "no vddr-supply in a8-msm8996-mtp.dtsi, msm8996-xiaomi-common.dtsi or "
                         "msm8996-mdss.dtsi at the pinned commit"},
                note="Present in all four stock lithium DTBs, absent from the pinned LineageOS "
                     "source: the LineageOS tree is not byte-identical to the stock build."),
            "panel_supplies": fact([
                {"name": "vddio", "regulator": "pm8994_l14", "min_uv": 1800000, "max_uv": 1800000,
                 "enable_load_ua": 62000, "disable_load_ua": 80, "post_on_sleep_ms": 1, "pre_off_sleep_ms": 10},
                {"name": "lab", "regulator": "PMI8994 LAB (lab_regulator @0xde00)", "min_uv": 4600000,
                 "max_uv": 6000000, "enable_load_ua": 100000, "disable_load_ua": 100},
                {"name": "ibb", "regulator": "PMI8994 IBB (ibb_regulator @0xdc00)", "min_uv": 4600000,
                 "max_uv": 6000000, "enable_load_ua": 100000, "disable_load_ua": 100,
                 "post_on_sleep_ms": 10, "pre_off_sleep_ms": 5}], "source_evidence",
                k.ref_(panels_x, "dsi_panel_pwr_supply: dsi_panel_pwr_supply", end="dsi_panel_pwr_supply_amoled"),
                k.ref_(mdss, "vddio-supply = <&pm8994_l14>;"),
                k.ref_(mdss, "lab-supply = <&lab_regulator>;"),
                k.ref_(mdss, "ibb-supply = <&ibb_regulator>;"),
                k.ref_(reg, "pm8994_l14: regulator-l14"),
                dref(d5, "dsi_panel_pwr_supply"),
                note="Enabled in list order vddio, lab, ibb; disabled in reverse "
                     "(mdss_io_util.c msm_dss_enable_vreg). LAB/IBB are +/- rails; IBB is "
                     "negative, the DT expresses magnitudes (inferred from qpnp-labibb naming)."),
            "labibb_mode_and_init": fact(
                {"mode": "lcd", "lab_init_lcd_uv": 5500000, "ibb_init_lcd_uv": 5500000,
                 "lab_soft_start_stock": 400, "ibb_discharge_resistor_stock": 300,
                 "ibb_lab_pwrup_delay_us": 8000, "ibb_lab_pwrdn_delay_us": 8000},
                "source_evidence",
                k.ref_(common, 'qpnp,qpnp-labibb-mode = "lcd";'),
                k.ref_(pmi, "qcom,qpnp-lab-init-lcd-voltage"),
                k.ref_(pmi, "qcom,qpnp-ibb-init-lcd-voltage"),
                k.ref_(common, "qcom,qpnp-lab-soft-start = <400>;"),
                k.ref_(pmi96, "qcom,qpnp-ibb-discharge-resistor = <300>;"),
                dref(d5, "qcom,lab@de00", prefix=True), dref(d5, "qcom,ibb@dc00", prefix=True)),
            "touch_controller_coupling": fact(
                {"compatible": "ft,ft5x46_i2c", "i2c_addr": "0x38", "reset_gpio": "TLMM 89",
                 "irq_gpio": "TLMM 125", "supplies": ["pm8994_l14 (vdd, vddio)", "lab", "ibb"],
                 "auo_lcd_vendor_id": "0x34", "sharp_lcd_vendor_id": "0x33",
                 "panel_reset_skip_hook_used": False},
                "source_evidence",
                k.ref_(a8, "ft5x46_i2c@38 {"),
                k.ref_(a8, 'fw-name = "fte8716_auo_incell_biel_a8.fw";'),
                k.ref_(a8, 'fw-name = "fte8716_sharp_incell_biel_a8.fw";'),
                k.ref_(MDSS + "mdss_dsi_panel.c", "if (mdss_panel_reset_skip && !pinfo->panel_dead)"),
                note="In-cell touch shares LAB/IBB with the panel. mdss_panel_reset_skip_enable() "
                     "is only called by Synaptics drivers, not ft5x46, so the LCD reset (gpio8) is "
                     "owned by the display driver on lithium."),
        },
        "backlight": {
            "controller": fact("PMI8994 WLED (qcom,qpnp-wled @0xd800), bl_ctrl_wled", "source_evidence",
                               k.ref_(pmi, "pmi8994_wled: qcom,leds@d800"),
                               *both(sh, "qcom,mdss-dsi-bl-pmic-control-type", shn),
                               *both(au, "qcom,mdss-dsi-bl-pmic-control-type", aun),
                               d5.ref(wled)),
            "level_range": panel_fact("qcom,mdss-dsi-bl-max-level",
                                      note="bl-min-level 1, bl-max-level 4095, brightness-max-level 4095 "
                                           "in both variants."),
            "wled_parameters_stock": fact(
                {"ovp_mv": u32s(wled["props"]["qcom,ovp-mv"])[0],
                 "fs_curr_ua": u32s(wled["props"]["qcom,fs-curr-ua"])[0],
                 "switch_freq_khz": u32s(wled["props"]["qcom,switch-freq-khz"])[0],
                 "ilim_ma": u32s(wled["props"]["qcom,ilim-ma"])[0],
                 "led_strings": list(wled["props"]["qcom,led-strings-list"]),
                 "en_cabc": "qcom,en-cabc" in wled["props"],
                 "en_phase_stag": "qcom,en-phase-stag" in wled["props"],
                 "dim_mode": s(wled["props"]["qcom,dim-mode"]),
                 "hyb_thres": u32s(wled["props"]["qcom,hyb-thres"])[0]},
                "observed",
                d5.ref(wled), k.ref_(a8, "qcom,ovp-mv = <31000>;"),
                k.ref_(common, "&pmi8994_wled {", end="qcom,led-strings-list = [00 01];"),
                note="Values read from the stock DTB. Source agrees except qcom,en-phase-stag, which "
                     "msm8996-xiaomi-common.dtsi sets and the stock DTB lacks (conflicting)."),
            "panel_side_brightness": fact(
                "On-commands send DCS 0x51 0xFF and 0x53 0x24 (BCTRL|BL on); brightness itself is "
                "WLED-controlled. The CABC hook writes DCS 0x55.", "inferred",
                k.ref_(sh, "15 00 00 00 00 00 02 51 FF", after=shn),
                k.ref_(au, "15 00 00 00 00 00 02 51 FF", after=aun)),
            "android_sysfs": fact("/sys/class/leds/lcd-backlight/{brightness,max_brightness}", "source_evidence",
                                  com.ref_("light/service.cpp", "kLcdBacklightPath")),
        },
        "power_sequence_downstream": fact([
            "1. msm_dss_enable_vreg: vddio (L14 1.8 V) on, sleep 1 ms; lab on; ibb on, sleep 10 ms",
            "2. DSI link clocks on, controller sw reset; lanes at LP-11 (qcom,mdss-dsi-lp11-init)",
            "3. pinctrl mdss_default (gpio8 out, gpio10 mdp_vsync, gpio40 output-high)",
            "4. gpio47 (enable) high, wait 100-110 us",
            "5. reset gpio8: high 10 ms, low 1 ms, high 10 ms (qcom,mdss-dsi-reset-sequence <1 10>,<0 1>,<1 10>)",
            "6. gpio48 (backlight enable) high",
            "7. send qcom,mdss-dsi-on-command in LP mode (dsi_lp_mode), batched by last flag",
            "8. start video; WLED backlight set via bl_ctrl_wled",
            "OFF: qcom,mdss-dsi-off-command in HS mode; gpio48 low; gpio47 low, 100 us; gpio8 low; "
            "pinctrl sleep; ibb off (5 ms pre), lab off, vddio off (10 ms pre)",
            "With continuous splash active at first boot, steps 4-6 are skipped (panel already on)."],
            "source_evidence",
            k.ref_(MDSS + "mdss_dsi.c", "static int mdss_dsi_panel_power_on("),
            k.ref_(MDSS + "mdss_dsi.c", "static int mdss_dsi_panel_power_off("),
            k.ref_(MDSS + "mdss_dsi.c", "* Issue hardware reset line after enabling the DSI clocks and data"),
            k.ref_(MDSS + "mdss_dsi_panel.c", "int mdss_dsi_panel_reset(struct mdss_panel_data *pdata, int enable)"),
            k.ref_(MDSS + "mdss_io_util.c", "int msm_dss_enable_vreg(struct dss_vreg *in_vreg, int num_vreg, int enable)"),
            note="Order derived from code paths, not from a captured trace. Not hardware validated."),
        "framebuffer": {
            "splash_reservation": fact({"base": sp["base"], "size": sp["size"], "end_exclusive": sp["end_exclusive"]},
                                       "observed",
                                       k.ref_(soc, "cont_splash_mem: cont_splash_mem@83401000"),
                                       *[dref(d, "cont_splash_mem@83401000") for d in dtbs],
                                       {"path": "research/hardware-map.json", "key": "reserved_memory[cont_splash_mem]",
                                        "status": "observed_live"},
                                       note="Fixed DT value in lithium's own stock DTBs and the live DT; "
                                            "not taken from scorpio."),
            "dfps_data_mem": fact({"base": "0x83400000", "size": "0x1000"}, "observed",
                                  k.ref_(soc, "dfps_data_mem: dfps_data_mem@83400000"),
                                  dref(d5, "dfps_data_mem@83400000")),
            "reservation_overlap_check": fact({"overlapping": overlaps, "adjacent": adjacent,
                                               "stock_reserved_regions": regions}, "observed",
                                              d5.ref(rm),
                                              note="Static regions in boot.img.dtb-5 only; dynamically "
                                                   "allocated carve-outs (adsp/qseecom/secure) have no fixed "
                                                   "reg and cannot be checked offline."),
            "kernel_consumer": fact(
                "Downstream reads only base/size of the reservation from DT via "
                "qcom,cont-splash-memory/linux,contiguous-region; scan-out stays as programmed by the "
                "bootloader in MDP registers.", "source_evidence",
                k.ref_(mdss, "mdss_fb0: qcom,mdss_fb_primary"),
                k.ref_(MDSS + "mdss_mdp_splash_logo.c", '"qcom,cont-splash-memory"'),
                d5.ref(d5.node("qcom,mdss_fb_primary"))),
            "cont_splash_enabled_flag": panel_fact("qcom,cont-splash-enabled", conv=lambda b: True),
            "scanout_base": fact(None, "unknown",
                                 {"artifact": "artifacts/stock/audit/emmc_appsboot.mbn", "sha256": aboot_sha256,
                                  "byte_offset": "0xa0514", "value_le32": "0x83400000"},
                                 k.ref_(MDSS + "mdss_mdp_splash_logo.c", "mdp5_mdata->splash_mem_addr = offsets[0];"),
                                 note="The reservation start is known; the address programmed into the MDP "
                                      "source pipe by aboot is not. aboot contains 0x83400000 as a 32-bit "
                                      "little-endian constant at 2 offsets (first 0xa0514) and no literal "
                                      "0x83401000; meaning not established."),
            "stride_bytes": fact(None, "unknown",
                                 k.ref_(MDSS + "mdss_mdp_splash_logo.c", '"qcom,cont-splash-memory"'),
                                 note="Runtime value in MDP SSPP registers; not in DT."),
            "pixel_format": fact(None, "unknown",
                                 k.ref_(sh, "qcom,mdss-dsi-bpp", after=shn), k.ref_(au, "qcom,mdss-dsi-bpp", after=aun),
                                 note="Panel bpp is 24 (RGB888 on the DSI link); framebuffer memory format "
                                      "(r8g8b8 vs x8r8g8b8 etc.) is set by aboot and unproven."),
            "dimensions": fact({"width": w, "height": h}, "inferred",
                               k.ref_(sh, "qcom,mdss-dsi-panel-width", after=shn),
                               k.ref_(sh, "qcom,mdss-dsi-panel-height", after=shn),
                               k.ref_(sh, "29 00 00 00 00 00 05 2A 00 00 04 37", after=shn),
                               k.ref_(sh, "29 00 00 00 00 00 05 2B 00 00 07 F7", after=shn),
                               note="Panel active area; framebuffer geometry assumed equal but not proven."),
            "size_bounds": fact({"rgb888_bytes": w * h * 3, "xrgb8888_bytes": w * h * 4,
                                 "reservation_bytes": int(sp["size"], 16)}, "inferred",
                                d5.ref(d5.by_path[sp["node"]], "reg"),
                                note="Either candidate format fits; this does not choose one."),
            "simple_framebuffer_recommendation": fact(
                "Do not add a simple-framebuffer node with guessed stride/format. Read MDP SSPP "
                "SRC0_ADDR/SRC_YSTRIDE0/SRC_FORMAT on stock (or let lk2nd report them) first.",
                "inferred",
                k.ref_(MDSS + "mdss_mdp_splash_logo.c", '"qcom,cont-splash-memory"'),
                ml.ref_("Documentation/devicetree/bindings/display/simple-framebuffer.yaml", "* `r8g8b8`")),
        },
        "mainline_api": {
            "kernel_tree": {"repository": ml.url, "commit": ml.commit},
            "struct_mipi_dsi_dcs_cmd": fact(False, "source_evidence",
                                            {"repository": ml.url, "commit": ml.commit,
                                             "path": "include/drm/drm_mipi_dsi.h",
                                             "note": "no match for 'mipi_dsi_dcs_cmd' in include/ or drivers/gpu/drm/"}),
            "multi_context": fact("struct mipi_dsi_multi_context", "source_evidence",
                                  ml.ref_("include/drm/drm_mipi_dsi.h", "struct mipi_dsi_multi_context {")),
            "generic_write_type_by_length": fact(
                {"0": "0x03", "1": "0x13", "2": "0x23", ">2": "0x29"}, "source_evidence",
                ml.ref_("drivers/gpu/drm/drm_mipi_dsi.c", "ssize_t mipi_dsi_generic_write(")),
            "dcs_write_type_by_length": fact(
                {"1": "0x05", "2": "0x15", ">2": "0x39"}, "source_evidence",
                ml.ref_("drivers/gpu/drm/drm_mipi_dsi.c", "ssize_t mipi_dsi_dcs_write_buffer(")),
            "device_transfer_is_static": fact(True, "source_evidence",
                                              ml.ref_("drivers/gpu/drm/drm_mipi_dsi.c",
                                                      "static ssize_t mipi_dsi_device_transfer(")),
            "seq_macros": fact(["mipi_dsi_generic_write_seq_multi", "mipi_dsi_dcs_write_seq_multi",
                                "mipi_dsi_msleep", "mipi_dsi_usleep_range"], "source_evidence",
                               ml.ref_("include/drm/drm_mipi_dsi.h", "#define mipi_dsi_generic_write_seq_multi("),
                               ml.ref_("include/drm/drm_mipi_dsi.h", "#define mipi_dsi_dcs_write_seq_multi("),
                               ml.ref_("include/drm/drm_mipi_dsi.h", "#define mipi_dsi_msleep(")),
            "lpm_flag": fact("MIPI_DSI_MODE_LPM", "source_evidence",
                             ml.ref_("include/drm/drm_mipi_dsi.h", "#define MIPI_DSI_MODE_LPM")),
            "existing_fte716_driver": fact(False, "source_evidence",
                                           {"repository": ml.url, "commit": ml.commit,
                                            "path": "drivers/gpu/drm/panel/",
                                            "note": "no fte716/ft8716 driver; nearest FocalTech TDDI is "
                                                    "panel-ebbg-ft8719.c (different panel)"}),
            "wled_binding": fact("qcom,pmi8994-wled", "source_evidence",
                                 ml.ref_("Documentation/devicetree/bindings/leds/backlight/qcom-wled.yaml",
                                         "qcom,pmi8994-wled")),
            "labibb_binding": fact("only qcom,pmi8998-lab-ibb", "source_evidence",
                                   ml.ref_("Documentation/devicetree/bindings/regulator/qcom-labibb-regulator.yaml",
                                           "const: qcom,pmi8998-lab-ibb"),
                                   note="No PMI8994/PMI8996 LAB/IBB compatible in the pinned tree."),
            "simple_framebuffer_binding": fact("simple-framebuffer formats include r8g8b8, x8r8g8b8, a8r8g8b8",
                                               "source_evidence",
                                               ml.ref_("Documentation/devicetree/bindings/display/simple-framebuffer.yaml",
                                                       "* `r8g8b8`")),
        },
        "unknowns": [
            "Scan-out base, stride and memory pixel format left by aboot",
            "Bootloader panel-ID GPIO and ID-to-variant mapping",
            "Electrical role of TLMM gpio47 and the disp_vddr rail voltage",
            "Whether 2-byte generic long writes (0x29) may be sent as generic short writes (0x23)",
            "Mainline LAB/IBB support for PMI8994/PMI8996",
            "Behaviour of the vendor register set (0x00 offset + FF 87 16 command-2 unlock) beyond the bytes",
            "Whether the stock kernel differs from LineageOS in panel code paths (DTB differences prove the trees differ)",
        ],
    }

    for vid, f, n in (("sharp", sh, shn), ("auo", au, aun)):
        p = panels[vid]
        def vp(prop, conv=lambda b: u32s(b)[0]):
            body = dtsi_node_body(k.lines(f), n)
            pr = dtsi_props(body)[prop]
            return conv(dtsi_value_bytes(pr)), {"repository": k.url, "commit": k.commit, "path": f, "line": pr["line"]}

        def F(prop, conv=lambda b: u32s(b)[0], status="source_evidence", note=None):
            val, r = vp(prop, conv)
            refs = [r] + [dref(d, n, prop) for d in dtbs]
            ident = all(row.get(dd.name) == "identical" for row in p["property_comparison_vs_stock"]
                        if row["property"] == prop for dd in dtbs)
            return fact(val, status if ident else "conflicting", *refs,
                        note=note if ident else (note or "") + " Stock DTB value differs from source.")

        pairs = lambda b: [list(x) for x in zip(u32s(b)[0::2], u32s(b)[1::2])]
        ev["variants"][vid] = {
            "downstream_node": n,
            "panel_name": F("qcom,mdss-dsi-panel-name", s),
            "panel_model": F("qcom,mdss-dsi-panel-model", s),
            "panel_id_property": F("qcom,mdss-dsi-panel-id"),
            "panel_type": F("qcom,mdss-dsi-panel-type", s),
            "resolution": {"width": F("qcom,mdss-dsi-panel-width"), "height": F("qcom,mdss-dsi-panel-height")},
            "physical_mm": {"width": F("qcom,mdss-pan-physical-width-dimension"),
                            "height": F("qcom,mdss-pan-physical-height-dimension")},
            "framerate_hz": F("qcom,mdss-dsi-panel-framerate"),
            "refresh_range_hz": {"min": F("qcom,mdss-dsi-min-refresh-rate"), "max": F("qcom,mdss-dsi-max-refresh-rate")},
            "bpp": F("qcom,mdss-dsi-bpp"),
            "virtual_channel": F("qcom,mdss-dsi-virtual-channel-id"),
            "stream": F("qcom,mdss-dsi-stream"),
            "lanes": fact(4, "source_evidence", *[vp(x, flag)[1] for x in (
                "qcom,mdss-dsi-lane-0-state", "qcom,mdss-dsi-lane-1-state",
                "qcom,mdss-dsi-lane-2-state", "qcom,mdss-dsi-lane-3-state")]),
            "traffic_mode": F("qcom,mdss-dsi-traffic-mode", s),
            "h_sync_pulse": F("qcom,mdss-dsi-h-sync-pulse"),
            "flags_boolean": fact(["lp11-init", "tx-eot-append", "bllp-power-mode", "bllp-eof-power-mode",
                                   "esd-check-enabled", "video-panel-esd-te-check", "cont-splash-enabled",
                                   "dispparam-enabled", "disp-paneloff-disablecabc-enabled"],
                                  "source_evidence", *[vp(x, flag)[1] for x in (
                                      "qcom,mdss-dsi-lp11-init", "qcom,mdss-dsi-tx-eot-append",
                                      "qcom,mdss-dsi-bllp-power-mode", "qcom,mdss-dsi-bllp-eof-power-mode")]),
            "timings": {
                "h_front_porch": F("qcom,mdss-dsi-h-front-porch"), "h_back_porch": F("qcom,mdss-dsi-h-back-porch"),
                "h_pulse_width": F("qcom,mdss-dsi-h-pulse-width"), "h_sync_skew": F("qcom,mdss-dsi-h-sync-skew"),
                "v_front_porch": F("qcom,mdss-dsi-v-front-porch"), "v_back_porch": F("qcom,mdss-dsi-v-back-porch"),
                "v_pulse_width": F("qcom,mdss-dsi-v-pulse-width"),
                "borders": fact(0, "source_evidence", vp("qcom,mdss-dsi-h-left-border")[1]),
                "derived": fact({"htotal": htot, "vtotal": vtot, "pixel_clock_hz_at_60": pclk,
                                 "drm_mode_clock_khz": round(pclk / 1000),
                                 "lane_bitrate_bps_4lanes_24bpp": pclk * 24 // 4}, "inferred",
                                *[vp(x)[1] for x in ("qcom,mdss-dsi-panel-width", "qcom,mdss-dsi-h-front-porch",
                                  "qcom,mdss-dsi-h-back-porch", "qcom,mdss-dsi-h-pulse-width",
                                  "qcom,mdss-dsi-panel-height", "qcom,mdss-dsi-v-front-porch",
                                  "qcom,mdss-dsi-v-back-porch", "qcom,mdss-dsi-v-pulse-width",
                                  "qcom,mdss-dsi-panel-framerate")],
                                note="Arithmetic from the timings; downstream adds no extra blanking here."),
                "phy_timings_v2": F("qcom,mdss-dsi-panel-timings-phy-v2", lambda b: b.hex(" ")),
                "phy_timings_legacy": F("qcom,mdss-dsi-panel-timings", lambda b: b.hex(" ")),
                "t_clk_post": F("qcom,mdss-dsi-t-clk-post"), "t_clk_pre": F("qcom,mdss-dsi-t-clk-pre"),
            },
            "reset_sequence": F("qcom,mdss-dsi-reset-sequence", pairs,
                                note="Pairs of <level ms>: high 10 ms, low 1 ms, high 10 ms."),
            "backlight": {"type": F("qcom,mdss-dsi-bl-pmic-control-type", s),
                          "min": F("qcom,mdss-dsi-bl-min-level"), "max": F("qcom,mdss-dsi-bl-max-level"),
                          "brightness_max": F("qcom,mdss-brightness-max-level")},
            "triggers": {"dma": F("qcom,mdss-dsi-dma-trigger", s), "mdp": F("qcom,mdss-dsi-mdp-trigger", s)},
            "esd": {"mode": F("qcom,mdss-dsi-panel-status-check-mode", s),
                    "status_read_command": fact(None, "source_evidence", vp("qcom,esd-check-enabled", flag)[1],
                                                note="No qcom,mdss-dsi-panel-status-command: ESD uses the TE "
                                                     "signal, not a register read.")},
            "command_states": {sid: fact(p["streams"][sid]["command_state"]["value"], "source_evidence",
                                         {"repository": k.url, "commit": k.commit, "path": f,
                                          "line": p["streams"][sid]["command_state"]["line"]})
                               for sid in p["streams"]},
            "commands": {sid: fact({"bytes": p["streams"][sid]["byte_length"],
                                    "packets": p["streams"][sid]["packet_count"],
                                    "batches": p["streams"][sid]["batch_count"],
                                    "sha256": p["streams"][sid]["sha256"],
                                    "decoded_file": VARIANTS[vid]["out"]},
                                   "source_evidence" if all(x["identical_to_source"] for x in
                                                            p["streams"][sid]["stock_dtb_corroboration"].values())
                                   else "conflicting",
                                   {"repository": k.url, "commit": k.commit, "path": f,
                                    "line": p["streams"][sid]["source"]["line"],
                                    "line_end": p["streams"][sid]["source"]["line_end"]},
                                   *[dref(d, n, p["streams"][sid]["property"]) for d in dtbs])
                         for sid in p["streams"]},
        }
    return ev


if __name__ == "__main__":
    main()
