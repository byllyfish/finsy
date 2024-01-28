"Implements the run() function."

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
import logging
import signal
import sys
from typing import Any, Coroutine

from finsy.p4schema import P4SchemaCache


def _sigterm_cancel_task(task: asyncio.Task[Any]) -> None:
    task.cancel()


async def _finsy_boilerplate(coro: Coroutine[Any, Any, None]):
    "Wrap main async function and implement boilerplate."
    logging.basicConfig(
        level=logging.INFO,
        format="%(created).03f %(levelname)s %(name)s %(message)s",
    )

    if sys.platform != "win32":
        # Boilerplate to shutdown cleanly upon SIGTERM signal.
        current_task = asyncio.current_task()
        assert current_task is not None
        asyncio.get_running_loop().add_signal_handler(
            signal.SIGTERM,
            _sigterm_cancel_task,
            current_task,
        )

    # Enable caching of P4Info definitions.
    with P4SchemaCache():
        await coro


def run(coro: Coroutine[Any, Any, None]) -> None:
    """`finsy.run` provides a useful wrapper around `asyncio.run`.

    This function implements common boilerplate for running a Finsy application.

    - Set up basic logging to stderr at the INFO log level.
    - Set up a signal handler for SIGTERM that shuts down gracefully.
    - Set up caching of P4Info data so common definitions are re-used.

    Example:

    ```python
    import finsy as fy

    async def main():
        async with fy.Switch("sw", "127.0.0.1:50001") as sw:
            print(sw.p4info)

    if __name__ == "__main__":
        fy.run(main())
    ```

    If you choose to use `asyncio.run` instead, your P4Schema/P4Info objects
    will not be eligible for sharing. You can create your own `P4SchemaCache`
    context manager to implement this.
    """
    try:
        asyncio.run(_finsy_boilerplate(coro))
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
