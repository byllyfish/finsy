"Implements the GNMIClient class."

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

# pyright: reportPrivateUsage=false

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncIterator, Iterator, Sequence, TypeAlias, cast

import grpc  # pyright: ignore[reportMissingTypeStubs]
from typing_extensions import Self

from finsy import pbuf
from finsy.gnmipath import GNMIPath
from finsy.grpcutil import GRPC_EOF, GRPCCredentialsTLS, GRPCStatusCode, grpc_channel
from finsy.log import LOGGER
from finsy.proto import gnmi, gnmi_grpc


class GNMIClientError(Exception):
    "Represents a `grpc.RpcError`."

    _code: GRPCStatusCode
    _message: str

    def __init__(self, error: grpc.RpcError):
        super().__init__()
        assert isinstance(error, grpc.aio.AioRpcError)

        self._code = GRPCStatusCode.from_status_code(error.code())
        self._message = error.details() or ""

        LOGGER.debug("GNMI failed: %s", self)

    @property
    def code(self) -> GRPCStatusCode:
        "GRPC status code."
        return self._code

    @property
    def message(self) -> str:
        "GRPC error message."
        return self._message

    def __str__(self) -> str:
        return f"GNMIClientError(code={self.code!r}, message={self.message!r})"


@dataclass
class GNMIUpdate:
    "Represents a gNMI update returned from GNMIClient."

    timestamp: int
    path: GNMIPath
    typed_value: gnmi.TypedValue | None

    @property
    def value(self) -> Any:
        "Return the value as a Python value."
        if self.typed_value is None:
            return None

        attr = self.typed_value.WhichOneof("value")
        if attr is None:
            raise ValueError("typed_value is not set")
        return getattr(self.typed_value, attr)

    def __repr__(self) -> str:
        "Override repr to strip newline from end of `TypedValue`."
        value = repr(self.typed_value).rstrip()
        return f"GNMIUpdate(timestamp={self.timestamp!r}, path={self.path!r}, typed_value=`{value}`)"


GNMISetValueType = bool | int | float | str | bytes | gnmi.TypedValue


def gnmi_update(
    path: GNMIPath,
    value: GNMISetValueType,
) -> gnmi.Update:
    "Construct a `gnmi.Update` message from path and value."
    match value:
        case gnmi.TypedValue():
            val = value
        case bool():
            val = gnmi.TypedValue(bool_val=value)
        case int():
            # Use uint_val if value is non-negative?
            if value >= 0:
                val = gnmi.TypedValue(uint_val=value)
            else:
                val = gnmi.TypedValue(int_val=value)
        case float():
            val = gnmi.TypedValue(double_val=value)
        case str():
            val = gnmi.TypedValue(string_val=value)
        case bytes():
            val = gnmi.TypedValue(bytes_val=value)
        case _:  # pyright: ignore[reportUnnecessaryComparison]
            raise TypeError(f"unexpected type: {type(value).__name__}")

    return gnmi.Update(path=path.path, val=val)


