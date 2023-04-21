import asyncio
from pathlib import Path

import testlib

L2SWITCH_DIR = Path(__file__).parent.parent / "l2_switch"

DEMONET = L2SWITCH_DIR / "net/run.py"


async def test_demo(demonet, python):
    "Test the l2_switch/demo example program."
    async with python(L2SWITCH_DIR / "demo.py") as demo:
        await asyncio.sleep(0.25)
        await demonet.send("pingall", expect="(6/6 received)")
        demo.cancel()


async def test_read_tables(demonet):
    "Test the state of the tables after the demo finishes."
    # FIXME: bmv2 switch doesn't return default entries?
    expected_switch_states = {
        "127.0.0.1:50001": {
            "smac srcAddr=0x1 NoAction()",
            "smac srcAddr=0x2 NoAction()",
            "smac srcAddr=0x3 NoAction()",
            "smac learn_mac()",
            "dmac dstAddr=0x1 fwd(eg_port=0x1)",
            "dmac dstAddr=0x2 fwd(eg_port=0x2)",
            "dmac dstAddr=0x3 fwd(eg_port=0x2)",
            "dmac broadcast(mgrp=0xab)",
        },
        "127.0.0.1:50002": {
            "smac srcAddr=0x1 NoAction()",
            "smac srcAddr=0x2 NoAction()",
            "smac srcAddr=0x3 NoAction()",
            "smac learn_mac()",
            "dmac dstAddr=0x1 fwd(eg_port=0x2)",
            "dmac dstAddr=0x2 fwd(eg_port=0x1)",
            "dmac dstAddr=0x3 fwd(eg_port=0x3)",
            "dmac broadcast(mgrp=0xab)",
        },
        "127.0.0.1:50003": {
            "smac srcAddr=0x1 NoAction()",
            "smac srcAddr=0x2 NoAction()",
            "smac srcAddr=0x3 NoAction()",
            "smac learn_mac()",
            "dmac dstAddr=0x1 fwd(eg_port=0x2)",
            "dmac dstAddr=0x2 fwd(eg_port=0x2)",
            "dmac dstAddr=0x3 fwd(eg_port=0x1)",
            "dmac broadcast(mgrp=0xab)",
        },
    }

    for target, expected_state in expected_switch_states.items():
        actual_state = await testlib.read_p4_tables(target)
        assert actual_state == expected_state
