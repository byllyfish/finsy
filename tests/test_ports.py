from finsy.ports import PortList


async def test_ports(gnmi_client):
    ports = PortList()

    await ports.subscribe(gnmi_client)
    for port in ports:
        print(port)

    ports.close()
