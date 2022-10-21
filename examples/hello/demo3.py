import asyncio
import logging
from ipaddress import IPv4Address
from pathlib import Path

import finsy as fy
from finsy.proto import stratum

P4SRC = Path(__file__).parent / "p4src"
LOG = fy.LoggerAdapter(logging.getLogger("demo3"))


class DemoRoleApp:
    "Hello World, demo app."

    CONTROLLER_PORT = 255
    P4INFO = P4SRC / "hello.p4info.txt"
    P4BLOB = P4SRC / "hello.json"

    def __init__(self):
        self.options = fy.SwitchOptions(
            p4info=self.P4INFO,
            p4blob=self.P4BLOB,
            ready_handler=self.on_ready,
        )
        # `backup_options` is a copy of `options` with some minor changes.
        self.backup_options = self.options(
            p4blob=None,  # Role 'backup' is not allowed to push pipelines.
            role_name="backup",
            role_config=stratum.P4RoleConfig(receives_packet_ins=True),
        )

    async def on_ready(self, switch: fy.Switch):
        "Switch's ready handler."
        if not switch.is_primary:
            return  # Bail out if we're not primary for our role

        if switch.role_name == "":
            # We are the default role; set up the switch.
            ports = [port.id for port in switch.ports] + [self.CONTROLLER_PORT]
            await switch.delete_all()
            await switch.insert([fy.P4MulticastGroupEntry(1, replicas=ports)])

        learned = set[IPv4Address]()
        async for packet in switch.read_packets(eth_types={0x0806}):
            # Extract source IPv4 address from ARP.
            addr = IPv4Address(packet.payload[28:32])
            if addr and addr not in learned:
                learned.add(addr)
                port = packet["ingress_port"]
                if switch.role_name == "backup":
                    # Backup role doesn't have write access, so just log the pkt.
                    LOG.info(f"Backup learned {addr} on port {port}")
                else:
                    await switch.insert(self._learn(addr, port))

    @staticmethod
    def _learn(addr: IPv4Address, port: int):
        "Return a P4TableEntry which tells where to forward this IPv4 address."
        LOG.info(f"Learn {addr} on port {port}")
        return [
            fy.P4TableEntry(
                "ipv4",
                match=fy.P4TableMatch(ipv4_dst=addr),
                action=fy.P4TableAction("forward", port=port),
            ),
        ]


async def main():
    app = DemoRoleApp()

    switches = [
        fy.Switch("s1", "127.0.0.1:50001", app.options),
        # `s1b` is the same switch as `s1` but with the backup role.
        fy.Switch("s1b", "127.0.0.1:50001", app.backup_options),
        fy.Switch("s2", "127.0.0.1:50002", app.options),
        fy.Switch("s3", "127.0.0.1:50003", app.options),
    ]

    controller = fy.Controller(switches)
    await controller.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
