import asyncio
from pathlib import Path

import pytest
import testlib

# All tests run in the "module" event loop.
pytestmark = pytest.mark.asyncio(loop_scope="module")

BASIC_DIR = Path(__file__).parents[1] / "basic"

DEMONET = BASIC_DIR / "net/run.py"


async def test_demo(demonet, python):
    "Test the basic/demo example program."
    async with python(BASIC_DIR / "demo.py") as demo:
        await asyncio.sleep(0.5)
        await demonet.send("pingall", expect="(12/12 received)")
        raise asyncio.CancelledError()


async def test_read_tables(demonet):
    "Test the state of the tables after the demo finishes."
    expected_switch_states = {
        "127.0.0.1:50001": {
            "ipv4_lpm drop()",
            "ipv4_lpm dstAddr=0xa000101 ipv4_forward(dstAddr=0x80000000111, port=0x1)",
            "ipv4_lpm dstAddr=0xa000202 ipv4_forward(dstAddr=0x80000000222, port=0x2)",
            "ipv4_lpm dstAddr=0xa000303 ipv4_forward(dstAddr=0x80000000300, port=0x3)",
            "ipv4_lpm dstAddr=0xa000404 ipv4_forward(dstAddr=0x80000000400, port=0x4)",
        },
        "127.0.0.1:50002": {
            "ipv4_lpm drop()",
            "ipv4_lpm dstAddr=0xa000101 ipv4_forward(dstAddr=0x80000000300, port=0x4)",
            "ipv4_lpm dstAddr=0xa000202 ipv4_forward(dstAddr=0x80000000400, port=0x3)",
            "ipv4_lpm dstAddr=0xa000303 ipv4_forward(dstAddr=0x80000000333, port=0x1)",
            "ipv4_lpm dstAddr=0xa000404 ipv4_forward(dstAddr=0x80000000444, port=0x2)",
        },
        "127.0.0.1:50003": {
            "ipv4_lpm drop()",
            "ipv4_lpm dstAddr=0xa000101 ipv4_forward(dstAddr=0x80000000100, port=0x1)",
            "ipv4_lpm dstAddr=0xa000202 ipv4_forward(dstAddr=0x80000000100, port=0x1)",
            "ipv4_lpm dstAddr=0xa000303 ipv4_forward(dstAddr=0x80000000200, port=0x2)",
            "ipv4_lpm dstAddr=0xa000404 ipv4_forward(dstAddr=0x80000000200, port=0x2)",
        },
        "127.0.0.1:50004": {
            "ipv4_lpm drop()",
            "ipv4_lpm dstAddr=0xa000101 ipv4_forward(dstAddr=0x80000000100, port=0x1)",
            "ipv4_lpm dstAddr=0xa000202 ipv4_forward(dstAddr=0x80000000100, port=0x1)",
            "ipv4_lpm dstAddr=0xa000303 ipv4_forward(dstAddr=0x80000000200, port=0x2)",
            "ipv4_lpm dstAddr=0xa000404 ipv4_forward(dstAddr=0x80000000200, port=0x2)",
        },
    }

    for target, expected_state in expected_switch_states.items():
        actual_state = await testlib.read_p4_tables(target)
        assert actual_state == expected_state, f"{target} failed!"
