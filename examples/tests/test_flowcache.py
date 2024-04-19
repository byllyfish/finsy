import asyncio
from pathlib import Path

import testlib

FLOWCACHE_DIR = Path(__file__).parents[1] / "flowcache"

DEMONET = FLOWCACHE_DIR / "net/run.py"


async def test_demo(demonet, python):
    "Test the flowcache/demo example program."
    async with python(FLOWCACHE_DIR / "demo.py") as demo:
        await asyncio.sleep(0.5)
        await demonet.send("h1 ping -c 1 -W .25 h2", expect="100% packet loss")
        await demonet.send("h2 ping -c 1 -W .25 h1", expect="100% packet loss")
        demo.cancel()


async def test_read_tables(demonet):
    "Test the state of the tables after the demo finishes."
    expected_switch_states = {
        "127.0.0.1:50001": {
            "dbgPacketOutHdr NoAction()",
            "debug_egress_stdmeta NoAction()",
            "flow_cache flow_unknown()",
            "flow_cache protocol=0x1 src_addr=0xa000001 dst_addr=0xa000002 cached_action(port=0x3, decrement_ttl=0x1, new_dscp=0x5)",
            "flow_cache protocol=0x1 src_addr=0xa000002 dst_addr=0xa000001 cached_action(port=0x3, decrement_ttl=0x1, new_dscp=0x5)",
            "/clone/0x39 class_of_service=0 510",
        }
    }

    for target, expected_state in expected_switch_states.items():
        actual_state = await testlib.read_p4_tables(target)
        assert actual_state == expected_state, f"{target} failed!"
