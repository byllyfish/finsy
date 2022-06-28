import asyncio

import pytest
from finsy.gnmiclient import gNMIClient, gNMIPath


@pytest.fixture
async def gnmi_client():
    async with gNMIClient("127.0.0.1:50001") as client:
        yield client


async def test_gnmi_get_top(gnmi_client):
    # Stratum only supports config elements.
    result = await gnmi_client.get(gNMIPath("/"), config=True)
    assert len(result) == 1


async def test_gnmi_get_interfaces(gnmi_client):
    interfaces = gNMIPath("interfaces/interface")
    result = await gnmi_client.get(interfaces)

    for notification in result:
        for update in notification.update:
            assert gNMIPath(update.path).first == "interfaces"


async def test_gnmi_get_ifstuff(gnmi_client):
    ifindex = gNMIPath("interfaces/interface[name=*]/state/ifindex")
    state_id = gNMIPath("interfaces/interface[name=*]/state/id")

    result = await gnmi_client.get(ifindex, state_id)

    for notification in result:
        for update in notification.update:
            assert gNMIPath(update.path).last in ("ifindex", "id")


async def test_gnmi_subscribe_once(gnmi_client):
    interfaces = await _get_interfaces(gnmi_client)

    oper_status = gNMIPath("interfaces/interface/state/oper-status")
    sub = gnmi_client.subscribe()
    for ifname in interfaces:
        sub.once(oper_status.key("interface", name=ifname))

    async for notification in sub.synchronize():
        pass

    assert sub._stream is None


async def test_gnmi_subscribe_on_change(gnmi_client):
    interfaces = await _get_interfaces(gnmi_client)

    oper_status = gNMIPath("interfaces/interface/state/oper-status")
    sub = gnmi_client.subscribe()
    for ifname in interfaces:
        sub.on_change(oper_status.key("interface", name=ifname))

    # Place test code in a coroutine so I can set a timeout.
    async def _read_stream():
        async for _ in sub.synchronize():
            pass

        async for _ in sub.updates():
            pass

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(_read_stream(), 1.0)


async def test_gnmi_subscribe_sample(gnmi_client):
    interfaces = await _get_interfaces(gnmi_client)

    in_octets = gNMIPath("interfaces/interface/state/counters/in-octets")
    sub = gnmi_client.subscribe()
    for ifname in interfaces:
        # FIXME: stratum sample_interval appears to be in milliseconds? (not
        # nanoseconds as it says in GNMI spec)
        sub.sample(in_octets.key("interface", name=ifname), sample_interval=100)

    # Place test code in a coroutine so I can set a timeout.
    async def _read_stream():
        async for _ in sub.updates():
            pass

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(_read_stream(), 1.0)


async def test_gnmi_capabilities(gnmi_client):
    result = await gnmi_client.capabilities()
    assert result.gNMI_version[:2] in ("0.", "1.")


async def _get_interfaces(client):
    ifindex = gNMIPath("interfaces/interface/state/ifindex")
    expected_last = ifindex.last

    result = await client.get(ifindex.key("interface", name="*"))

    interfaces = {}
    for notification in result:
        for update in notification.update:
            path = gNMIPath(update.path)
            if path.last != expected_last:
                continue

            ifname = path["interface", "name"]
            interfaces[ifname] = update.val.uint_val

    return interfaces
