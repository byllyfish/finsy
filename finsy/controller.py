"Implements the Controller class."

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

import asyncio
from contextvars import ContextVar
from types import TracebackType
from typing import Any, Iterable, Iterator

from typing_extensions import Self

from finsy.futures import CountdownFuture, wait_for_cancel
from finsy.log import LOGGER
from finsy.switch import Switch, SwitchEvent, SwitchFailFastError


class Controller:
    """A Controller is a collection of switches.

    Each switch MUST have a unique name.
    """

    _switches: dict[str, Switch]
    _removed: set[Switch]
    _task_count: CountdownFuture

    control_task: asyncio.Task[Any] | None = None
    "Keep track of controller's main task."

    def __init__(self, switches: Iterable[Switch] = ()):
        "Initialize Controller with a list of switches."
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

    async def run(self) -> None:
        "Run the controller."
        async with self:
            await wait_for_cancel()

    def stop(self) -> None:
        "Stop the controller if it is running."
        if self.control_task is not None:
            self.control_task.cancel()

    async def __aenter__(self) -> Self:
        "Run the controller as a context manager (see also run())."
        assert not self.running, "Controller.__aenter__ is not re-entrant"
        assert self._task_count.value() == 0
        assert not self._removed

        self.control_task = asyncio.current_task()
        _CONTROLLER.set(self)

        try:
            # Start each switch running.
            for switch in self:
                self._start_switch(switch)
        except Exception:
            self.control_task = None
            _CONTROLLER.set(None)
            raise

        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> bool | None:
        "Run the controller as a context manager (see also run())."
        assert self.running

        try:
            # Stop all the switches.
            for switch in self:
                self._stop_switch(switch)

            # Wait for switch tasks to finish.
            await self._task_count.wait()

        finally:
            self.control_task = None
            _CONTROLLER.set(None)

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
            switch.ee.once(SwitchEvent.CONTROLLER_LEAVE, self._removed.discard)  # type: ignore

    def _start_switch(self, switch: Switch):
        "Start the switch's control task."
        LOGGER.debug("Controller._start_switch: %r", switch)
        assert switch.control_task is None

        switch.ee.emit(SwitchEvent.CONTROLLER_ENTER, switch)

        task = asyncio.create_task(switch.run(), name=f"fy:{switch.name}")
        switch.control_task = task
        self._task_count.increment()

        def _switch_done(done: asyncio.Task[Any]):
            switch.control_task = None
            switch.ee.emit(SwitchEvent.CONTROLLER_LEAVE, switch)
            self._task_count.decrement()

            if not done.cancelled():
                ex = done.exception()
                if ex is not None:
                    if not isinstance(ex, SwitchFailFastError):
                        # The `fail_fast` error has already been logged. If
                        # it's any other error, log it. (There shouldn't be
                        # any other error.)
                        LOGGER.critical(
                            "Controller task %r failed",
                            done.get_name(),
                            exc_info=ex,
                        )
                    # Shutdown the program cleanly due to switch failure.
                    raise SystemExit(99)

        task.add_done_callback(_switch_done)

    def _stop_switch(self, switch: Switch):
        "Stop the switch's control task."
        LOGGER.debug("Controller._stop_switch: %r", switch)

        if switch.control_task is not None:
            switch.control_task.cancel()

    def __len__(self) -> int:
        "Return switch count."
        return len(self._switches)

    def __iter__(self) -> Iterator[Switch]:
        "Iterate over switches."
        return iter(self._switches.values())

    def __getitem__(self, name: str) -> Switch:
        "Retrieve switch by name."
        return self._switches[name]

    def get(self, name: str) -> Switch | None:
        "Retrieve switch by name, or return None if not found."
        return self._switches.get(name)

    @staticmethod
    def current() -> "Controller":
        "Return the current Controller object."
        result = _CONTROLLER.get()
        if result is None:
            raise RuntimeError("controller does not exist")
        return result


_CONTROLLER: ContextVar[Controller | None] = ContextVar("_CONTROLLER", default=None)
