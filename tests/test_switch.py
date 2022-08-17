import asyncio
from pathlib import Path

import pytest
from finsy import (
    P4TableAction,
    P4TableEntry,
    P4TableMatch,
    Switch,
    SwitchEvent,
    SwitchOptions,
)
from finsy.log import TRACE


async def test_switch1(p4rt_server_target):
    "Test switch and P4RT server."

    async with Switch("sw1", p4rt_server_target):
        pass


async def test_switch2(p4rt_server_target):
    @TRACE
    async def _read(sw: Switch):
        entry = P4TableEntry(
            "ipv4_lpm",
            match=P4TableMatch(dstAddr=(167772160, 24)),
            action=P4TableAction("ipv4_forward", dstAddr=1108152157446, port=1),
        )
        await sw.insert([entry])

        packet_ins = sw.read_packets()
        async for packet in packet_ins:
            print("test_switch._read", packet)

    options = SwitchOptions(
        p4info=Path("tests/test_data/p4info/basic.p4.p4info.txt"),
    )

    sw1 = Switch("sw1", p4rt_server_target, options)
    sw1.ee.add_listener(SwitchEvent.CHANNEL_UP, _read)  # FIXME: incorrect!

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(sw1.run(), 2.0)


def test_switch3():
    options = SwitchOptions(
        p4info=Path("tests/test_data/p4info/basic.p4.p4info.txt"),
    )

    sw1 = Switch("sw1", "127.0.0.1:19559", options)

    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(asyncio.wait_for(sw1.run(), 2.0))
