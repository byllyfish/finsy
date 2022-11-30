"""
Finsy demo program that reads an existing P4Info file and prints out a
description of its contents.
"""

import sys
from pathlib import Path

import finsy as fy

if len(sys.argv) != 2:
    print("Usage: demo0.py <path>", file=sys.stderr)
    sys.exit(1)

p4info_path = Path(sys.argv[1])

# Create a P4Schema object from the given P4Info file, then print it out.
p4info = fy.P4Schema(p4info_path)
print(p4info)
