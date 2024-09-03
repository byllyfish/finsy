from pathlib import Path

import pytest
import testlib

# All tests run in the "module" event loop.
pytestmark = pytest.mark.asyncio(loop_scope="module")

TUNNEL_DIR = Path(__file__).parents[1] / "tunnel"

DEMONET = TUNNEL_DIR / "net/run.py"


async def test_demo(demonet, python):
    "Test the tunnel/demo1 example program."
    await python(TUNNEL_DIR / "demo1.py")
    await demonet.send("h1 ping -c 3 h2", expect=" 0% packet loss")
    await demonet.send("h2 ping -c 3 h1", expect=" 0% packet loss")


async def test_read_tables(demonet):
    "Test the state of the tables after the demo finishes."
    expected_switch_states = {
        "127.0.0.1:50001": {
            "ipv4_lpm dstAddr=0xa000202 myTunnel_ingress(dst_id=0xc8)",
            "ipv4_lpm NoAction()",
            "myTunnel_exact dst_id=0xc8 myTunnel_forward(port=0x1)",
            "myTunnel_exact dst_id=0x64 myTunnel_egress(dstAddr=0x80000000111, port=0x3)",
            "myTunnel_exact drop()",
        },
        "127.0.0.1:50002": {
            "ipv4_lpm dstAddr=0xa000101 myTunnel_ingress(dst_id=0x64)",
            "ipv4_lpm NoAction()",
            "myTunnel_exact dst_id=0x64 myTunnel_forward(port=0x1)",
            "myTunnel_exact dst_id=0xc8 myTunnel_egress(dstAddr=0x80000000222, port=0x3)",
            "myTunnel_exact drop()",
        },
        "127.0.0.1:50003": {
            "ipv4_lpm NoAction()",
            "myTunnel_exact drop()",
        },
    }

    for target, expected_state in expected_switch_states.items():
        actual_state = await testlib.read_p4_tables(target)
        assert actual_state == expected_state, f"{target} failed!"
