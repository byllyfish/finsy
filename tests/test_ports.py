import asyncio

import pytest

from finsy.ports import SwitchPortList


def test_ports():
    ports = SwitchPortList()
    assert len(ports) == 0
    assert list(ports) == []

    with pytest.raises(KeyError):
        ports["x"]


async def test_gnmi_ports_subscribe(gnmi_client):
    ports = SwitchPortList()

    await ports.subscribe(gnmi_client)
    for port in ports:
        print(port)
        assert ports[port.name] is port

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(ports.update(), 0.5)

    ports.close()