class GNMIClient:
    """Async GNMI client.

    This client implements `get`, `set`, `subscribe` and `capabilities`.

    The API depends on the protobuf definition of `gnmi.TypedValue`.

    Get usage:
    ```
    client = GNMIClient('127.0.0.1:9339')
    await client.open()

    path = GNMIPath("interfaces/interface")
    async for update in client.get(path):
        print(update)
    ```

    Subscribe usage:
    ```
    path = GNMIPath("interfaces/interface[name=eth1]/state/oper-status")
    sub = client.subscribe()
    sub.on_change(path)

    async for initial_state in sub.synchronize():
        print(initial_state)

    async for update in sub.updates():
        print(update)
    ```

    Set usage:
    ```
    enabled = GNMIPath("interfaces/interface[name=eth1]/config/enabled")

    await client.set(update={
        enabled: gnmi.TypedValue(boolValue=True),
    })
    ```
    """

    _address: str
    _credentials: GRPCCredentialsTLS | None
    _channel: grpc.aio.Channel | None = None
    _stub: gnmi_grpc.gNMIStub | None = None
    _channel_reused: bool = False

    def __init__(
        self,
        address: str,
        credentials: GRPCCredentialsTLS | None = None,
    ):
        self._address = address
        self._credentials = credentials

    async def __aenter__(self) -> Self:
        await self.open()
        return self

    async def __aexit__(self, *_args: Any) -> bool | None:
        await self.close()

    async def open(
        self,
        *,
        channel: grpc.aio.Channel | None = None,
    ) -> None:
        """Open the client channel.

        Note: This method is `async` for forward-compatible reasons.
        """
        if self._channel is not None:
            raise RuntimeError("GNMIClient: client is already open")

        assert self._stub is None

        if channel is not None:
            self._channel = channel
            self._channel_reused = True
        else:
            self._channel = grpc_channel(
                self._address,
                credentials=self._credentials,
                client_type="GNMIClient",
            )

        self._stub = gnmi_grpc.gNMIStub(self._channel)

    async def close(self) -> None:
        "Close the client channel."
        if self._channel is not None:
            if not self._channel_reused:
                LOGGER.debug("GNMIClient: close channel %r", self._address)
                await self._channel.close()

            self._channel = None
            self._stub = None
            self._channel_reused = False

    async def get(
        self,
        *path: GNMIPath,
        prefix: GNMIPath | None = None,
        config: bool = False,
    ) -> Sequence[GNMIUpdate]:
        "Retrieve value(s) using a GetRequest."
        if self._stub is None:
            raise RuntimeError("GNMIClient: client is not open")

        request = gnmi.GetRequest(
            path=(i.path for i in path),
            encoding=gnmi.Encoding.PROTO,
        )

        if prefix is not None:
            request.prefix.CopyFrom(prefix.path)

        if config:
            request.type = gnmi.GetRequest.CONFIG

        self._log_msg(request)
        try:
            reply = cast(
                gnmi.GetResponse,
                await self._stub.Get(request),
            )
        except grpc.RpcError as ex:
            raise GNMIClientError(ex) from None

        self._log_msg(reply)

        result: list[GNMIUpdate] = []
        for notification in reply.notification:
            for update in _read_updates(notification):
                result.append(update)

        return result

    def subscribe(
        self,
        *,
        prefix: GNMIPath | None = None,
    ) -> "GNMISubscription":
        """Subscribe to gNMI change notifications.

        Usage:
        ```
        sub = client.subscribe()
        sub.on_change(path1, ...)
        sub.sample(path3, path4, sample_interval=1000000000)

        async for update in sub.synchronize():
            # do something with initial state

        async for update in sub.updates():
            # do something with updates
        ```

        You can also subscribe in "ONCE" mode:
        ```
        sub = client.subscribe()
        sub.once(path1, path2, ...)

        async for info in sub.synchronize():
            # do something with info
        ```

        The subscription object is not re-entrant, but a fully consumed
        subscription may be reused.
        """
        if self._stub is None:
            raise RuntimeError("GNMIClient: client is not open")

        return GNMISubscription(self, prefix)

    async def capabilities(self) -> gnmi.CapabilityResponse:
        "Issue a CapabilitiesRequest."
        if self._stub is None:
            raise RuntimeError("GNMIClient: client is not open")

        request = gnmi.CapabilityRequest()

        self._log_msg(request)
        try:
            reply = cast(
                gnmi.CapabilityResponse,
                await self._stub.Capabilities(request),
            )
        except grpc.RpcError as ex:
            raise GNMIClientError(ex) from None

        self._log_msg(reply)
        return reply

    async def set(
        self,
        *,
        update: Sequence[tuple[GNMIPath, GNMISetValueType]] | None = None,
        replace: Sequence[tuple[GNMIPath, GNMISetValueType]] | None = None,
        delete: Sequence[GNMIPath] | None = None,
        prefix: GNMIPath | None = None,
    ) -> int:
        """Set value(s) using SetRequest.

        Returns the timestamp from the successful `SetResponse`.
        """
        if self._stub is None:
            raise RuntimeError("GNMIClient: client is not open")

        if update is not None:
            updates = [gnmi_update(path, value) for path, value in update]
        else:
            updates = None

        if replace is not None:
            replaces = [gnmi_update(path, value) for path, value in replace]
        else:
            replaces = None

        if delete is not None:
            deletes = [path.path for path in delete]
        else:
            deletes = None

        request = gnmi.SetRequest(
            update=updates,
            replace=replaces,
            delete=deletes,
        )

        if prefix is not None:
            request.prefix.CopyFrom(prefix.path)

        self._log_msg(request)
        try:
            reply = cast(
                gnmi.SetResponse,
                await self._stub.Set(request),
            )
        except grpc.RpcError as ex:
            raise GNMIClientError(ex) from None

        self._log_msg(reply)

        # According to the comments in the current protobuf, I expect all error
        # results to be raised as an exception. The only useful value in a
        # successful response is the timestamp.

        if reply.HasField("message"):
            raise NotImplementedError("SetResponse error not supported")

        for result in reply.response:
            if result.HasField("message"):
                raise NotImplementedError("SetResponse suberror not supported")

        return reply.timestamp

    def _log_msg(self, msg: "pbuf.PBMessage"):
        "Log a gNMI message."
        pbuf.log_msg(self._channel, msg, None)


_StreamTypeAlias: TypeAlias = grpc.aio.StreamStreamCall[
    gnmi.SubscribeRequest, gnmi.SubscribeResponse
]


