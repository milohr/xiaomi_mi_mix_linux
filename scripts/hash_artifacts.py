#!/usr/bin/env python3
"""Emit an input manifest to stdout; does not modify artifacts."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('files', nargs='+', type=Path)
a = p.parse_args()
items = []
for path in a.files:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    items.append({'file': str(path), 'bytes': path.stat().st_size,
                  'sha256': digest.hexdigest()})
print(json.dumps({'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'artifacts': items}, indent=2))
