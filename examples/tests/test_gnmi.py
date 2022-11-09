import asyncio
from pathlib import Path

GNMI_DIR = Path(__file__).parent.parent / "gnmi"

DEMONET = GNMI_DIR / "demonet/run.sh"


async def test_demo1(demonet, python):
    "Test the gnmi/demo1 example program."

    result = await python(GNMI_DIR / "demo1.py")
    assert result == "Interface 's1-eth1' is UP\n"


async def test_demo2(demonet, python):
    "Test the gnmi/demo2 example program."

    result = bytearray()

    async with python(GNMI_DIR / "demo2.py") | result as demo2:
        await asyncio.sleep(0.5)
        await demonet.send("h1 ifconfig h1-eth0 down")
        await asyncio.sleep(0.5)
        await demonet.send("h1 ifconfig h1-eth0 up")
        await asyncio.sleep(0.5)
        demo2.cancel()

    assert (
        result.decode()
        == "initial: s1-eth1 is UP\nupdate:  s1-eth1 is DOWN\nupdate:  s1-eth1 is UP\n"
    )


async def test_demo3(demonet, python):
    "Test the gnmi/demo3 example program."

    result = bytearray()

    async with python(GNMI_DIR / "demo3.py") | result as demo3:
        await asyncio.sleep(6.5)
        demo3.cancel()

    assert result.decode().startswith(
        "initial: s1-eth1 is UP\nupdate:  s1-eth1 is DOWN\nupdate:  s1-eth1 is UP\nupdate:  s1-eth1 is DOWN"
    )