import asyncio
import os
import struct
from dataclasses import dataclass, field
from ipaddress import IPv4Address, IPv6Address

import finsy as fy
from finsy import MACAddress, Switch

from . import netcfg
from .log import LOG


class PROTO:
    ETH_ARP = 0x0806
    ETH_IPV6 = 0x86DD
    ICMPV6 = 58


@dataclass(slots=True)
class L2Host:
    mac: MACAddress
    port: int
    addrs: set[IPv4Address | IPv6Address] = field(default_factory=set)


class HostEvent:
    pass


@dataclass
class HostAdd(HostEvent):
    host: L2Host
    addr: IPv4Address | IPv6Address


@dataclass
class HostMove(HostEvent):
    host: L2Host
    old_port: int


@dataclass
class HostAddIP(HostEvent):
    host: L2Host
    addr: IPv4Address | IPv6Address


class HostManagerOneShot:
    """The HostManager tracks the hosts discovered on each switch port."""

    MULTICAST_GROUP_ID = 99
    CPU_CLONE_SESSION_ID = 99
    CONTROLLER_PORT = 255

    switch: Switch
    hosts: dict[MACAddress, L2Host]
    events: asyncio.Queue[HostEvent]

    def __init__(self, switch: Switch):
        self.switch = switch
        self.hosts = {}
        self.events = asyncio.Queue()

    async def run(self):
        "Listen for ARP/NDP packets and learn the host/port/address mappings."
        assert self.events.empty()
        self.hosts.clear()

        if netcfg.is_spine(self.switch):
            await self.switch.write([self._insert_clone_session()])
            return

        await self.switch.write(
            [
                self._insert_clone_session(),
                self._insert_multicast_group(),
                self._insert_l2_ternary_rules(),
                self._insert_acl_rules(),
            ]
        )

        self.switch.create_task(self._handle_events())

        async for packet in self.switch.read_packets(
            eth_types=(PROTO.ETH_ARP, PROTO.ETH_IPV6)
        ):
            self._handle_packet(packet)

    def _handle_packet(self, packet: fy.P4PacketIn):
        mac, addr = _parse_host_packet(packet.payload)
        port = packet["ingress_port"]
        if addr.is_unspecified:
            return

        host = self.hosts.get(mac)
        if not host:
            # Host added...
            host = L2Host(mac, port)
            host.addrs.add(addr)
            self.hosts[mac] = host
            self.events.put_nowait(HostAdd(host, addr))
        else:
            if addr not in host.addrs:
                # Host new IP!
                host.addrs.add(addr)
                self.events.put_nowait(HostAddIP(host, addr))
            if host.port != port:
                # Host moved...
                old_port = host.port
                host.port = port
                self.events.put_nowait(HostMove(host, old_port))

    async def _handle_events(self):
        while True:
            event = await self.events.get()
            LOG.info("%r", event)
            match event:
                case HostAdd(host, addr):
                    await self.switch.write(
                        [
                            self._l2learn(host),
                            await self._l3learn(host, addr),
                        ]
                    )
                case HostMove(host, _):
                    pass
                case HostAddIP(host, addr):
                    await self.switch.write(await self._l3learn(host, addr))
                case _:
                    pass

    def _l2learn(self, host: L2Host):
        return [
            +fy.P4TableEntry(
                "l2_exact_table",
                match=fy.P4TableMatch(dst_addr=host.mac),
                action=fy.P4TableAction("set_egress_port", port_num=host.port),
            ),
        ]

    async def _l3learn(
        self,
        host: L2Host,
        addr: IPv4Address | IPv6Address,
    ) -> list[fy.P4TableEntry]:
        if not isinstance(addr, IPv6Address):
            return []

        return [
            +fy.P4TableEntry(
                "routing_v6_table",
                match=fy.P4TableMatch(dst_addr=(addr, 128)),
                action=fy.P4TableAction("set_next_hop", dmac=host.mac),
            )
        ]

    def _insert_multicast_group(self):
        return +fy.P4MulticastGroupEntry(
            self.MULTICAST_GROUP_ID,
            replicas=list(netcfg.get_host_facing_ports(self.switch)),
        )

    def _insert_clone_session(self):
        return +fy.P4CloneSessionEntry(
            self.CPU_CLONE_SESSION_ID,
            replicas=[self.CONTROLLER_PORT],
        )

    def _insert_l2_ternary_rules(self):
        set_multicast_group = fy.P4TableAction(
            "set_multicast_group", gid=self.MULTICAST_GROUP_ID
        )
        return [
            +fy.P4TableEntry(
                "l2_ternary_table",
                match=fy.P4TableMatch(dst_addr=dst_addr),
                action=set_multicast_group,
                priority=priority,
            )
            for dst_addr, priority in [
                ("FF:FF:FF:FF:FF:FF/FF:FF:FF:FF:FF:FF", 2),
                ("33:33:00:00:00:00/FF:FF:00:00:00:00", 2),
            ]
        ]

    def _insert_acl_rules(self):
        return [
            +fy.P4TableEntry(
                "acl_table",
                match=fy.P4TableMatch(ether_type=(PROTO.ETH_ARP, 0xFFFF)),
                action=fy.P4TableAction("clone_to_cpu"),
                priority=1,
            ),
        ] + [
            +fy.P4TableEntry(
                "acl_table",
                match=fy.P4TableMatch(
                    ether_type=PROTO.ETH_IPV6,
                    ip_proto=PROTO.ICMPV6,
                    icmp_type=icmp_type,
                ),
                action=fy.P4TableAction("clone_to_cpu"),
                priority=1,
            )
            for icmp_type in (135, 136)
        ]


def _parse_host_packet(data: bytes) -> tuple[MACAddress, IPv4Address | IPv6Address]:
    eth_src, eth_type = struct.unpack_from("!6x6sH", data)
    match eth_type:
        case PROTO.ETH_ARP:
            (ipv4,) = struct.unpack_from("!8x6x4s", data[14:])
            return (MACAddress(eth_src), IPv4Address(ipv4))
        case PROTO.ETH_IPV6:
            (ipv6,) = struct.unpack_from("!8x16s", data[14:])
            return (MACAddress(eth_src), IPv6Address(ipv6))
        case _:
            raise ValueError(f"unknown eth_type: {eth_type!r}")


class HostManagerActionProfile(HostManagerOneShot):
    _macs: dict[MACAddress, int] | None = None
    _id: int = 2**16

    def _get_next_id(self):
        self._id += 1
        return self._id

    async def _l3learn(
        self,
        host: L2Host,
        addr: IPv4Address | IPv6Address,
    ) -> list[fy.P4TableEntry]:
        if not isinstance(addr, IPv6Address):
            return []

        if self._macs is None:
            self._macs = {}

        member_id = self._macs.get(host.mac)
        if member_id is None:
            member_id = self._get_next_id()
            member = fy.P4ActionProfileMember(
                "ecmp_selector",
                member_id=member_id,
                action=fy.P4TableAction("set_next_hop", dmac=host.mac),
            )
            self._macs[host.mac] = member_id
            await self.switch.write([+member])

        return [
            +fy.P4TableEntry(
                "routing_v6_table",
                match=fy.P4TableMatch(dst_addr=(addr, 128)),
                action=fy.P4IndirectAction(member_id=member_id),
            )
        ]


if os.environ.get("NGSDN_USE_ACTIONPROFILE"):
    HostManager = HostManagerActionProfile
else:
    HostManager = HostManagerOneShot
