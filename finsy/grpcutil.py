"Utility functions for opening a GRPC channel."

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
from pathlib import Path
from typing import cast

import grpc  # pyright: ignore[reportMissingTypeStubs]
from typing_extensions import Self

from finsy.log import LOGGER
from finsy.proto import rpc_code

# `grpc.aio.EOF` is not typed.
GRPC_EOF: object = cast(
    object, grpc.aio.EOF  # pyright: ignore[reportUnknownMemberType]
)


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
        return GRPCStatusCode(
            val.value[0]  # pyright: ignore[reportUnknownArgumentType]
        )

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

    MAX_METADATA_SIZE = "grpc.max_metadata_size"  # int
    MAX_RECONNECT_BACKOFF_MS = "grpc.max_reconnect_backoff_ms"  # int
    SSL_TARGET_NAME_OVERRIDE_ARG = "grpc.ssl_target_name_override"  # str


GRPCChannelArgumentType = list[tuple[str, int | str]]


@dataclass
class GRPCOptions:
    "GRPC channel arguments."

    max_metadata_size: int | None = None
    max_reconnect_backoff_ms: int | None = None

    def to_native(self) -> GRPCChannelArgumentType:
        "Return GRPC options in form suitable for grpc API."
        results: GRPCChannelArgumentType = []

        if self.max_metadata_size is not None:
            results.append((GRPCArg.MAX_METADATA_SIZE, self.max_metadata_size))
        if self.max_reconnect_backoff_ms is not None:
            results.append(
                (GRPCArg.MAX_RECONNECT_BACKOFF_MS, self.max_reconnect_backoff_ms)
            )
        return results


@dataclass(kw_only=True)
class GRPCCredentialsTLS:
    "GRPC channel credentials for Transport Layer Security (TLS)."

    cacert: Path | bytes | None
    """Certificate authority used to authenticate the certificate at the other
    end of the connection."""

    cert: Path | bytes | None
    "Certificate that identifies this side of the connection."

    private_key: Path | bytes | None
    "Private key associated with this side's certificate identity."

    target_name_override: str = ""
    "Override the target name used for TLS host name checking (useful for testing)."

    call_credentials: grpc.AuthMetadataPlugin | None = None
    """Optional GRPC call credentials for the client channel. Be aware that the
    auth plugin's callback takes place in a different thread."""

    def to_client_credentials(self) -> grpc.ChannelCredentials:
        "Create native SSL client credentials object."
        root_certificates = _coerce_tls_path(self.cacert)
        certificate_chain = _coerce_tls_path(self.cert)
        private_key = _coerce_tls_path(self.private_key)

        return self._compose_credentials(
            grpc.ssl_channel_credentials(  # pyright: ignore[reportUnknownMemberType]
                root_certificates=root_certificates,
                private_key=private_key,
                certificate_chain=certificate_chain,
            )
        )

    def to_server_credentials(self) -> grpc.ServerCredentials:
        """Create native SSL server credentials object.

        On the server side, we ignore the `call_credentials`.
        """
        root_certificates = _coerce_tls_path(self.cacert)
        certificate_chain = _coerce_tls_path(self.cert)
        private_key = _coerce_tls_path(self.private_key)

        return grpc.ssl_server_credentials(  # pyright: ignore[reportUnknownMemberType]
            private_key_certificate_chain_pairs=[(private_key, certificate_chain)],
            root_certificates=root_certificates,
            require_client_auth=True,
        )

    def _compose_credentials(
        self, channel_cred: grpc.ChannelCredentials
    ) -> grpc.ChannelCredentials:
        "Compose call credentials with channel credentials."
        if not self.call_credentials:
            return channel_cred

        call_cred = (
            grpc.metadata_call_credentials(  # pyright: ignore[reportUnknownMemberType]
                self.call_credentials
            )
        )
        return grpc.composite_channel_credentials(  # pyright: ignore[reportUnknownMemberType]
            channel_cred,
            call_cred,
        )


def _coerce_tls_path(value: Path | bytes | None) -> bytes | None:
    "Convert Path to bytes."
    if isinstance(value, Path):
        return value.read_bytes()
    assert value is None or isinstance(value, bytes)
    return value


def grpc_channel(
    address: str,
    *,
    credentials: GRPCCredentialsTLS | None = None,
    options: GRPCOptions | None = None,
    client_type: str = "GRPC",
) -> grpc.aio.Channel:
    "Create a GRPC AIO channel."
    if credentials is None:
        LOGGER.debug("%s: create INSECURE channel %r", client_type, address)
        channel = grpc.aio.insecure_channel(
            address,
            options=options.to_native() if options else None,
        )
    else:
        LOGGER.debug("%s: create secure channel %r", client_type, address)
        args: GRPCChannelArgumentType = options.to_native() if options else []
        if credentials.target_name_override:
            args.append(
                (GRPCArg.SSL_TARGET_NAME_OVERRIDE_ARG, credentials.target_name_override)
            )
        channel = grpc.aio.secure_channel(
            address,
            credentials=credentials.to_client_credentials(),
            options=args,
        )

    return channel
