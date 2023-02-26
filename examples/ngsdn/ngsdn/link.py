import asyncio
import enum
import random
import struct
from dataclasses import dataclass

from macaddress import MAC

import finsy as fy

from . import netcfg
from .log import LOG

_MAGIC_PREFIX = 0x5F18


class LinkEvent(str, enum.Enum):
    "Events for LinkManager class."

    LINK_READY = "LINK_READY"  # (switch, LinkReady)


@dataclass
class LinkReady:
    local_port: int
    remote_switch: str
    remote_port: str


class LinkManager:
    switch: fy.Switch
    links: dict[int, LinkReady]

    def __init__(self, switch: fy.Switch):
        self.switch = switch
        self.links = {}

    async def run(self):
        self.links.clear()

        self.switch.create_task(self._read_packets())
        await self.switch.write(self._listen_lldp())

        # FIXME: Links can come up at different times.
        await asyncio.sleep(random.uniform(0, 0.25))

        for _ in range(3):
            await self.switch.write(self._send_packets())
            await asyncio.sleep(0.2)

    async def _read_packets(self):
        async for packet in self.switch.read_packets(eth_types=[0x88CC]):
            local_port = packet["ingress_port"]
            remote_switch, remote_port = _decode_lldp(packet.payload)
            event = LinkReady(local_port, remote_switch, remote_port)
            existing_event = self.links.get(local_port)
            if existing_event != event:
                self.links[local_port] = event
                LOG.info("%r", event)
                self.switch.ee.emit(LinkEvent.LINK_READY, self.switch, event)

    def _listen_lldp(self):
        return [
            +fy.P4TableEntry(
                "acl_table",
                match=fy.P4TableMatch(ether_type=(0x88CC, 0xFFFF)),
                action=fy.P4TableAction("send_to_cpu"),
                priority=2,
            )
        ]

    def _send_packets(self):
        station_mac = netcfg.get_station_mac(self.switch)
        for port in self.switch.ports:
            payload = _encode_lldp(
                station_mac, self.switch.name.encode(), port.name.encode()
            )
            yield fy.P4PacketOut(payload, magic_val=_MAGIC_PREFIX, egress_port=port.id)


_LLDP_DST = b"\x01\x80\xc2\x00\x00\x00"


def _encode_lldp(station_mac: MAC, chassis_id: bytes, port_id: bytes):
    result = b"".join(
        [
            struct.pack("!6s6sH", _LLDP_DST, bytes(station_mac), 0x88CC),
            _encode_tlv(1, chassis_id),
            _encode_tlv(2, port_id),
            _encode_tlv(3, b"\x00\x01"),
            _encode_tlv(0, b""),
        ]
    )

    # If LLDP is less than 60 bytes, pad it with zeros. (?)
    # if len(result) < 60:
    #    result += b"\x00" * (60 - len(result))

    return result


def _encode_tlv(tag: int, value: bytes):
    return struct.pack("!H", (tag << 9) | len(value)) + value


def _decode_lldp(payload: bytes) -> tuple[str, str]:
    data = payload[14:]
    chassis_id = ""
    port_id = ""

    while True:
        (taglen,) = struct.unpack_from("!H", data)
        size = taglen & 0x01FF
        match (taglen >> 9):
            case 1:
                chassis_id = data[2 : 2 + size].decode()
            case 2:
                port_id = data[2 : 2 + size].decode()
            case _:
                return (chassis_id, port_id)
        data = data[2 + size :]
