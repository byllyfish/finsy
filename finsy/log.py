"Logging utilities."

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
import os
from typing import TYPE_CHECKING, Any, MutableMapping, TypeAlias


def get_setting(name: str, default: str = "") -> bool:
    "Retrieve environment variable setting."
    value = os.environ.get(name, default)
    if not value:
        return False
    return value.strip().lower() not in {"0", "false"}


FINSY_DEBUG = get_setting("FINSY_DEBUG")


if TYPE_CHECKING:  # pragma: no cover
    _BaseLoggerAdapter: TypeAlias = logging.LoggerAdapter[logging.Logger]
else:
    # logging.LoggerAdapter will be generic at runtime in Python 3.11.
    _BaseLoggerAdapter: TypeAlias = logging.LoggerAdapter


def _get_current_task_name(shorten: bool = False) -> str:
    "Return the name of the current task (or '' if there is none.)"
    # current_task() raises RuntimeError if there is no running event loop.
    try:
        task = asyncio.current_task()
    except RuntimeError:
        return ""

    # Task may be None if we're not in a task; e.g. in a low-level callback.
    if not task:
        return ""

    # Remove the "fy:" prefix from the task name.
    name = task.get_name()
    if name.startswith("fy:"):
        name = name[3:]

    # Shorten task name to omit details after "|".
    if shorten:
        pos = name.find("|")
        if pos > 0:
            name = name[:pos]

    return name


class LoggerAdapter(_BaseLoggerAdapter):
    """Custom log adapter to include the name of the current task."""

    def process(
        self,
        msg: Any,
        kwargs: MutableMapping[str, Any],
    ) -> tuple[Any, MutableMapping[str, Any]]:
        """Process the logging message and keyword arguments passed in to a
        logging call to insert contextual information.
        """
        task_name = _get_current_task_name()
        return f"[{task_name}] {msg}", kwargs

    def info(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        """INFO level uses a concise task name represention for readability."""
        if self.logger.isEnabledFor(logging.INFO):
            task_name = _get_current_task_name(True)
            self.logger.info(f"[{task_name}] {msg}", *args, **kwargs)


LOGGER = LoggerAdapter(logging.getLogger(__package__))
MSG_LOG = LoggerAdapter(logging.getLogger(f"{__package__}.msg"))

if FINSY_DEBUG:  # pragma: no cover
    # If FINSY_DEBUG is true, log all protobuf messages.
    MSG_LOG.setLevel(logging.DEBUG)
