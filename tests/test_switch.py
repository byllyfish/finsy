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
from finsy.proto import stratum
from finsy.switch import ApiVersion


async def test_switch1(p4rt_server_target: str):
    "Test switch and P4RT server."
    async with Switch("sw1", p4rt_server_target) as sw1:
        assert sw1.is_up
        assert sw1.device_id == 1
        assert sw1.election_id == 10
        assert sw1.primary_id == 10
        assert sw1.is_primary
        assert sw1.gnmi_client is None

        with pytest.raises(RuntimeError, match="client is open"):
            sw1.options = SwitchOptions(device_id=2)

    sw1.options = SwitchOptions(device_id=3)
    assert sw1.device_id == 3


async def test_switch2(p4rt_server_target: str):
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
    sw1.ee.add_listener(SwitchEvent.CHANNEL_READY, _read)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(sw1.run(), 2.0)


def test_switch3(unused_tcp_target: str):
    "Test switch with unavailable TCP server."
    options = SwitchOptions(
        p4info=Path("tests/test_data/p4info/basic.p4.p4info.txt"),
    )

    sw1 = Switch("sw1", unused_tcp_target, options)

    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(asyncio.wait_for(sw1.run(), 2.0))


async def test_switch4(p4rt_server_target: str):
    "Test switch and P4RT server with custom role."
    options = SwitchOptions(
        p4info=Path("tests/test_data/p4info/basic.p4.p4info.txt"),
        role_name="role1",
        role_config=stratum.P4RoleConfig(receives_packet_ins=True),
    )

    async with Switch("sw1", p4rt_server_target, options):
        await asyncio.sleep(0.01)


def test_switch_options():
    "Test the SwitchOptions class."
    some_path = Path("/")
    opts = SwitchOptions(
        p4info=some_path,
        p4blob=some_path,
        p4force=True,
        device_id=23,
        initial_election_id=9,
        channel_credentials=None,
        role_name="some_role",
        role_config=None,
        ready_handler=None,
        fail_fast=True,
        configuration={},
    )
    assert opts.p4info == some_path
    assert opts.device_id == 23

    opts1 = opts(device_id=100)
    assert opts1 != opts
    assert opts1.device_id == 100

    opts2 = opts1(device_id=23)
    assert opts2 != opts1
    assert opts2 == opts and opts2 is not opts


def test_api_version():
    "Test the internal ApiVersion class (currently defined in switch.py)."
    assert ApiVersion.parse("0.9") == ApiVersion(0, 9, 0, "")
    assert ApiVersion.parse("0.9.a") == ApiVersion(0, 9, 0, ".a")
    assert ApiVersion.parse("0.9.9f") == ApiVersion(0, 9, 9, "f")
    assert ApiVersion.parse("1.2") == ApiVersion(1, 2, 0, "")
    assert ApiVersion.parse("1.2.3") == ApiVersion(1, 2, 3, "")
    assert ApiVersion.parse("1.2.3+4") == ApiVersion(1, 2, 3, "+4")
    assert ApiVersion.parse("1.2.3-final") == ApiVersion(1, 2, 3, "-final")
    assert ApiVersion.parse("1.2.3.4") == ApiVersion(1, 2, 3, ".4")
    assert ApiVersion.parse(" 1.2.3 ") == ApiVersion(1, 2, 3, "")

    with pytest.raises(ValueError):
        ApiVersion.parse("1.")

    assert str(ApiVersion(1, 2, 3, "-abc")) == "1.2.3-abc"
