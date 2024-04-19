import logging
import struct
from ipaddress import IPv4Address
from pathlib import Path

import finsy as fy

LOGGER = fy.LoggerAdapter(logging.getLogger("flowcache"))

_P4DIR = Path(__file__).parent / "p4"
P4INFO = _P4DIR / "flowcache.p4info.txtpb"
P4BLOB = _P4DIR / "flowcache.json"

CPU_PORT = 510
CPU_PORT_CLONE_SESSION_ID = 57
NUM_PORTS = 5


def _decode_ip(data: bytes) -> tuple[int, IPv4Address, IPv4Address]:
    "Decode IPv4 packet and return (ip_proto, ip_src, ip_dst)"
    proto, src, dst = struct.unpack_from(">23xb2xLL", data)
    return proto, IPv4Address(src), IPv4Address(dst)


class DemoApp:
    """P4Runtime app for the flowcache example.

    This example uses a serializable enum from the P4Info file.
    """

    P4 = fy.P4Schema(P4INFO)
    OPCODE = P4.type_info.serializable_enums["ControllerOpcode_t"]
    PUNT_REASON = P4.type_info.serializable_enums["PuntReason_t"]
    FLOW_UNKNOWN = PUNT_REASON["FLOW_UNKNOWN"]

    options: fy.SwitchOptions

    def __init__(self):
        "Initialize SwitchOptions with reference to instance's on_ready method."
        self.options = fy.SwitchOptions(
            p4info=P4INFO,
            p4blob=P4BLOB,
            ready_handler=self.on_ready,
        )

    async def on_ready(self, sw: fy.Switch):
        """Called each time a P4Runtime connection is established with a
        Switch."""
        LOGGER.info("Delete all entries")
        await sw.delete_all()

        LOGGER.info("Insert CloneSessionEntry")
        await sw.write(
            [
                +fy.P4CloneSessionEntry(
                    CPU_PORT_CLONE_SESSION_ID,
                    replicas=[CPU_PORT],
                )
            ]
        )

        # Read packet-in's from switch and handle them.
        async for pkt in sw.read_packets():
            if pkt["punt_reason"] == self.FLOW_UNKNOWN:
                await self._handle_flow_unknown(sw, pkt)
            else:
                LOGGER.warning("unexpected packet_in: %s", pkt)

    async def _handle_flow_unknown(self, sw: fy.Switch, pkt: fy.P4PacketIn):
        "Handle the `FLOW_UNKNOWN` packet event."
        ip_proto, ip_src, ip_dst = _decode_ip(pkt.payload)
        flow_hash = int(ip_src) ^ int(ip_dst) ^ ip_proto
        dest_port = 1 + (flow_hash % NUM_PORTS)

        entry = self._flowcache_cached_action(
            ip_proto, ip_src, ip_dst, dest_port, True, 5
        )

        LOGGER.info(
            "Insert into %s: %s -> %s",
            entry.table_id,
            entry.match_str(sw.p4info),
            entry.action_str(sw.p4info),
        )
        await sw.write([+entry])

    @staticmethod
    def _flowcache_cached_action(
        ip_proto: int,
        ip_src: IPv4Address,
        ip_dst: IPv4Address,
        dest_port: int,
        decrement_ttl: bool,
        dscp: int,
    ):
        "Construct a `cached_action` entry to put into the `flow_cache` table."
        match = fy.Match(protocol=ip_proto, src_addr=ip_src, dst_addr=ip_dst)
        action = fy.Action(
            "cached_action",
            port=dest_port,
            decrement_ttl=decrement_ttl,
            new_dscp=dscp,
        )
        return fy.P4TableEntry("flow_cache", match=match, action=action)


async def main():
    app = DemoApp()
    switches = [
        fy.Switch("sw1", "127.0.0.1:50001", app.options),
    ]
    controller = fy.Controller(switches)
    await controller.run()


if __name__ == "__main__":
    fy.run(main())
