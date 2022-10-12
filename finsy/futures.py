"Asyncio utilities."

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
from typing import Any, Callable

from finsy.log import LOGGER, TRACE


def _create_future() -> asyncio.Future[Any]:
    "Create a new Future."
    return asyncio.get_running_loop().create_future()


async def wait_for_cancel() -> None:
    "Wait for the running task to be cancelled or interrupted."
    try:
        await _create_future()
    except (asyncio.CancelledError, KeyboardInterrupt) as ex:
        LOGGER.debug("wait_for_cancel interrupted: %r", ex)


class CountdownFuture:
    """Implements a `Future` that we can await to count down to <= zero.

    A `CountdownFuture` can be used to track the number of running tasks and
    wait for them to finish.

    If a `CountdownFuture` is cancelled itself, it will execute a custom cancel
    function, then wait for the countdown to fully finish.
    """

    _future: asyncio.Future[int] | None = None
    _counter: int = 0

    def increment(self) -> None:
        "Increment the countdown counter."
        if self._future is None or self._future.done():
            self._future = _create_future()

        self._counter += 1

    def decrement(self) -> None:
        "Decrement the countdown counter."
        assert self._future is not None

        self._counter -= 1
        if self._counter <= 0 and not self._future.cancelled():
            self._future.set_result(1)

    def value(self) -> int:
        "Return current value of counter."
        return self._counter

    @TRACE
    async def wait(
        self,
        on_cancel: Callable[[], None] | None = None,
    ) -> None:
        "Wait for the countdown to finish."
        if self._counter <= 0:
            return

        assert self._future is not None

        try:
            await self._future
        except asyncio.CancelledError:
            if on_cancel is not None:
                on_cancel()
            await self._wait_cancelled()
            raise

    @TRACE
    async def _wait_cancelled(self) -> None:
        assert self._future and self._future.cancelled()

        while True:
            if self._counter <= 0:
                break

            self._future = _create_future()
            try:
                await self._future
            except asyncio.CancelledError:
                # Handle case where we receive subsequent cancel's but the
                # countdown still isn't finished.
                pass
            else:
                break
