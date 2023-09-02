"Implements the PortList and Port classes."

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

import enum
from dataclasses import dataclass
from typing import Iterator

import finsy.switch as _sw  # circular import
from finsy.gnmiclient import GNMIClient, GNMIPath, GNMISubscription, GNMIUpdate
from finsy.log import LOGGER

# FIXME: Use GNMI id or ifIndex?
_ifIndex = GNMIPath("interfaces/interface[name=*]/state/ifindex")
_ifOperStatus = GNMIPath("interfaces/interface[name=*]/state/oper-status")


class OperStatus(enum.Enum):
    "gNMI values for ifOperStatus"

    DORMANT = "DORMANT"
    LOWER_LAYER_DOWN = "LOWER_LAYER_DOWN"
    UNKNOWN = "UNKNOWN"
    TESTING = "TESTING"
    UP = "UP"
    DOWN = "DOWN"
    NOT_PRESENT = "NOT_PRESENT"


@dataclass
class SwitchPort:
    "Represents a switch port."

    id: int
    name: str
    oper_status: OperStatus = OperStatus.UNKNOWN

    @property
    def up(self) -> bool:
        "Return true if port is basically up."
        return self.oper_status == OperStatus.UP


class SwitchPortList:
    "Represents a list of switch ports."

    _ports: dict[str, SwitchPort]
    _subscription: GNMISubscription | None = None

    def __init__(self):
        self._ports = {}

    def __getitem__(self, key: str) -> SwitchPort:
        "Retrieve interface by ID."
        return self._ports[key]

    def __len__(self) -> int:
        "Return number of switch ports."
        return len(self._ports)

    def __iter__(self) -> Iterator[SwitchPort]:
        "Iterate over switch ports."
        return iter(self._ports.values())

    async def subscribe(self, client: GNMIClient) -> None:
        """Obtain the initial list of ports and subscribe to switch port status
        updates using GNMI."""
        assert self._subscription is None

        self._ports = await self._get_ports(client)
        if self._ports:
            self._subscription = await self._get_subscription(client)
        else:
            LOGGER.warning("No switch ports exist")

    async def listen(self, switch: "_sw.Switch | None" = None) -> None:
        "Listen for switch port updates."
        assert self._subscription is not None

        async for update in self._subscription.updates():
            self._update(update, switch)

    def close(self) -> None:
        "Close the switch port subscription."
        if self._subscription is not None:
            self._subscription.cancel()
            self._subscription = None
            self._ports = {}

    async def _get_ports(self, client: GNMIClient) -> dict[str, SwitchPort]:
        "Retrieve ID and name of each port."
        ports: dict[str, SwitchPort] = {}

        result = await client.get(_ifIndex)
        for update in result:
            path = update.path
            assert path.last == _ifIndex.last

            port = SwitchPort(update.value, path["name"])
            ports[port.name] = port

        return ports

    async def _get_subscription(self, client: GNMIClient) -> GNMISubscription:
        sub = client.subscribe()

        # Subscribe to change notifications.
        for port in self._ports.values():
            sub.on_change(_ifOperStatus.set(name=port.name))

        # Synchronize initial settings for ports.
        async for update in sub.synchronize():
            self._update(update, None)

        return sub

    def _update(self, update: GNMIUpdate, switch: "_sw.Switch | None"):
        path = update.path
        if path.last == _ifOperStatus.last:
            status = OperStatus(update.value)
            self._update_port(path["name"], status, switch)
        else:
            LOGGER.warning(f"PortList: unknown gNMI path: {path}")

    def _update_port(self, name: str, status: OperStatus, switch: "_sw.Switch | None"):
        port = self._ports[name]

        prev_up = port.up
        port.oper_status = status
        curr_up = port.up

        if switch is not None and curr_up != prev_up:
            if curr_up:
                switch.ee.emit(_sw.SwitchEvent.PORT_UP, switch, port)
            else:
                switch.ee.emit(_sw.SwitchEvent.PORT_DOWN, switch, port)
