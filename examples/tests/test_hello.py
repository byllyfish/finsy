import asyncio
from pathlib import Path

import pytest
import testlib

HELLO_DIR = Path(__file__).parent.parent / "hello"

DEMONET = HELLO_DIR / "net/run.py"


async def test_demo0(python):
    "Test the hello/demo0 example program."
    result = await python(
        HELLO_DIR / "demo0.py",
        HELLO_DIR / "p4/hello.p4info.txt",
    )

    assert (
        result
        == """
hello.p4 (version=1, arch=v1model)
⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
📋 ipv4[1024]
   ipv4_dst:32
   forward(port:9) flood() MyIngress.drop()
📬 packet_in
   ingress_port:9 _pad:7
📬 packet_out
   egress_port:9 _pad:7

"""
    )


async def test_demo1(demonet, python):
    "Test the hello/demo1 example program."
    async with python(HELLO_DIR / "demo1.py") as demo1:
        await asyncio.sleep(0.25)
        await demonet.send("pingall", expect="(6/6 received)")
        demo1.cancel()


async def test_demo2(demonet, python):
    "Test the hello/demo2 example program."
    async with python(HELLO_DIR / "demo2.py") as demo2:
        await asyncio.sleep(0.25)
        await demonet.send("pingall")
        await demonet.send("pingall", expect="(6/6 received)")
        demo2.cancel()


async def test_demo3(demonet, python):
    "Test the hello/demo3 example program."
    async with python(HELLO_DIR / "demo3.py") as demo3:
        await asyncio.sleep(0.25)
        await demonet.send("pingall")
        await demonet.send("pingall", expect="(6/6 received)")
        demo3.cancel()


async def test_read_tables(demonet):
    "Read the state of the P4Runtime tables after running all the tests."
    expected_switch_states = {
        "127.0.0.1:50001": {
            "ipv4 ipv4_dst=10.0.0.1 forward(port=0x1)",
            "ipv4 ipv4_dst=10.0.0.2 forward(port=0x2)",
            "ipv4 ipv4_dst=10.0.0.3 forward(port=0x2)",
            "ipv4 MyIngress.drop()",
            "/multicast/0x1 1 2 255",
        },
        "127.0.0.1:50002": {
            "ipv4 ipv4_dst=10.0.0.1 forward(port=0x2)",
            "ipv4 ipv4_dst=10.0.0.2 forward(port=0x1)",
            "ipv4 ipv4_dst=10.0.0.3 forward(port=0x3)",
            "ipv4 MyIngress.drop()",
            "/multicast/0x1 1 2 3 255",
        },
        "127.0.0.1:50003": {
            "ipv4 ipv4_dst=10.0.0.1 forward(port=0x2)",
            "ipv4 ipv4_dst=10.0.0.2 forward(port=0x2)",
            "ipv4 ipv4_dst=10.0.0.3 forward(port=0x1)",
            "ipv4 MyIngress.drop()",
            "/multicast/0x1 1 2 255",
        },
    }

    for target, expected_state in expected_switch_states.items():
        actual_state = await testlib.read_p4_tables(target)
        assert actual_state == expected_state, f"{target} failed!"


@pytest.mark.skipif(not testlib.has_pygraphviz(), reason="Requires pygraphviz")
async def test_graph_dot(demonet, tmp_path):
    "Test the graph dot file."
    orig = HELLO_DIR / "net/map.dot"
    temp = tmp_path / "map.dot"
    demonet.config.to_graph().write(temp)

    assert testlib.diff_text(orig, temp) == []
