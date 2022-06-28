from finsy.gnmiclient import gNMIClient
from finsy.ports import PortList


async def test_ports():
    async with gNMIClient("127.0.0.1:50001") as client:
        ports = PortList()

        await ports.subscribe(client)
        for port in ports:
            print(port)

        ports.close()
