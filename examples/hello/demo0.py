import sys
from pathlib import Path

import finsy as fy

if len(sys.argv) != 2:
    print("Usage: demo0.py <path>", file=sys.stderr)
    sys.exit(1)

p4info_path = Path(sys.argv[1])
p4info = fy.P4Schema(p4info_path)
print(p4info)
