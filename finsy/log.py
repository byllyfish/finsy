"Logging utilities."

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
import functools
import logging
import os
import sys
from typing import TYPE_CHECKING, Any, MutableMapping, TypeAlias


def get_setting(name: str, default: str = "") -> bool:
    "Retrieve environment variable setting."
    value = os.environ.get(name, default)
    if not value:
        return False
    return value.strip().lower() not in {"0", "false"}


FINSY_DEBUG = get_setting("FINSY_DEBUG")
FINSY_TRANSLATE_LOGS = get_setting("FINSY_TRANSLATE_LOGS", "true")


if TYPE_CHECKING:
    _LoggerAdapter: TypeAlias = logging.LoggerAdapter[logging.Logger]
else:
    # LoggerAdapter will be generic at runtime in Python 3.11.
    _LoggerAdapter: TypeAlias = logging.LoggerAdapter


class _CustomAdapter(_LoggerAdapter):
    """Custom log adapter to include the name of the current task."""

    def process(
        self,
        msg: Any,
        kwargs: MutableMapping[str, Any],
    ) -> tuple[Any, MutableMapping[str, Any]]:
        """Process the logging message and keyword arguments passed in to a
        logging call to insert contextual information.
        """

        task_name = ""
        try:
            # current_task() will raise a RuntimeError if there is no running
            # event loop. It can also return None if there's a running event
            # loop but we aren't in a task (ie we're in a low-level callback).
            task = asyncio.current_task()
            if task:
                task_name = task.get_name()
                # Remove the "fy:" prefix from the task name before logging.
                if task_name.startswith("fy:"):
                    task_name = task_name[3:]
                task_name = f"[{task_name}] "
            else:
                task_name = "[] "  # low-level callback - no running task
        except RuntimeError:
            pass

        return f"{task_name}{msg}", kwargs


LOGGER = _CustomAdapter(logging.getLogger(__package__))
MSG_LOG = _CustomAdapter(logging.getLogger(f"{__package__}.msg"))
TRACE_LOG = _CustomAdapter(logging.getLogger(f"{__package__}.trace"))


def _exc() -> BaseException | None:
    # TODO: replace sys.exc_info() with sys.exception() someday...
    return sys.exc_info()[1]


def _trace_step(func: Any) -> Any:
    "Decorator to log when we step in and step out of a coroutine function."

    @functools.wraps(func)
    async def _wrapper(*args: Any, **kwd: Any):
        try:
            TRACE_LOG.info("%s stepin", func.__qualname__)
            return await func(*args, **kwd)
        finally:
            TRACE_LOG.info("%s stepout ex=%r", func.__qualname__, _exc())

    return _wrapper


def _trace_noop(func: Any) -> Any:
    "No op decorator"
    return func


TRACE = _trace_step if FINSY_DEBUG else _trace_noop
