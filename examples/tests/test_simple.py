import asyncio
from pathlib import Path

import pytest
import testlib

import finsy as fy
from finsy import pbuf

SIMPLE_DIR = Path(__file__).parent.parent / "simple"

DEMONET = SIMPLE_DIR / "demonet/run.sh"


async def test_demo(demonet, python):
    "Test the simple/demo example program."
    await python(SIMPLE_DIR / "demo.py")
    await demonet.send("pingall", expect="(2/2 received)")
    await demonet.send("iperf", expect="Mbits/sec")


async def test_read_tables(demonet):
    "Test the state of the tables after the demo finishes."
    expected_switch_states = {
        "127.0.0.1:50001": {
            "forward ingress._drop()",
            "send_frame egress._drop()",
            "ipv4_lpm ingress._drop()",
            "send_frame egress_port=0x2 rewrite_mac(smac=0xaabbcc)",
            "send_frame egress_port=0x1 rewrite_mac(smac=0xaabbcc)",
            "forward nhop_ipv4=0xa00020a set_dmac(dmac=0x2)",
            "forward nhop_ipv4=0xa00010a set_dmac(dmac=0x1)",
            "ipv4_lpm dstAddr=0xa00010a set_nhop(nhop_ipv4=0xa00010a, port=0x1)",
            "ipv4_lpm dstAddr=0xa00020a set_nhop(nhop_ipv4=0xa00020a, port=0x2)",
        }
    }

    for target, expected_state in expected_switch_states.items():
        actual_state = await testlib.read_p4_tables(target)
        assert actual_state == expected_state


async def test_too_many_entries(demonet):
    "Test sending 1025 entries to a table that only support 1024."
    entries = [
        +fy.P4TableEntry(
            "ipv4_lpm",
            match=fy.P4TableMatch(dstAddr=i),
            action=fy.P4TableAction("set_nhop", nhop_ipv4=1, port=2),
        )
        for i in range(1025)
    ]

    async with fy.Switch("sw", "127.0.0.1:50001") as sw:
        await sw.delete_all()
        with pytest.raises(fy.P4ClientError) as exinfo:
            await sw.write(entries)

        # Check that INSERT failed for 1025'th entry.
        ex = exinfo.value
        assert ex.code == fy.GRPCStatusCode.UNKNOWN
        assert len(ex.details) == 1
        assert pbuf.to_dict(ex.details[1024].subvalue) == {
            "type": "INSERT",
            "entity": {
                "table_entry": {
                    "table_id": 43030458,
                    "match": [
                        {"field_id": 1, "lpm": {"value": "BAA=", "prefix_len": 32}}
                    ],
                    "action": {
                        "action": {
                            "action_id": 29239084,
                            "params": [
                                {"param_id": 1, "value": "AQ=="},
                                {"param_id": 2, "value": "Ag=="},
                            ],
                        }
                    },
                }
            },
        }
