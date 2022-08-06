import asyncio
import logging
from pathlib import Path

import finsy as fy


class HelloWorldApp:
    "Hello World, demo app."

    CONTROLLER_PORT = 255
    P4SRC = Path(__file__).parent / "p4src"
    P4INFO = P4SRC / "hello.p4info.txt"
    P4BLOB = P4SRC / "hello.json"
    PORTS = [1, 2, 3, 4, CONTROLLER_PORT]

    options: fy.SwitchOptions

    def __init__(self):
        self.options = fy.SwitchOptions(
            p4info=self.P4INFO,
            p4blob=self.P4BLOB,
            ready_handler=self.on_ready,
        )

    async def on_ready(self, switch: fy.Switch):
        "Switch's ready handler."
        await switch.delete_all()
        await switch.insert(fy.P4MulticastGroupEntry(1, replicas=self.PORTS))

        switch.create_task(self._send_packet_out(switch))

        seen = set[bytes]()
        async for packet in switch.read_packets():
            addr = packet.payload[28:32]  # source IPv4 address from ARP
            if addr and addr not in seen:
                seen.add(addr)
                port = packet["ingress_port"]
                await switch.insert(self._learn(switch, addr, port))

    async def _send_packet_out(self, switch: fy.Switch):
        "Once a second, send a packet which will come right back to us."
        while True:
            await asyncio.sleep(1.0)
            await switch.write(
                fy.P4PacketOut(
                    bytes.fromhex("deadbeefdeadbeef"),
                    egress_port=self.CONTROLLER_PORT,
                    _pad=0,
                )
            )

    @staticmethod
    def _learn(switch: fy.Switch, addr: bytes, port: int):
        "Return a P4TableEntry which tells where to forward this IPv4 address."
        print(f"{switch.name} learned {addr.hex()} on port {port}")
        return fy.P4TableEntry(
            "ipv4",
            match=fy.P4TableMatch(ipv4_dst=addr),
            action=fy.P4TableAction("forward", port=port),
        )


async def main():
    app = HelloWorldApp()

    switches = [
        fy.Switch("s1", "127.0.0.1:50001", app.options),
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
