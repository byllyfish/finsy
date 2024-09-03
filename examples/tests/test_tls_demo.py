import asyncio
from pathlib import Path

import pytest

# All tests run in the "module" event loop.
pytestmark = pytest.mark.asyncio(loop_scope="module")

TLSDEMO_DIR = Path(__file__).parents[1] / "tls_demo"

DEMONET = TLSDEMO_DIR / "net/run.py"


async def test_demo1(demonet, python):
    "Test the tls_demo/demo1 example program."
    async with python(TLSDEMO_DIR / "demo1.py") as demo1:
        await asyncio.sleep(0.25)
        await demonet.send("pingall", expect="(2/2 received)")
        demo1.cancel()
