import asyncio
from pathlib import Path

import finsy as fy

P4SRC = Path(__file__).parent / "p4"


async def setup_tunnel(
    ingress: fy.Switch,
    egress: fy.Switch,
    tunnel_id: int,
    dst_eth: str,
    dst_ip: str,
    ingress_port: int,
    egress_port: int,
):
    await ingress.write(
        [
            +fy.P4TableEntry(
                "ipv4_lpm",
                match=fy.P4TableMatch(dstAddr=dst_ip),
                action=fy.P4TableAction("myTunnel_ingress", dst_id=tunnel_id),
            ),
            +fy.P4TableEntry(
                "myTunnel_exact",
                match=fy.P4TableMatch(dst_id=tunnel_id),
                action=fy.P4TableAction("myTunnel_forward", port=ingress_port),
            ),
        ]
    )
    await egress.write(
        [
            +fy.P4TableEntry(
                "myTunnel_exact",
                match=fy.P4TableMatch(dst_id=tunnel_id),
                action=fy.P4TableAction(
                    "myTunnel_egress", dstAddr=dst_eth, port=egress_port
                ),
            )
        ]
    )


async def main():
    opts = fy.SwitchOptions(
        p4info=P4SRC / "advanced_tunnel.p4info.txt",
        p4blob=P4SRC / "advanced_tunnel.json",
    )

    sw1 = fy.Switch("sw1", "127.0.0.1:50001", opts)
    sw2 = fy.Switch("sw2", "127.0.0.1:50002", opts)
    sw3 = fy.Switch("sw3", "127.0.0.1:50003", opts)

    async with sw1, sw2, sw3:
        # Delete existing rules.
        for sw in (sw1, sw2, sw3):
            await sw.delete_all()

        # Tunnel 100: traffic to h1.
        await setup_tunnel(sw2, sw1, 100, "08:00:00:00:01:11", "10.0.1.1", 1, 3)
        # Tunnel 200: traffic to h2.
        await setup_tunnel(sw1, sw2, 200, "08:00:00:00:02:22", "10.0.2.2", 1, 3)


if __name__ == "__main__":
    asyncio.run(main())
