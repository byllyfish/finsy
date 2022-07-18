"Utility functions for opening a GRPC channel."

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

import enum
from dataclasses import dataclass
from typing import Sequence

import grpc  # pyright: ignore[reportMissingTypeStubs]
from typing_extensions import Self

from finsy.log import LOGGER
from finsy.proto import rpc_code

# `grpc.aio.EOF` is not typed.
GRPC_EOF: object = grpc.aio.EOF  # pyright: ignore[reportUnknownMemberType]


class _EnumBase(enum.IntEnum):
    "Base class for GRPC/Protobuf Enum wrapper classes."

    def __repr__(self) -> str:
        return f"{type(self).__name__}.{self.name}"


class GRPCStatusCode(_EnumBase):
    "IntEnum equivalent to `grpc.StatusCode`."

    OK = rpc_code.OK
    CANCELLED = rpc_code.CANCELLED
    UNKNOWN = rpc_code.UNKNOWN
    FAILED_PRECONDITION = rpc_code.FAILED_PRECONDITION
    INVALID_ARGUMENT = rpc_code.INVALID_ARGUMENT
    DEADLINE_EXCEEDED = rpc_code.DEADLINE_EXCEEDED
    NOT_FOUND = rpc_code.NOT_FOUND
    ALREADY_EXISTS = rpc_code.ALREADY_EXISTS
    PERMISSION_DENIED = rpc_code.PERMISSION_DENIED
    UNAUTHENTICATED = rpc_code.UNAUTHENTICATED
    RESOURCE_EXHAUSTED = rpc_code.RESOURCE_EXHAUSTED
    ABORTED = rpc_code.ABORTED
    OUT_OF_RANGE = rpc_code.OUT_OF_RANGE
    UNIMPLEMENTED = rpc_code.UNIMPLEMENTED
    INTERNAL = rpc_code.INTERNAL
    UNAVAILABLE = rpc_code.UNAVAILABLE
    DATA_LOSS = rpc_code.DATA_LOSS

    @classmethod
    def from_status_code(cls, val: grpc.StatusCode) -> Self:
        "Create corresponding GRPCStatusCode from a grpc.StatusCode object."
        assert isinstance(val, grpc.StatusCode)
        return GRPCStatusCode(val.value[0])

    @staticmethod
    def _validate_enum() -> None:
        for value in grpc.StatusCode:
            assert GRPCStatusCode[value.name].value == value.value[0], value.name


# Check GRPCStatusCode against grpc.StatusCode.
GRPCStatusCode._validate_enum()  # pyright: ignore[reportPrivateUsage]


class GRPCArg(str, enum.Enum):
    """Names for GRPC channel arguments.

    Reference:
    https://grpc.github.io/grpc/core/group__grpc__arg__keys.html
    """

    MAX_METADATA_SIZE = "grpc.max_metadata_size"
    MAX_RECONNECT_BACKOFF_MS = "grpc.max_reconnect_backoff_ms"


@dataclass
class GRPCOptions:
    "GRPC channel arguments."

    max_metadata_size: int | None = None
    max_reconnect_backoff_ms: int | None = None

    def args(self) -> Sequence[tuple[str, int]]:
        results: list[tuple[str, int]] = []

        if self.max_metadata_size is not None:
            results.append((GRPCArg.MAX_METADATA_SIZE, self.max_metadata_size))

        if self.max_reconnect_backoff_ms is not None:
            results.append(
                (GRPCArg.MAX_RECONNECT_BACKOFF_MS, self.max_reconnect_backoff_ms)
            )

        return results


def grpc_channel(
    address: str,
    *,
    credentials: grpc.ChannelCredentials | None = None,
    options: GRPCOptions | None = None,
    client_type: str = "GRPC",
) -> grpc.aio.Channel:
    "Create a GRPC AIO channel."

    args = options.args() if options else None

    if credentials is None:
        LOGGER.debug("%s: create INSECURE channel %r", client_type, address)
        channel = grpc.aio.insecure_channel(
            address,
            options=args,
        )
    else:
        LOGGER.debug("%s: create secure channel %r", client_type, address)
        channel = grpc.aio.secure_channel(
            address,
            credentials=credentials,
            options=args,
        )

    return channel
