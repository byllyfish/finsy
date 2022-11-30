import asyncio
from pathlib import Path

NGSDN_DIR = Path(__file__).parent.parent / "ngsdn"

DEMONET = NGSDN_DIR / "demonet/run.sh"


async def test_ngsdn(demonet, python):
    "Test the ngsdn/ngsdn example program."

    async with python("-m", "ngsdn").env(PYTHONPATH="..:ngsdn") as demo:
        await asyncio.sleep(2.0)

        # These are IPv6 pings.
        await demonet.send("h1a ping -c 1 h3")
        await demonet.send("h3 ping -c 1 h1a", expect=" 0% packet loss")

        demo.cancel()
