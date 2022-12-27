import asyncio
from pathlib import Path

import testlib

import finsy as fy

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
