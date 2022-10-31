import asyncio
from pathlib import Path

L2SWITCH_DIR = Path(__file__).parent.parent / "l2_switch"

DEMONET = L2SWITCH_DIR / "demonet/run.sh"


async def test_demo(demonet, python):
    "Test the l2_switch/demo example program."

    async with python(L2SWITCH_DIR / "demo.py") as demo:
        await asyncio.sleep(0.25)
        await demonet.send("pingall", expect="(6/6 received)")
        demo.cancel()
