#!/usr/bin/env python3
"""Collect a narrow Android inventory. No root, reboot or device writes."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PROPS = ['ro.product.manufacturer', 'ro.product.model', 'ro.product.device',
         'ro.product.name', 'ro.board.platform', 'ro.hardware',
         'ro.build.version.release', 'ro.build.version.security_patch',
         'ro.build.version.incremental', 'ro.build.display.id',
         'ro.miui.ui.version.name', 'ro.boot.flash.locked',
         'ro.boot.verifiedbootstate', 'ro.boot.vbmeta.device_state',
         'ro.boot.veritymode', 'ro.oem_unlock_supported',
         'sys.oem_unlock_allowed', 'ro.boot.slot_suffix', 'ro.product.cpu.abilist']

def run(serial, command):
    try:
        p = subprocess.run(['adb', '-s', serial, 'shell', *command],
                           capture_output=True, text=True, timeout=20)
        return {'command': command, 'returncode': p.returncode,
                'stdout': p.stdout.strip(), 'stderr': p.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'command': command, 'returncode': None, 'error': str(exc)}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--serial', required=True, help='Explicit authorized ADB target')
    args = p.parse_args()
    identity = run(args.serial, ['getprop', 'ro.product.device'])
    if identity.get('returncode') != 0 or identity.get('stdout') != 'lithium':
        p.exit(1, 'Refusing collection: target is not an accessible lithium.\n')
    now = datetime.datetime.now(datetime.timezone.utc)
    output = ROOT / 'artifacts' / ('inventory-' + now.strftime('%Y%m%dT%H%M%S%fZ'))
    output.mkdir(parents=True, mode=0o700)
    results = [run(args.serial, ['getprop', prop]) for prop in PROPS]
    for command in [['uname', '-a'], ['cat', '/proc/meminfo'],
                    ['cat', '/proc/partitions'],
                    ['ls', '-l', '/dev/block/bootdevice/by-name'],
                    ['ls', '-l', '/proc/config.gz']]:
        results.append(run(args.serial, command))
    report = {'collected_at': now.isoformat(), 'target': 'lithium',
              'serial_omitted': True, 'results': results}
    target = output / 'inventory.json'
    target.write_text(json.dumps(report, indent=2) + '\n')
    target.chmod(0o600)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (output / 'SHA256SUMS').write_text(f'{digest}  inventory.json\n')
    print(target)
    print('Review denied/unavailable fields; raw results remain ignored by Git.')

if __name__ == '__main__':
    main()
