"""
.. include:: ../README.md

# API Documentation
"""

# Copyright (c) 2022-2023 Bill Fisher
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

__version__ = "0.19.0"

import sys

if sys.version_info < (3, 10):  # pragma: no cover
    raise RuntimeError("Requires Python 3.10+.")

from .controller import Controller
from .gnmiclient import GNMIClient, GNMISubscription, GNMIUpdate
from .gnmipath import GNMIPath
from .grpcutil import GRPCCredentialsTLS, GRPCStatusCode
from .log import LoggerAdapter
from .macaddr import MACAddress
from .p4client import P4Client, P4ClientError, P4Error
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
    P4DirectMeterEntry,
    P4IndirectAction,
    P4Member,
    P4MeterConfig,
    P4MeterCounterData,
    P4MeterEntry,
    P4MulticastGroupEntry,
    P4PacketIn,
    P4PacketOut,
    P4RegisterEntry,
    P4TableAction,
    P4TableEntry,
    P4TableMatch,
    P4ValueSetEntry,
)
from .p4schema import P4ConfigAction, P4CounterUnit, P4Schema
from .ports import SwitchPort, SwitchPortList
from .runner import run
from .switch import Switch, SwitchEvent, SwitchOptions

__all__ = [
    "run",
    "Controller",
    "LoggerAdapter",
    "MACAddress",
    "P4ActionProfileGroup",
    "P4ActionProfileMember",
    "P4Client",
    "P4ClientError",
    "P4CloneSessionEntry",
    "P4CounterData",
    "P4CounterEntry",
    "P4CounterUnit",
    "P4DigestEntry",
    "P4DigestList",
    "P4DigestListAck",
    "P4DirectCounterEntry",
    "P4DirectMeterEntry",
    "P4Error",
    "P4IndirectAction",
    "P4Member",
    "P4MeterConfig",
    "P4MeterCounterData",
    "P4MeterEntry",
    "P4MulticastGroupEntry",
    "P4PacketIn",
    "P4PacketOut",
    "P4RegisterEntry",
    "P4TableAction",
    "P4TableEntry",
    "P4TableMatch",
    "P4ValueSetEntry",
    "P4ConfigAction",
    "P4Schema",
    "Switch",
    "SwitchEvent",
    "SwitchOptions",
    "SwitchPort",
    "SwitchPortList",
    "GNMIClient",
    "GNMIPath",
    "GNMISubscription",
    "GNMIUpdate",
    "GRPCCredentialsTLS",
    "GRPCStatusCode",
]
