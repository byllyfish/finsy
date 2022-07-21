import argparse
import asyncio
import logging
from typing import AsyncIterator

import grpc
from finsy.log import LOGGER, TRACE
from finsy.proto import p4r, p4r_grpc


class TaskDict:
    def __init__(self):
        self._tasks = {}

    def start(self, coro):
        name = coro.__qualname__
        i = 0
        while name in self._tasks:
            i += 1
            name = f"{name}#{i}"
        task = asyncio.create_task(coro, name=name)
        self._tasks[name] = task
        task.add_done_callback(self._remove_task)
        return task

    def _remove_task(self, task):
        del self._tasks[task.get_name()]


class P4RuntimeServer(p4r_grpc.P4RuntimeServicer):
    def __init__(self, listen_addr: str, api_version="1.3.0"):
        self.listen_addr = listen_addr
        self._api_version = api_version
        self._server = None
        self._tasks = TaskDict()
        self._stream_context = None
        self._stream_closed = None
        self._stream_queue = asyncio.Queue()

    def __del__(self):
        LOGGER.debug("P4RuntimeServer: destroy server")

    @TRACE
    async def run(self):
        self._server = self._create_server()
        try:
            await self._server.start()
            await asyncio.sleep(5)

            # await self._server.wait_for_termination()
        finally:
            await self._server.stop(0)
            self._server = None

    def _create_server(self):
        server = grpc.aio.server()
        p4r_grpc.add_P4RuntimeServicer_to_server(self, server)  # type: ignore
        server.add_insecure_port(self.listen_addr)
        return server

    @TRACE
    async def StreamChannel(
        self,
        _request_iter,
        context: grpc.aio.ServicerContext,
    ):
        if self._stream_context is not None:
            return "ERROR"

        self._stream_context = context
        self._stream_closed = asyncio.Event()

        read_task = self._tasks.start(self._stream_read())
        write_task = self._tasks.start(self._stream_write())

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

            match request.WhichOneof("update"):  # type: ignore
                case "arbitration":
                    self._tasks.start(self._do_arbitration(request))
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
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
