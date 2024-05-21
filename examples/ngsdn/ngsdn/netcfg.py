"Reads netcfg.json file."

from ipaddress import IPv6Address, IPv6Interface, IPv6Network
from typing import Any, Iterator
from urllib.parse import parse_qs, urlparse

import finsy as fy


def configured_devices(netcfg: dict[str, Any]) -> Iterator[tuple[str, str, int]]:
    "Return list of configured switch names, addresses, device_ids."
    for name, cfg in netcfg["devices"].items():
        address, device_id = _parse_url(cfg["basic"]["managementAddress"])
        yield (name, address, device_id)


def spine_switches() -> list[fy.Switch]:
    "Return list of spine switches."
    return [sw for sw in fy.Controller.current() if is_spine(sw)]


def leaf_switches() -> list[fy.Switch]:
    "Return list of leaf switches."
    return [sw for sw in fy.Controller.current() if not is_spine(sw)]


def is_spine(switch: fy.Switch) -> bool:
    "Return true if `isSpine` is true."
    return _fabric_config(switch)["isSpine"]


def get_station_mac(switch: fy.Switch) -> fy.MACAddress:
    "Return the switch's station mac."
    return fy.MACAddress(_fabric_config(switch)["myStationMac"])


def get_sid(switch: fy.Switch) -> IPv6Address:
    "Return the switch's `mySid` value."
    return IPv6Address(_fabric_config(switch)["mySid"])


def get_networks(switch: fy.Switch, include_sid: bool = False) -> set[IPv6Network]:
    "Return the leaf networks associated with the switch."
    result = {intf.network for _, intf in _get_interfaces(switch)}
    if include_sid:
        result.add(IPv6Network(get_sid(switch)))
    return result


def get_addresses(switch: fy.Switch) -> set[IPv6Address]:
    "Return the interface addresses associated with the switch."
    return {intf.ip for _, intf in _get_interfaces(switch)}


def get_host_facing_ports(switch: fy.Switch) -> set[int]:
    "Return the set of host-facing port numbers."
    return {switch.ports[name].id for name, _ in _get_interfaces(switch)}


def _get_interfaces(switch: fy.Switch) -> Iterator[tuple[str, IPv6Interface]]:
    "Helper function to return list of configured interfaces."
    prefix = f"{switch.name}/"
    netcfg = switch.stash["config"]

    for name, port in netcfg["ports"].items():
        if not name.startswith(prefix):
            continue

        for interface in port["interfaces"]:
            ifname = interface["name"]
            for intf in interface["ips"]:
                yield ifname, IPv6Interface(intf)


def _fabric_config(switch: fy.Switch) -> dict[str, Any]:
    "Return the fabric config for a device."
    netcfg = switch.stash["config"]
    return netcfg["devices"][switch.name]["fabricDeviceConfig"]


def _parse_url(url: str) -> tuple[str, int]:
    "Parse GRPC URL and return (address, device_id)."
    obj = urlparse(url)
    if obj.scheme != "grpc":
        raise ValueError(f"Not a grpc url: {url!r}")

    query = parse_qs(obj.query)
    return (obj.netloc, int(query["device_id"][0]))
