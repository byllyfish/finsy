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
from typing import Any, Coroutine


async def _finsy_main(coro: Coroutine[Any, Any, None]):
    # Activate logging.
    logging.basicConfig(level=logging.INFO)

    # Boilerplate to shutdown cleanly upon SIGTERM signal.
    asyncio.get_running_loop().add_signal_handler(
        signal.SIGTERM,
        lambda task: task.cancel(),
        asyncio.current_task(),
    )

    await coro


def run(coro: Coroutine[Any, Any, None]):
    "Helper API that provides the boilerplate for `asyncio.run`."
    try:
        asyncio.run(_finsy_main(coro))
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