class GNMISubscription:
    """Represents a gNMI subscription stream.

    Returned from `GNMIClient.subscribe()`.
    """

    _client: GNMIClient
    _stream: _StreamTypeAlias | None

    def __init__(self, client: GNMIClient, prefix: GNMIPath | None = None):
        "Initialize a GNMISubscription."
        self._client = client
        self._stream = None
        self._sublist = gnmi.SubscriptionList(
            mode=gnmi.SubscriptionList.Mode.STREAM,
        )
        if prefix is not None:
            self._sublist.prefix.CopyFrom(prefix.path)

    def once(self, *paths: GNMIPath) -> None:
        "Subscribe in `ONCE` mode to given paths."
        self._sublist.mode = gnmi.SubscriptionList.Mode.ONCE

        for path in paths:
            sub = gnmi.Subscription(path=path.path)
            self._sublist.subscription.append(sub)

    def on_change(self, *paths: GNMIPath) -> None:
        "Subscribe in `ON_CHANGE` mode to given paths."
        assert self._sublist.mode == gnmi.SubscriptionList.Mode.STREAM

        for path in paths:
            sub = gnmi.Subscription(
                path=path.path,
                mode=gnmi.SubscriptionMode.ON_CHANGE,
            )
            self._sublist.subscription.append(sub)

    def sample(
        self,
        *paths: GNMIPath,
        sample_interval: int,
        suppress_redundant: bool = False,
        heartbeat_interval: int = 0,
    ) -> None:
        "Subscribe in `SAMPLE` mode to given paths."
        assert self._sublist.mode == gnmi.SubscriptionList.Mode.STREAM

        for path in paths:
            sub = gnmi.Subscription(
                path=path.path,
                mode=gnmi.SubscriptionMode.SAMPLE,
                sample_interval=sample_interval,
                suppress_redundant=suppress_redundant,
                heartbeat_interval=heartbeat_interval,
            )
            self._sublist.subscription.append(sub)

    async def synchronize(self) -> AsyncIterator[GNMIUpdate]:
        """Async iterator for initial subscription updates.

        Retrieve all updates up to `sync_response` message.
        """
        if self._stream is None:
            await self._subscribe()

        try:
            async for result in self._read(True):
                yield result
        except grpc.RpcError as ex:
            raise GNMIClientError(ex) from None

    async def updates(self) -> AsyncIterator[GNMIUpdate]:
        "Async iterator for all remaining subscription updates."
        if self._stream is None:
            await self._subscribe()

        try:
            async for result in self._read(False):
                yield result
        except grpc.RpcError as ex:
            raise GNMIClientError(ex) from None

    def cancel(self) -> None:
        "Cancel the subscription."
        if self._stream is not None:
            self._stream.cancel()
            self._stream = None

    async def _subscribe(self):
        assert self._stream is None
        assert self._client._stub is not None

        self._stream = cast(
            _StreamTypeAlias,
            self._client._stub.Subscribe(wait_for_ready=True),  # type: ignore
        )

        request = gnmi.SubscribeRequest(subscribe=self._sublist)
        self._client._log_msg(request)
        try:
            await self._stream.write(request)
        except grpc.RpcError as ex:
            raise GNMIClientError(ex) from None

    async def _read(self, stop_at_sync: bool) -> AsyncIterator[GNMIUpdate]:
        assert self._stream is not None

        while True:
            msg = cast(
                gnmi.SubscribeResponse,
                await self._stream.read(),  # type: ignore
            )
            if msg is GRPC_EOF:
                LOGGER.warning("gNMI _read: unexpected EOF")
                return

            self._client._log_msg(msg)

            match msg.WhichOneof("response"):
                case "update":
                    for update in _read_updates(msg.update):
                        yield update
                case "sync_response":
                    if stop_at_sync:
                        if self._is_once():
                            # FIXME? I expected Stratum to issue an EOF after
                            # the sync_response in "ONCE" mode, but it doesn't.
                            # For now, cancel the stream explictly.
                            self.cancel()
                            # Let grpc react to the cancellation immediately.
                            await asyncio.sleep(0)
                        return  # All done!
                    LOGGER.warning("gNMI _read: ignored sync_response")
                case other:
                    LOGGER.warning("gNMI _read: unexpected oneof: %s", other)

    def _is_once(self) -> bool:
        "Return true if the subscription is in ONCE mode."
        return self._sublist.mode == gnmi.SubscriptionList.Mode.ONCE


def _read_updates(notification: gnmi.Notification) -> Iterator[GNMIUpdate]:
    "Generator to retrieve all updates from a notification."
    for update in notification.update:
        yield GNMIUpdate(
            timestamp=notification.timestamp,
            path=GNMIPath(update.path),
            typed_value=update.val,
        )

    for delete in notification.delete:
        yield GNMIUpdate(
            timestamp=notification.timestamp,
            path=GNMIPath(delete),
            typed_value=None,
        )
