"Finsy is a P4Runtime framework for Python."

# Copyright (c) 2022 Bill Fisher
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

__version__ = "0.1.0"

import sys

if sys.version_info < (3, 10):
    raise RuntimeError("Requires Python 3.10+.")

from .controller import *
from .p4entity import *
from .p4schema import *
from .switch import *

__all__ = controller.__all__ + switch.__all__ + p4schema.__all__ + p4entity.__all__
