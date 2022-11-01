import asyncio
from pathlib import Path

HELLO_DIR = Path(__file__).parent.parent / "hello"

DEMONET = HELLO_DIR / "demonet/run.sh"


async def test_demo0(python):
    "Test the hello/demo0 example program."

    result = await python(
        HELLO_DIR / "demo0.py",
        HELLO_DIR / "p4src/hello.p4info.txt",
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
