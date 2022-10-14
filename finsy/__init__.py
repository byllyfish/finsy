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

__version__ = "0.7.0"

import sys

if sys.version_info < (3, 10):  # pragma: no cover
    raise RuntimeError("Requires Python 3.10+.")

from .controller import Controller, current_controller
from .gnmiclient import gNMIClient, gNMISubscription, gNMIUpdate
from .gnmipath import gNMIPath
from .log import LoggerAdapter
from .p4entity import (
    P4ActionProfileGroup,
    P4ActionProfileMember,
    P4CloneSessionEntry,
    P4CounterData,
    P4CounterEntry,
    P4DigestEntry,
    P4DigestList,
    P4DigestListAck,
    P4DirectCounterEntry,
    P4IndirectAction,
    P4MeterConfig,
    P4MeterCounterData,
    P4MulticastGroupEntry,
    P4PacketIn,
    P4PacketOut,
    P4RegisterEntry,
    P4TableAction,
    P4TableEntry,
    P4TableMatch,
)
from .p4schema import P4ConfigAction, P4CounterUnit, P4Schema
from .switch import Switch, SwitchEvent, SwitchOptions

__all__ = [
    "current_controller",
    "Controller",
    "LoggerAdapter",
    "P4ActionProfileGroup",
    "P4ActionProfileMember",
    "P4CloneSessionEntry",
    "P4CounterData",
    "P4CounterEntry",
    "P4CounterUnit",
    "P4DigestEntry",
    "P4DigestList",
    "P4DigestListAck",
    "P4DirectCounterEntry",
    "P4IndirectAction",
    "P4MeterConfig",
    "P4MeterCounterData",
    "P4MulticastGroupEntry",
    "P4PacketIn",
    "P4PacketOut",
    "P4RegisterEntry",
    "P4TableAction",
    "P4TableEntry",
    "P4TableMatch",
    "P4ConfigAction",
    "P4Schema",
    "Switch",
    "SwitchEvent",
    "SwitchOptions",
    "gNMIClient",
    "gNMIPath",
    "gNMISubscription",
    "gNMIUpdate",
]
