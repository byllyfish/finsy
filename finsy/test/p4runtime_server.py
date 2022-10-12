import argparse
import asyncio
import contextlib
import logging
from typing import AsyncIterator

import grpc
from finsy.futures import wait_for_cancel
from finsy.log import LOGGER, TRACE
from finsy.proto import p4r, p4r_grpc


class _TaskSet(set[asyncio.Task]):
    def create_task(self, coro):
        task = asyncio.create_task(coro)
        self.add(task)
        task.add_done_callback(self.discard)
        return task


class P4RuntimeServer(p4r_grpc.P4RuntimeServicer):
    "Test P4Runtime server."

    _listen_addr: str
    _api_version: str

    def __init__(self, listen_addr: str, api_version: str = "1.3.0"):
        "Initialize P4Runtime server."

        self._listen_addr = listen_addr
        self._api_version = api_version
        self._server = None
        self._tasks = _TaskSet()
        self._stream_context = None
        self._stream_closed = None
        self._stream_queue = asyncio.Queue()

    def __del__(self):
        LOGGER.debug("P4RuntimeServer: destroy server")

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
        server.add_insecure_port(self._listen_addr)
        return server

    @TRACE
    async def StreamChannel(
        self,
        _request_iter,
        context: grpc.aio.ServicerContext,
    ):
        "Handle StreamChannel."

        # If another stream RPC is already open, return an error.
        if self._stream_context is not None:
            LOGGER.warning("P4RuntimeServer: Multiple clients not implemented")
            await context.abort(
                grpc.StatusCode.UNIMPLEMENTED,
                "Multiple clients not implemented",
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

    @TRACE
    async def _stream_read(self):
        assert self._stream_context is not None

        while True:
            try:
                request = await self._stream_context.read()
            except Exception as ex:
                LOGGER.debug("_stream_read ex=%r", ex)
                request = grpc.aio.EOF

            if request == grpc.aio.EOF:
                LOGGER.debug("_stream_read EOF")
                assert self._stream_closed is not None
                self._stream_closed.set()
                self._stream_context = None
                return

            match request.WhichOneof("update"):
                case "arbitration":
                    self._tasks.create_task(self._do_arbitration(request))
                case kind:
                    LOGGER.debug("_stream_read: unknown message %r", kind)

    @TRACE
    async def _stream_write(self):
        assert self._stream_context is not None
        # Only one write() at a time. Otherwise GRPC raises an ExecuteBatchError.
        while True:
            response = await self._stream_queue.get()
            await self._stream_context.write(response)

    @TRACE
    async def _do_arbitration(self, request: p4r.StreamMessageRequest):
        response = p4r.StreamMessageResponse(arbitration=request.arbitration)
        await asyncio.sleep(0.5)
        self._send(response)

        await asyncio.sleep(0.5)
        self._send_test_packet()

    def _send(self, response):
        self._stream_queue.put_nowait(response)

    def _send_test_packet(self):
        response = p4r.StreamMessageResponse(packet=p4r.PacketIn(payload=b"abcdef"))
        self._send(response)

    @TRACE
    async def Capabilities(
        self,
        request: p4r.CapabilitiesRequest,
        context: grpc.aio.ServicerContext,
    ) -> p4r.CapabilitiesResponse:
        return p4r.CapabilitiesResponse(p4runtime_api_version=self._api_version)

    @TRACE
    async def GetForwardingPipelineConfig(
        self,
        request: p4r.GetForwardingPipelineConfigRequest,
        context: grpc.aio.ServicerContext,
    ) -> p4r.GetForwardingPipelineConfigResponse:
        return p4r.GetForwardingPipelineConfigResponse(
            config=p4r.ForwardingPipelineConfig()
        )

    @TRACE
    async def SetForwardingPipelineConfig(
        self,
        request: p4r.SetForwardingPipelineConfigRequest,
        context: grpc.aio.ServicerContext,
    ) -> p4r.SetForwardingPipelineConfigResponse:
        return p4r.SetForwardingPipelineConfigResponse()

    @TRACE
    async def Read(
        self,
        request: p4r.ReadRequest,
        context: grpc.aio.ServicerContext,
    ) -> AsyncIterator[p4r.ReadResponse]:
        # TODO: fix response
        yield p4r.ReadResponse()

    @TRACE
    async def Write(
        self,
        request: p4r.WriteRequest,
        context: grpc.aio.ServicerContext,
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


async def main():
    args = _parse_args()
    logging.basicConfig(level=logging.DEBUG)

    server = P4RuntimeServer(f"localhost:{args.port}")
    async with server.run():
        await wait_for_cancel()


if __name__ == "__main__":
    asyncio.run(main())
