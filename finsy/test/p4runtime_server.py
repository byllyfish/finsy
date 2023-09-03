"P4Runtime server for testing."

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

import argparse
import asyncio
import contextlib
import logging
from typing import Any, AsyncIterator, Coroutine, TypeVar

import grpc  # pyright: ignore[reportMissingTypeStubs]

from finsy.futures import wait_for_cancel
from finsy.grpcutil import GRPC_EOF, GRPCCredentialsTLS
from finsy.log import LOGGER
from finsy.proto import p4r, p4r_grpc

# FIXME: This module is not strictly typed yet.
# pyright: reportUnknownMemberType=false, reportIncompatibleMethodOverride=false
# pylint: disable=invalid-overridden-method

_T = TypeVar("_T")


class _TaskSet(set[asyncio.Task[_T]]):
    "Keep fire-and-forget Tasks alive while task is running."

    def create_task(self, coro: Coroutine[Any, Any, _T]) -> asyncio.Task[_T]:
        "Create a task and maintain refcount while it is running."
        task = asyncio.create_task(coro)
        self.add(task)
        task.add_done_callback(self.discard)
        return task


class P4RuntimeServer(p4r_grpc.P4RuntimeServicer):
    "Test P4Runtime server."

    _listen_addr: str
    _api_version: str
    _tasks: _TaskSet[Any]
    _stream_queue: asyncio.Queue[p4r.StreamMessageResponse]
    _credentials: GRPCCredentialsTLS | None

    def __init__(
        self,
        listen_addr: str,
        api_version: str = "1.3.0",
        credentials: GRPCCredentialsTLS | None = None,
    ):
        "Initialize P4Runtime server."
        LOGGER.debug("P4RuntimeServer: init server: %s", listen_addr)
        self._listen_addr = listen_addr
        self._api_version = api_version
        self._server = None
        self._tasks = _TaskSet()
        self._stream_context = None
        self._stream_closed = None
        self._stream_queue = asyncio.Queue()
        self._credentials = credentials

    def __del__(self) -> None:
        LOGGER.debug("P4RuntimeServer: destroy server: %s", self._listen_addr)

    @contextlib.asynccontextmanager
    async def run(self):
        "Run server inside an async context manager."
        self._server = self._create_server()
        try:
            await self._server.start()
            yield self

        finally:
            for task in self._tasks:
                task.cancel()
            await self._server.stop(0)
            self._server = None

    def _create_server(self) -> grpc.aio.Server:
        "Create AIO server."
        server = grpc.aio.server()
        p4r_grpc.add_P4RuntimeServicer_to_server(self, server)
        if self._credentials is None:
            LOGGER.debug(
                "P4RuntimeServer: create insecure server: %s", self._listen_addr
            )
            server.add_insecure_port(self._listen_addr)
        else:
            LOGGER.debug("P4RuntimeServer: create secure server: %s", self._listen_addr)
            server.add_secure_port(
                self._listen_addr,
                self._credentials.to_server_credentials(),
            )
        return server

    async def StreamChannel(
        self,
        _request_iter: AsyncIterator[p4r.StreamMessageRequest],
        context: grpc.aio.ServicerContext[
            p4r.StreamMessageRequest, p4r.StreamMessageResponse
        ],
    ) -> None:
        "Handle StreamChannel."
        # If another stream RPC is already open, return an error.
        if self._stream_context is not None:
            LOGGER.warning(
                "P4RuntimeServer: Multiple clients not implemented in TEST server"
            )
            await context.abort(
                grpc.StatusCode.UNIMPLEMENTED,
                "Multiple clients not implemented in TEST server",
            )

        self._stream_context = context
        self._stream_closed = asyncio.Event()

        read_task = self._tasks.create_task(self._stream_read())
        write_task = self._tasks.create_task(self._stream_write())

        try:
            await self._stream_closed.wait()

        finally:
            read_task.cancel()
            write_task.cancel()
            await asyncio.wait([read_task, write_task])

    async def _stream_read(self):
        assert self._stream_context is not None

        while True:
            try:
                request = await self._stream_context.read()
            except Exception as ex:
                LOGGER.debug("_stream_read ex=%r", ex)
                request = GRPC_EOF

            if request is GRPC_EOF:
                LOGGER.debug("_stream_read EOF")
                assert self._stream_closed is not None
                self._stream_closed.set()
                self._stream_context = None
                return

            assert isinstance(request, p4r.StreamMessageRequest)

            match request.WhichOneof("update"):
                case "arbitration":
                    self._tasks.create_task(self._do_arbitration(request))
                case kind:
                    LOGGER.debug("_stream_read: unknown message %r", kind)

    async def _stream_write(self):
        assert self._stream_context is not None
        # Only one write() at a time. Otherwise GRPC raises an ExecuteBatchError.
        while True:
            response = await self._stream_queue.get()
            await self._stream_context.write(response)

    async def _do_arbitration(self, request: p4r.StreamMessageRequest):
        response = p4r.StreamMessageResponse(arbitration=request.arbitration)
        await asyncio.sleep(0.5)
        self._send(response)

        await asyncio.sleep(0.5)
        self._send_test_packet()

    def _send(self, response: p4r.StreamMessageResponse):
        self._stream_queue.put_nowait(response)

    def _send_test_packet(self):
        response = p4r.StreamMessageResponse(packet=p4r.PacketIn(payload=b"abcdef"))
        self._send(response)

    async def Capabilities(
        self,
        request: p4r.CapabilitiesRequest,
        context: grpc.aio.ServicerContext[
            p4r.CapabilitiesRequest, p4r.CapabilitiesResponse
        ],
    ) -> p4r.CapabilitiesResponse:
        metadata = context.invocation_metadata()
        if metadata:
            for datum in metadata:
                if not datum[0].startswith("x-"):
                    continue
                LOGGER.debug(f"Server request with x-metadata: {datum!r}")
        return p4r.CapabilitiesResponse(p4runtime_api_version=self._api_version)

    async def GetForwardingPipelineConfig(
        self,
        request: p4r.GetForwardingPipelineConfigRequest,
        context: grpc.aio.ServicerContext[
            p4r.GetForwardingPipelineConfigRequest,
            p4r.GetForwardingPipelineConfigResponse,
        ],
    ) -> p4r.GetForwardingPipelineConfigResponse:
        return p4r.GetForwardingPipelineConfigResponse(
            config=p4r.ForwardingPipelineConfig()
        )

    async def SetForwardingPipelineConfig(
        self,
        request: p4r.SetForwardingPipelineConfigRequest,
        context: grpc.aio.ServicerContext[
            p4r.SetForwardingPipelineConfigRequest,
            p4r.SetForwardingPipelineConfigResponse,
        ],
    ) -> p4r.SetForwardingPipelineConfigResponse:
        return p4r.SetForwardingPipelineConfigResponse()

    async def Read(
        self,
        request: p4r.ReadRequest,
        context: grpc.aio.ServicerContext[p4r.ReadRequest, p4r.ReadResponse],
    ) -> AsyncIterator[p4r.ReadResponse]:
        # TODO: fix response
        yield p4r.ReadResponse()

    async def Write(
        self,
        request: p4r.WriteRequest,
        context: grpc.aio.ServicerContext[p4r.WriteRequest, p4r.WriteResponse],
    ) -> p4r.WriteResponse:
        return p4r.WriteResponse()


def _parse_args():
    "Parse command line arguments."
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--port",
        type=int,
        default=9559,
        help="TCP listen port number",
    )
    return parser.parse_args()


async def _main():
    args = _parse_args()
    logging.basicConfig(level=logging.DEBUG)

    server = P4RuntimeServer(f"localhost:{args.port}")
    async with server.run():
        await wait_for_cancel()


if __name__ == "__main__":
    asyncio.run(_main())
