import sys
from pathlib import Path

import finsy as fy

p4info = fy.P4Schema(Path(sys.argv[1]))
print(p4info)
