"Implements the P4Client class."

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

import re
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Sequence, TypeAlias, overload

import grpc  # pyright: ignore[reportMissingTypeStubs]

from finsy import pbuf
from finsy.grpcutil import GRPC_EOF, GRPCOptions, GRPCStatusCode, grpc_channel
from finsy.log import LOGGER, TRACE
from finsy.p4schema import P4Schema
from finsy.proto import p4r, p4r_grpc, rpc_code, rpc_status

_DEFAULT_RPC_TIMEOUT = 10.0

# GRPCStatusCode.INVALID_ARGUMENT
#   simple_switch_grpc: 'Election id already exists'
#   stratum_bmv2: 'Election ID is already used by another connection with the same role.'

_ELECTION_ID_EXISTS = re.compile(
    r"election id .*\b(?:used|exists)\b",
    re.IGNORECASE,
)

# GRPCStatusCode.FAILED_PRECONDITION
#   simple_switch_grpc: 'No forwarding pipeline config set for this device.'
#   stratum_bmv2: 'No valid forwarding pipeline config has been pushed for any node so far.'

_NO_PIPELINE_CONFIG = re.compile(
    r"no .*\bforwarding pipeline config",
    re.IGNORECASE,
)


@dataclass
class P4SubError:
    canonical_code: GRPCStatusCode
    message: str
    space: str
    code: int
    subvalue: pbuf.PBMessage | None = None


@dataclass
class P4Status:
    "Implements rpc.status."

    code: GRPCStatusCode
    message: str
    details: dict[int, P4SubError]

    @property
    def is_not_found_only(self) -> bool:
        """Return True if the only sub-errors are NOT_FOUND."""
        if self.code != GRPCStatusCode.UNKNOWN:
            return False

        for err in self.details.values():
            if err.canonical_code != GRPCStatusCode.NOT_FOUND:
                return False
        return True

    @property
    def is_election_id_used(self) -> bool:
        """Return true if error is that election ID is in use."""
        return (
            self.code == GRPCStatusCode.INVALID_ARGUMENT
            and _ELECTION_ID_EXISTS.search(self.message) is not None
        )

    @property
    def is_no_pipeline_configured(self) -> bool:
        "Return true if error is that no pipeline config is set."
        return (
            self.code == GRPCStatusCode.FAILED_PRECONDITION
            and _NO_PIPELINE_CONFIG.search(self.message) is not None
        )

    @staticmethod
    def from_rpc_error(error: grpc.RpcError) -> "P4Status":
        "Construct status from RpcError."
        assert isinstance(error, grpc.aio.AioRpcError)

        for key, value in error.trailing_metadata():
            if key == "grpc-status-details-bin":
                assert isinstance(value, bytes)
                return P4Status.from_bytes(value)

        return P4Status(
            GRPCStatusCode.from_status_code(error.code()),
            error.details() or "",
            {},
        )

    @staticmethod
    def from_bytes(data: bytes) -> "P4Status":
        "Construct status from protobuf bytes."
        status = rpc_status.Status()
        status.ParseFromString(data)
        return P4Status.from_status(status)

    @staticmethod
    def from_status(status: rpc_status.Status) -> "P4Status":
        "Construct status from RPC status."
        return P4Status(
            GRPCStatusCode(status.code),
            status.message,
            P4Status._parse_error(status.details),
        )

    @staticmethod
    def _parse_error(details: Sequence[pbuf.PBAny]) -> dict[int, P4SubError]:
        result: dict[int, P4SubError] = {}

        for i in range(len(details)):
            err = pbuf.from_any(details[i], p4r.Error)
            if err.canonical_code != rpc_code.OK:
                result[i] = P4SubError(
                    GRPCStatusCode(err.canonical_code),
                    err.message,
                    err.space,
                    err.code,
                )
        return result


class P4ClientError(Exception):
    "Wrap grpc.RpcError."

    _operation: str
    _status: P4Status
    _outer_code: GRPCStatusCode
    _outer_message: str

    def __init__(
        self,
        error: grpc.RpcError,
        operation: str,
        *,
        msg: pbuf.PBMessage | None = None,
    ):
        super().__init__()
        assert isinstance(error, grpc.aio.AioRpcError)

        self._operation = operation
        self._status = P4Status.from_rpc_error(error)
        self._outer_code = GRPCStatusCode.from_status_code(error.code())
        self._outer_message = error.details() or ""

        if msg is not None and self.details:
            self._attach_details(msg)

        LOGGER.debug("%s failed: %s", operation, self)

    @property
    def operation(self) -> str:
        return self._operation

    @property
    def status(self) -> P4Status:
        return self._status

    @property
    def code(self) -> GRPCStatusCode:
        return self._status.code

    @property
    def message(self) -> str:
        return self._status.message

    @property
    def details(self) -> dict[int, P4SubError]:
        return self._status.details

    @property
    def is_unimplemented(self) -> bool:
        return self.code == GRPCStatusCode.UNIMPLEMENTED

    def _attach_details(self, msg: pbuf.PBMessage):
        "Attach the subvalue(s) from the message that caused the error."
        if isinstance(msg, p4r.WriteRequest):
            for key, value in self.details.items():
                value.subvalue = msg.updates[key]

    def __str__(self) -> str:
        if self.details:

            def _indent(value: P4SubError):
                s = repr(value).replace("\n}\n)", "\n})")  # tidy multiline repr
                return s.replace("\n", "\n" + " " * 6)

            items = [""] + [
                f"  [details.{key}] {_indent(val)}" for key, val in self.details.items()
            ]
            details = "\n".join(items)
        else:
            details = ""

        if self.code == self._outer_code and self.message == self._outer_message:
            return (
                f"operation={self.operation} code={self.code!r} "
                f"message={self.message!r} {details}"
            )
        return (
            f"code={self.code!r} message={self.message!r} "
            f"details={self.details!r} operation={self.operation} "
            f"_outer_message={self._outer_message!r} _outer_code={self._outer_code!r}"
        )


