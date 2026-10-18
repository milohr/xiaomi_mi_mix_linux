#!/usr/bin/env python3
"""Decode Qualcomm downstream records without discarding transport metadata."""
import argparse
import json
import re
from pathlib import Path

TYPES = {0x05: 'dcs_short_write', 0x15: 'dcs_short_write_param',
         0x39: 'dcs_long_write', 0x03: 'generic_short_write_0',
         0x13: 'generic_short_write_1', 0x23: 'generic_short_write_2',
         0x29: 'generic_long_write', 0x06: 'dcs_read'}

def parse(text):
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    if '[' in text:
        if text.count('[') != 1 or text.count(']') != 1:
            raise ValueError('Provide exactly one byte block')
        text = text.split('[', 1)[1].split(']', 1)[0]
    tokens = text.split()
    if not tokens or any(not re.fullmatch(r'[0-9a-fA-F]{2}', t) for t in tokens):
        raise ValueError('Expected whitespace-separated two-digit hexadecimal bytes')
    data = bytes(int(t, 16) for t in tokens)
    records = []
    offset = 0
    while offset < len(data):
        start = offset
        if len(data) - offset < 7:
            raise ValueError(f'Truncated header at byte {offset}')
        dtype, last, channel, ack, delay, hi, lo = data[offset:offset+7]
        length = (hi << 8) | lo
        offset += 7
        if len(data) - offset < length:
            raise ValueError(f'Truncated payload at byte {start}: expected {length}')
        records.append(dict(offset=start, type=dtype,
                            kind=TYPES.get(dtype, 'unknown_preserved'), last=last,
                            channel=channel, ack=ack, delay_ms=delay,
                            length=length, payload=list(data[offset:offset+length])))
        offset += length
    return records

def render_c(records):
    lines = ['/* Audit representation only; no transport executor. */',
             '#include <linux/types.h>',
             'struct lithium_panel_record {',
             '    u8 type, last, channel, ack, delay_ms;',
             '    u16 length;',
             '    const u8 *payload;',
             '};']
    for i, record in enumerate(records):
        if record['payload']:
            payload = ', '.join(f'0x{x:02x}' for x in record['payload'])
            lines.append(f'static const u8 panel_payload_{i}[] = {{ {payload} }};')
    lines.append('static const struct lithium_panel_record panel_records[] = {')
    for i, r in enumerate(records):
        payload = f'panel_payload_{i}' if r['payload'] else '0'
        lines.append('    { .type = 0x%02x, .last = %d, .channel = %d, '
                     '.ack = %d, .delay_ms = %d, .length = %d, .payload = %s },'
                     % (r['type'], r['last'], r['channel'], r['ack'],
                        r['delay_ms'], r['length'], payload))
    lines.append('};')
    return '\n'.join(lines)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--format', choices=['json', 'c'], default='json')
    args = parser.parse_args()
    try:
        records = parse(args.input.read_text())
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(records, indent=2) if args.format == 'json' else render_c(records))

if __name__ == '__main__':
    main()
