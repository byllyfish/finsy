import asyncio
from pathlib import Path

import finsy as fy

L2SWITCH_DIR = Path(__file__).parent.parent / "l2_switch"

DEMONET = L2SWITCH_DIR / "demonet/run.sh"


async def test_demo(demonet, python):
    "Test the l2_switch/demo example program."

    async with python(L2SWITCH_DIR / "demo.py") as demo:
        await asyncio.sleep(0.25)
        await demonet.send("pingall", expect="(6/6 received)")
        demo.cancel()


async def test_read_tables(demonet):
    "Test the state of the tables after the demo finishes."

    expected_switch_states = {
        "127.0.0.1:50001": {
            "smac srcAddr=0x1 NoAction()",
            "smac srcAddr=0x2 NoAction()",
            "smac srcAddr=0x3 NoAction()",
            "dmac dstAddr=0x1 fwd(eg_port=0x1)",
            "dmac dstAddr=0x2 fwd(eg_port=0x2)",
            "dmac dstAddr=0x3 fwd(eg_port=0x2)",
        },
        "127.0.0.1:50002": {
            "smac srcAddr=0x1 NoAction()",
            "smac srcAddr=0x2 NoAction()",
            "smac srcAddr=0x3 NoAction()",
            "dmac dstAddr=0x1 fwd(eg_port=0x2)",
            "dmac dstAddr=0x2 fwd(eg_port=0x1)",
            "dmac dstAddr=0x3 fwd(eg_port=0x3)",
        },
        "127.0.0.1:50003": {
            "smac srcAddr=0x1 NoAction()",
            "smac srcAddr=0x2 NoAction()",
            "smac srcAddr=0x3 NoAction()",
            "dmac dstAddr=0x1 fwd(eg_port=0x2)",
            "dmac dstAddr=0x2 fwd(eg_port=0x2)",
            "dmac dstAddr=0x3 fwd(eg_port=0x1)",
        },
    }

    for target, expected_state in expected_switch_states.items():
        actual_state = await _read_tables(target)
        # At a minimum, the actual state should be the expected state.
        # Ignore additional host address noise.
        assert actual_state >= expected_state


async def _read_tables(target) -> set[str]:
    "Read all table entries from the P4Runtime switch."
    result = set()

    async with fy.Switch("sw", target) as sw:
        with sw.p4info:
            async for entry in sw.read([fy.P4TableEntry()]):
                result.add(
                    f"{entry.table_id} {entry.match_str(wildcard='*')} {entry.action_str()}"
                )

    return result
