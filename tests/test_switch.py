import asyncio
import contextlib
from pathlib import Path

import pytest
from finsy import Switch, SwitchOptions
from finsy.log import TRACE
from finsy.test.p4runtime_server import P4RuntimeServer


@pytest.fixture
async def p4rt_server():
    server = P4RuntimeServer("127.0.0.1:19559")
    task = asyncio.create_task(server.run())
    yield server

    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


async def test_switch(p4rt_server):
    @TRACE
    async def _read(sw):
        packet_ins = sw.packet_iterator()
        async for packet in packet_ins:
            print("test_switch._read", packet)

    options = SwitchOptions(
        p4info=Path("tests/test_data/p4info/basic.p4.p4info.txt"),
    )

    sw1 = Switch("sw1", p4rt_server.listen_addr, options)
    sw1.ee.add_listener("channel_up", _read)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(sw1.run(), 2.0)


def test_switch2():
    options = SwitchOptions(
        p4info=Path("tests/test_data/p4info/basic.p4.p4info.txt"),
    )

    sw1 = Switch("sw1", "127.0.0.1:19559", options)

    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(asyncio.wait_for(sw1.run(), 2.0))
