#!/usr/bin/env python3
"""Report host tooling availability without installing anything."""
import json
import platform
import shutil
TOOLS = {'collection': ['adb', 'fastboot'],
         'source_and_analysis': ['git', 'dtc', 'fdtdump', 'sha256sum', 'unpack_bootimg'],
         'packaging': ['pmbootstrap'],
         'kernel_build': ['make', 'gcc', 'clang', 'bison', 'flex', 'pkg-config'],
         'optional_checks': ['shellcheck', 'dt-validate']}
print(json.dumps({'python': platform.python_version(), 'host': platform.platform(),
                  'tools': {phase: {t: shutil.which(t) for t in names}
                            for phase, names in TOOLS.items()},
                  'note': 'Tool presence is not version or target compatibility validation.'}, indent=2))
