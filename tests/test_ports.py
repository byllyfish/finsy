import pytest
from finsy.ports import PortList


def test_ports():
    ports = PortList()
    assert len(ports) == 0
    assert list(ports) == []

    with pytest.raises(KeyError):
        ports[0]


async def test_ports_subscribe(gnmi_client):
    ports = PortList()

    await ports.subscribe(gnmi_client)
    for port in ports:
        print(port)

    ports.close()
