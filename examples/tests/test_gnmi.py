import asyncio
from pathlib import Path

import pytest
import testlib

# All tests run in the "module" event loop.
pytestmark = pytest.mark.asyncio(loop_scope="module")

GNMI_DIR = Path(__file__).parents[1] / "gnmi"

DEMONET = GNMI_DIR / "net/run.py"


async def test_demo1(demonet, python):
    "Test the gnmi/demo1 example program."
    result = await python(GNMI_DIR / "demo1.py")
    assert result == "Interface 's1-eth1' is UP\n"


async def test_demo2(demonet, python):
    "Test the gnmi/demo2 example program."
    result = bytearray()

    async with python(GNMI_DIR / "demo2.py") | result as demo2:
        await asyncio.sleep(0.5)
        await demonet.send("h1 ifconfig eth0 down")
        await asyncio.sleep(0.5)
        await demonet.send("h1 ifconfig eth0 up")
        await asyncio.sleep(0.5)
        raise asyncio.CancelledError()

    assert (
        result.decode()
        == "initial: s1-eth1 is UP\nupdate:  s1-eth1 is DOWN\nupdate:  s1-eth1 is UP\n"
    )


async def test_demo3(demonet, python):
    "Test the gnmi/demo3 example program."
    result = bytearray()

    async with python(GNMI_DIR / "demo3.py") | result as demo3:
        await asyncio.sleep(6.5)
        raise asyncio.CancelledError()

    assert result.decode().startswith(
        "initial: s1-eth1 is UP\nupdate:  s1-eth1 is DOWN\nupdate:  s1-eth1 is UP\nupdate:  s1-eth1 is DOWN"
    )


@pytest.mark.skipif(not testlib.has_pygraphviz(), reason="Requires pygraphviz")
async def test_graph_dot(demonet, tmp_path):
    "Test the graph dot file."
    orig = GNMI_DIR / "net/map.dot"
    temp = tmp_path / "map.dot"
    demonet.config.to_graph().write(temp)

    assert testlib.diff_text(orig, temp) == []
