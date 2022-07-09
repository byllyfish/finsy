"Implements the Controller class."

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

import asyncio
from typing import Any, Iterable

from finsy.log import LOGGER, TRACE
from finsy.switch import Switch, SwitchEvent
from finsy.util import CountdownFuture, wait_for_cancel


class Controller:
    """A Controller is a collection of switches.

    Each switch MUST have a unique name.
    """

    _name: str  # used to name control_task
    _switches: dict[str, Switch]
    _removed: set[Switch]
    _task_count: CountdownFuture

    control_task: asyncio.Task[Any] | None = None
    "Keep track of controller's main task."

    def __init__(self, switches: Iterable[Switch], *, name="controller"):
        self._name = name
        self._switches = {}
        self._removed = set()
        self._task_count = CountdownFuture()

        for switch in switches:
            if switch.name in self._switches:
                raise ValueError(f"Switch named {switch.name!r} already exists")
            self._switches[switch.name] = switch

    @property
    def running(self) -> bool:
        "True if Controller is running."
        return self.control_task is not None

    @TRACE
    async def run(self):
        "Run the controller."
        assert not self.running, "Controller.run() is not re-entrant"

        self.control_task = asyncio.current_task()
        assert self.control_task is not None
        self.control_task.set_name(f"fy:{self._name}")

        try:
            # Start each switch running.
            for switch in self:
                self._start_switch(switch)

            # Run forever.
            await wait_for_cancel()

            # Stop all the switches.
            for switch in self:
                self._stop_switch(switch)

            # Wait for switch tasks to finish.
            await self._task_count.wait()

        finally:
            self.control_task = None

    def stop(self):
        "Stop the controller if it is running."

        if self.control_task is not None:
            self.control_task.cancel()

    def add(self, switch: Switch) -> None:
        """Add a switch to the controller.

        If the controller is running, tell the switch to start.
        """
        if switch.name in self._switches:
            raise ValueError(f"Switch named {switch.name!r} already exists")

        assert switch.control_task is None

        self._switches[switch.name] = switch
        if self.running:
            self._start_switch(switch)

    def remove(self, switch: Switch) -> None:
        """Remove a switch from the controller.

        If the controller is running, tell the switch to stop and schedule it
        for removal when it fully stops.
        """
        name = switch.name
        if self._switches.get(name, None) is not switch:
            raise ValueError(f"Switch named {name!r} not found")

        del self._switches[name]

        if self.running:
            self._stop_switch(switch)
            self._removed.add(switch)
            switch.ee.once(SwitchEvent.SWITCH_DONE, self._removed.discard)

    def _start_switch(self, switch: Switch):
        "Start the switch's control task."
        LOGGER.debug("Controller._start_switch: %r", switch)
        assert switch.control_task is None

        task = asyncio.create_task(switch.run(), name=f"fy:{switch.name}")
        switch.control_task = task
        self._task_count.increment()

        def _switch_done(done):
            switch.control_task = None
            switch.ee.emit(SwitchEvent.SWITCH_DONE)
            self._task_count.decrement()

            if not done.cancelled():
                ex = done.exception()
                if ex is not None:
                    LOGGER.error(
                        "Controller task %r failed",
                        done.get_name(),
                        exc_info=ex,
                    )

        task.add_done_callback(_switch_done)

    def _stop_switch(self, switch: Switch):
        "Stop the switch's control task."
        LOGGER.debug("Controller._stop_switch: %r", switch)

        if switch.control_task is not None:
            switch.control_task.cancel()

    def __len__(self):
        "Return switch count."
        return len(self._switches)

    def __iter__(self):
        "Iterate over switches."
        return iter(self._switches.values())

    def __getitem__(self, name):
        "Retrieve switch by name."
        return self._switches[name]
