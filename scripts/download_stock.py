#!/usr/bin/env python3
"""Resume the exact-build Xiaomi archive on the host; never flash it."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[1]
report = json.loads((ROOT / 'research/recovery-baseline.json').read_text())
url = report['rom_candidate']['official_download_url']
expected = report['download']['expected_bytes']
folder = ROOT / 'artifacts/stock'
folder.mkdir(parents=True, exist_ok=True)
partial = folder / 'lithium-global-V11.0.2.0.tgz.partial'
final = folder / 'lithium-global-V11.0.2.0.tgz'
if final.exists():
    sys.exit('Completed filename already exists; verify its manifest before reuse.')
result = subprocess.run(['curl', '--fail', '--location', '--proto', '=https',
    '--proto-redir', '=https', '--connect-timeout', '20', '--max-time', '900',
    '--continue-at', '-', '--output', str(partial), url])
if result.returncode:
    sys.exit('Transfer incomplete; partial retained. Rerun to resume, not to flash.')
if partial.stat().st_size != expected:
    sys.exit('Unexpected byte count; partial retained for investigation.')
hash_value = hashlib.sha256()
with partial.open('rb') as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        hash_value.update(chunk)
partial.rename(final)
manifest = {'url': url, 'bytes': expected, 'sha256': hash_value.hexdigest(),
            'file': final.name, 'status': 'download_complete_not_yet_archive_audited',
            'note': 'Local hash records identity; it is not an independently published signature.'}
(final.with_suffix('.manifest.json')).write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest, indent=2))
