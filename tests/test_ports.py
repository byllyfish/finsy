import asyncio

import pytest
from finsy.ports import PortList


def test_ports():
    ports = PortList()
    assert len(ports) == 0
    assert list(ports) == []

    with pytest.raises(KeyError):
        ports[0]


async def test_gnmi_ports_subscribe(gnmi_client):
    ports = PortList()

    await ports.subscribe(gnmi_client)
    for port in ports:
        print(port)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(ports.update(), 0.5)

    ports.close()
