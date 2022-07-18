"Implements the gNMIClient class."

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

# pyright: reportPrivateUsage=false

import asyncio
from typing import Any, AsyncIterator, Sequence, TypeAlias

import grpc  # pyright: ignore[reportMissingTypeStubs]

from finsy import pbuf
from finsy.gnmipath import gNMIPath
from finsy.grpcutil import GRPC_EOF, GRPCStatusCode, grpc_channel
from finsy.log import LOGGER, TRACE
from finsy.proto import gnmi, gnmi_grpc


class gNMIClientError(Exception):
    "Wrap grpc.RpcError."

    _code: GRPCStatusCode
    _message: str

    def __init__(self, error: grpc.RpcError):
        super().__init__()
        assert isinstance(error, grpc.aio.AioRpcError)

        self._code = GRPCStatusCode.from_status_code(error.code())
        self._message = error.details() or ""

        LOGGER.debug("gNMI failed: %s", self)

    @property
    def code(self):
        return self._code

    @property
    def message(self):
        return self._message

    @property
    def is_unimplemented(self):
        return self.code == GRPCStatusCode.UNIMPLEMENTED

    def __str__(self) -> str:
        return f"gNMIClientError(code={self.code!r}, message={self.message!r})"


class gNMIClient:
    """Simple read-only GNMI client.

    This client only implements `get` and `subscribe`.

    Basic usage:
    ```
    client = gNMIClient('127.0.0.1:9339')

    path = gNMIPath("interfaces/interface")
    result = await client.get(path)
    print(result)
    ```

    Subscribe to change notifications:
    ```
    path = gNMIPath("interfaces/interface[name=Ethernet1]/state/oper-status")
    sub = client.subscribe()
    sub.on_change(path)

    async for initial_state in sub.synchronize():
        print(initial_state)

    async for update in sub.updates():
        print(update)
    ```
    """

    _address: str
    _credentials: grpc.ChannelCredentials | None
    _channel: grpc.aio.Channel | None = None
    _stub: gnmi_grpc.gNMIStub | None = None
    _channel_reused: bool = False

    def __init__(
        self,
        address: str,
        credentials: grpc.ChannelCredentials | None = None,
    ):
        self._address = address
        self._credentials = credentials

    async def __aenter__(self):
        await self.open()
        return self

    async def __aexit__(self, *_args: Any):
        await self.close()

    @TRACE
    async def open(
        self,
        *,
        channel: grpc.aio.Channel | None = None,
    ) -> None:
        """Open the client channel.

        Note: This method is `async` for forward-compatible reasons.
        """
        assert self._channel is None
        assert self._stub is None

        if channel is not None:
            self._channel = channel
            self._channel_reused = True
        else:
            self._channel = grpc_channel(
                self._address,
                credentials=self._credentials,
                client_type="gNMIClient",
            )

        self._stub = gnmi_grpc.gNMIStub(self._channel)  # type: ignore

    @TRACE
    async def close(self) -> None:
        "Close the client channel."
        if self._channel is not None:
            if not self._channel_reused:
                LOGGER.debug("gNMIClient: close channel %r", self._address)
                await self._channel.close()

            self._channel = None
            self._stub = None
            self._channel_reused = False

    async def get(
        self,
        *path: gNMIPath,
        prefix: gNMIPath | None = None,
        config: bool = False,
    ) -> Sequence[gnmi.Notification]:
        "Retrieve value(s) using a GetRequest."
        assert self._stub is not None

        request = gnmi.GetRequest(
            path=(i.path for i in path),
            encoding=gnmi.Encoding.PROTO,
        )

        if prefix is not None:
            request.prefix.CopyFrom(prefix.path)

        if config:
            request.type = gnmi.GetRequest.CONFIG

        self.log_msg(request)
        try:
            reply: gnmi.GetResponse = await self._stub.Get(request)
        except grpc.RpcError as ex:
            raise gNMIClientError(ex) from None

        self.log_msg(reply)
        return reply.notification

    def subscribe(
        self,
        *,
        prefix: gNMIPath | None = None,
    ) -> "gNMISubscription":
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
        return gNMISubscription(self, prefix)

    async def capabilities(self) -> gnmi.CapabilityResponse:
        "Issue a CapabilitiesRequest."
        assert self._stub is not None

        request = gnmi.CapabilityRequest()

        self.log_msg(request)
        try:
            reply: gnmi.CapabilityResponse = await self._stub.Capabilities(request)
        except grpc.RpcError as ex:
            raise gNMIClientError(ex) from None

        self.log_msg(reply)
        return reply

    def log_msg(self, msg: "pbuf.PBMessage"):
        assert self._channel is not None
        pbuf.log_msg(self._channel.get_state(), msg, None)


_StreamTypeAlias: TypeAlias = grpc.aio.StreamStreamCall[
    gnmi.SubscribeRequest, gnmi.SubscribeResponse
]


class gNMISubscription:
    """Represents a gNMI subscription stream."""

    _client: gNMIClient
    _stream: _StreamTypeAlias | None

    def __init__(self, client: gNMIClient, prefix: gNMIPath | None = None):
        self._client = client
        self._stream = None
        self._sublist = gnmi.SubscriptionList(
            mode=gnmi.SubscriptionList.Mode.STREAM,
        )
        if prefix is not None:
            self._sublist.prefix.CopyFrom(prefix.path)

    def once(self, *paths: gNMIPath):
        self._sublist.mode = gnmi.SubscriptionList.Mode.ONCE

        for path in paths:
            sub = gnmi.Subscription(path=path.path)
            self._sublist.subscription.append(sub)

    def on_change(self, *paths: gNMIPath):
        assert self._sublist.mode == gnmi.SubscriptionList.Mode.STREAM

        for path in paths:
            sub = gnmi.Subscription(
                path=path.path,
                mode=gnmi.SubscriptionMode.ON_CHANGE,
            )
            self._sublist.subscription.append(sub)

    def sample(
        self,
        *paths: gNMIPath,
        sample_interval: int,
        suppress_redundant: bool = False,
        heartbeat_interval: int = 0,
    ):
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

    async def synchronize(self) -> AsyncIterator[gnmi.Notification]:
        await self._subscribe()

        try:
            async for result in self._read(True):
                yield result
        except grpc.RpcError as ex:
            raise gNMIClientError(ex) from None

    async def updates(self) -> AsyncIterator[gnmi.Notification]:
        if self._stream is None:
            await self._subscribe()

        try:
            async for result in self._read(False):
                yield result
        except grpc.RpcError as ex:
            raise gNMIClientError(ex) from None

    def cancel(self):
        if self._stream is not None:
            self._stream.cancel()
            self._stream = None

    async def _subscribe(self):
        assert self._stream is None
        assert self._client._stub is not None

        s: _StreamTypeAlias = self._client._stub.Subscribe(wait_for_ready=True)  # type: ignore
        self._stream = s
        request = gnmi.SubscribeRequest(subscribe=self._sublist)

        self._client.log_msg(request)
        try:
            await self._stream.write(request)
        except grpc.RpcError as ex:
            raise gNMIClientError(ex) from None

    async def _read(self, stop_at_sync: bool) -> AsyncIterator[gnmi.Notification]:
        assert self._stream is not None

        while True:
            msg = await self._stream.read()
            if msg == GRPC_EOF:
                LOGGER.warning("gNMI _read: unexpected EOF")
                return

            self._client.log_msg(msg)

            match msg.WhichOneof("response"):
                case "update":
                    yield msg.update
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
