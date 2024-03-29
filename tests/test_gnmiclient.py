import asyncio

import pytest

from finsy import pbutil
from finsy.gnmiclient import GNMIClient, GNMIPath, gnmi_update


async def test_gnmi_get_top(gnmi_client: GNMIClient):
    # Stratum only supports config elements.
    result = await gnmi_client.get(GNMIPath("/"), config=True)
    assert len(result) == 1
    assert result[0].path == GNMIPath("/")


async def test_gnmi_get_interfaces(gnmi_client: GNMIClient):
    interfaces = GNMIPath("interfaces/interface")
    result = await gnmi_client.get(interfaces)

    for update in result:
        assert update.path.first == "interfaces"


async def test_gnmi_get_ifstuff(gnmi_client: GNMIClient):
    ifindex = GNMIPath("interfaces/interface[name=*]/state/ifindex")
    state_id = GNMIPath("interfaces/interface[name=*]/state/id")

    result = await gnmi_client.get(ifindex, state_id)

    for update in result:
        assert update.path.last in ("ifindex", "id")


async def test_gnmi_subscribe_once(gnmi_client: GNMIClient):
    interfaces = await _get_interfaces(gnmi_client)

    oper_status = GNMIPath("interfaces/interface/state/oper-status")
    sub = gnmi_client.subscribe()
    for ifname in interfaces:
        sub.once(oper_status.set("interface", name=ifname))

    async for _update in sub.synchronize():
        pass

    assert sub._stream is None


async def test_gnmi_subscribe_on_change(gnmi_client: GNMIClient):
    interfaces = await _get_interfaces(gnmi_client)

    oper_status = GNMIPath("interfaces/interface/state/oper-status")
    sub = gnmi_client.subscribe()
    for ifname in interfaces:
        sub.on_change(oper_status.set("interface", name=ifname))

    # Place test code in a coroutine so I can set a timeout.
    async def _read_stream():
        async for _ in sub.synchronize():
            pass

        async for _ in sub.updates():
            pass

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(_read_stream(), 1.0)


async def test_gnmi_subscribe_sample(gnmi_client: GNMIClient):
    interfaces = await _get_interfaces(gnmi_client)

    in_octets = GNMIPath("interfaces/interface/state/counters/in-octets")
    sub = gnmi_client.subscribe()
    for ifname in interfaces:
        # FIXME: stratum sample_interval appears to be in milliseconds? (not
        # nanoseconds as it says in GNMI spec)
        sub.sample(in_octets.set("interface", name=ifname), sample_interval=100)

    # Place test code in a coroutine so I can set a timeout.
    async def _read_stream():
        async for update in sub.updates():
            assert update.path.last == "in-octets"

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(_read_stream(), 1.0)


async def test_gnmi_capabilities(gnmi_client: GNMIClient):
    result = await gnmi_client.capabilities()
    assert result.gNMI_version[:2] in ("0.", "1.")


async def test_gnmi_set(gnmi_client: GNMIClient):
    enabled = GNMIPath("interfaces/interface[name=s1-eth1]/config/enabled")
    result = await gnmi_client.get(enabled)
    assert result

    await gnmi_client.set(replace=[(enabled, False)])

    await gnmi_client.get(
        GNMIPath("interfaces/interface[name=s1-eth1]/state/admin-status")
    )


async def _get_interfaces(gnmi_client: GNMIClient):
    ifindex = GNMIPath("interfaces/interface[name=*]/state/ifindex")
    result = await gnmi_client.get(ifindex)

    interfaces = {}
    for update in result:
        if update.path.last != ifindex.last:
            continue

        ifname = update.path["interface", "name"]
        interfaces[ifname] = update.value

    return interfaces


def test_gnmi_update():
    "Test the internal `gnmi_update` function."
    examples = [
        (True, {"bool_val": True}),
        (False, {"bool_val": False}),
        (0, {"uint_val": "0"}),
        (1, {"uint_val": "1"}),
        (-1, {"int_val": "-1"}),
        (1.1, {"double_val": 1.1}),
        ("s", {"string_val": "s"}),
        (b"b", {"bytes_val": "Yg=="}),
    ]

    path = GNMIPath("path")
    for val, result in examples:
        assert pbutil.to_dict(gnmi_update(path, val).val) == result