_P4StreamTypeAlias: TypeAlias = grpc.aio.StreamStreamCall[
    p4r.StreamMessageRequest, p4r.StreamMessageResponse
]


class P4Client:
    "Implements a P4Runtime client."

    _address: str
    _credentials: grpc.ChannelCredentials | None
    _wait_for_ready: bool
    _channel: grpc.aio.Channel | None = None
    _stub: p4r_grpc.P4RuntimeStub | None = None
    _stream: _P4StreamTypeAlias | None = None
    _complete_request: Callable[[pbuf.PBMessage], None] | None = None

    _schema: P4Schema | None = None
    "Annotate log messages using this optional P4Info schema."

    def __init__(
        self,
        address: str,
        credentials: grpc.ChannelCredentials | None = None,
        *,
        wait_for_ready: bool = True,
    ) -> None:
        self._address = address
        self._credentials = credentials
        self._wait_for_ready = wait_for_ready

    @property
    def channel(self) -> grpc.aio.Channel | None:
        "Return the GRPC channel object, or None if the channel is not open."
        return self._channel

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, *args: Any):
        await self.close()

    @TRACE
    async def open(
        self,
        *,
        schema: P4Schema | None = None,
        complete_request: Callable[[pbuf.PBMessage], None] | None = None,
    ) -> None:
        """Open the client channel.

        Note: This method is `async` for forward-compatible reasons.
        """
        assert self._channel is None
        assert self._stub is None

        # Increase max_metadata_size from 8 KB to 32 KB.
        options = GRPCOptions(
            max_metadata_size=32 * 1024,  # 32 kilobytes
            max_reconnect_backoff_ms=15000,  # 15.0 seconds
        )

        self._channel = grpc_channel(
            self._address,
            credentials=self._credentials,
            options=options,
            client_type="P4Client",
        )

        self._stub = p4r_grpc.P4RuntimeStub(self._channel)  # type: ignore
        self._schema = schema
        self._complete_request = complete_request

    @TRACE
    async def close(self) -> None:
        "Close the client channel."

        if self._channel is not None:
            LOGGER.debug("P4Client: close channel %r", self._address)

            if self._stream is not None:
                self._stream.cancel()
                self._stream = None

            await self._channel.close()
            self._channel = None
            self._stub = None
            self._schema = None
            self._complete_request = None

    @TRACE
    async def send(self, msg: p4r.StreamMessageRequest) -> None:
        """Send a message to the stream."""
        assert self._stub is not None

        if not self._stream or self._stream.done():
            s: _P4StreamTypeAlias = self._stub.StreamChannel(wait_for_ready=self._wait_for_ready)  # type: ignore
            self._stream = s

        self._log_msg(msg)

        try:
            await self._stream.write(msg)
        except grpc.RpcError as ex:
            raise P4ClientError(ex, "send") from None

    @TRACE
    async def receive(self) -> p4r.StreamMessageResponse:
        """Read a message from the stream."""
        assert self._stream is not None

        try:
            msg = await self._stream.read()
            if msg == GRPC_EOF:
                # Treat EOF as a protocol violation.
                raise RuntimeError("P4Client.receive got EOF!")

        except grpc.RpcError as ex:
            raise P4ClientError(ex, "receive") from None

        self._log_msg(msg)
        return msg

    @overload
    async def request(self, msg: p4r.WriteRequest) -> p4r.WriteResponse:
        ...

    @overload
    async def request(
        self, msg: p4r.GetForwardingPipelineConfigRequest
    ) -> p4r.GetForwardingPipelineConfigResponse:
        ...

    @overload
    async def request(
        self, msg: p4r.SetForwardingPipelineConfigRequest
    ) -> p4r.SetForwardingPipelineConfigResponse:
        ...

    @overload
    async def request(self, msg: p4r.CapabilitiesRequest) -> p4r.CapabilitiesResponse:
        ...

    async def request(self, msg: pbuf.PBMessage) -> pbuf.PBMessage:
        "Send a unary-unary P4Runtime request and wait for the response."

        if self._complete_request:
            self._complete_request(msg)

        msg_type = type(msg).__name__
        assert msg_type.endswith("Request")
        rpc_method = getattr(self._stub, msg_type[:-7])

        self._log_msg(msg)
        try:
            reply = await rpc_method(
                msg,
                timeout=_DEFAULT_RPC_TIMEOUT,
            )
        except grpc.RpcError as ex:
            raise P4ClientError(ex, msg_type, msg=msg) from None

        self._log_msg(reply)
        return reply

    async def request_iter(
        self, msg: p4r.ReadRequest
    ) -> AsyncIterator[p4r.ReadResponse]:
        "Send a unary-stream P4Runtime read request and wait for the responses."

        if self._complete_request:
            self._complete_request(msg)

        msg_type = type(msg).__name__
        assert msg_type.endswith("Request")
        rpc_method = getattr(self._stub, msg_type[:-7])

        self._log_msg(msg)
        try:
            async for reply in rpc_method(
                msg,
                timeout=_DEFAULT_RPC_TIMEOUT,
            ):
                self._log_msg(reply)
                yield reply
        except grpc.RpcError as ex:
            raise P4ClientError(ex, msg_type) from None

    def _log_msg(self, msg: pbuf.PBMessage) -> None:
        "Log a P4Runtime request or response."
        pbuf.log_msg(self._channel, msg, self._schema)
