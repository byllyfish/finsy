import asyncio
import logging
from ipaddress import IPv4Address
from pathlib import Path

import finsy as fy

_ETH_ARP = 0x0806


class DemoApp:
    "Hello World, demo app."

    CONTROLLER_PORT = 255
    P4SRC = Path(__file__).parent / "p4src"
    P4INFO = P4SRC / "hello.p4info.txt"
    P4BLOB = P4SRC / "hello.json"

    def __init__(self):
        self.options = fy.SwitchOptions(
            p4info=self.P4INFO,
            p4blob=self.P4BLOB,
            ready_handler=self.on_ready,
        )

    async def on_ready(self, switch: fy.Switch):
        "Switch's ready handler."
        ports = [port.id for port in switch.ports] + [self.CONTROLLER_PORT]
        learned = set[IPv4Address]()

        await switch.delete_all()
        await switch.insert([fy.P4MulticastGroupEntry(1, replicas=ports)])

        async for packet in switch.read_packets(eth_types={_ETH_ARP}):
            # Extract source IPv4 address from ARP.
            addr = IPv4Address(packet.payload[28:32])
            if addr and addr not in learned:
                learned.add(addr)
                port = packet["ingress_port"]
                await switch.insert(self._learn(switch, addr, port))

    @staticmethod
    def _learn(switch: fy.Switch, addr: IPv4Address, port: int):
        "Return a P4TableEntry which tells where to forward this IPv4 address."
        print(f"{switch.name} learned {addr} on port {port}")
        return [
            fy.P4TableEntry(
                "ipv4",
                match=fy.P4TableMatch(ipv4_dst=addr),
                action=fy.P4TableAction("forward", port=port),
            ),
        ]


async def main():
    app = DemoApp()

    switches = [
        fy.Switch("s1", "127.0.0.1:50001", app.options),
        fy.Switch("s2", "127.0.0.1:50002", app.options),
        fy.Switch("s3", "127.0.0.1:50003", app.options),
    ]

    controller = fy.Controller(switches)
    await controller.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
