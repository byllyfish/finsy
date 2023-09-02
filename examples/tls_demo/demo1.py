"""
Finsy demo program for a simple P4Runtime controller that floods every packet.
Same as `hello/demo1.py`, but uses mTLS.
"""

import logging
from pathlib import Path

import finsy as fy

# P4SRC is the path to the "p4" directory from the "hello" example.
P4SRC = Path(__file__).parent.parent / "hello/p4"

LOG = fy.LoggerAdapter(logging.getLogger("tls-demo1"))

CERT_DIR = Path(__file__).parent.parent.parent / "tests/test_certs/mtls1"

CACERT = CERT_DIR / "ca.crt"
CERT = CERT_DIR / "client.crt"
KEY = CERT_DIR / "client.key"


async def ready_handler(sw: fy.Switch):
    """The `ready_handler` function is the main entry point for each switch.

    Finsy calls this automatically after it has connected to the switch and
    loaded the forwarding pipeline program.
    """
    await sw.delete_all()
    await sw.write(
        [
            # Insert multicast group with ports 1, 2, and CONTROLLER.
            +fy.P4MulticastGroupEntry(1, replicas=[1, 2, 255]),
            # Modify default table entry to flood all unmatched packets.
            ~fy.P4TableEntry(
                "ipv4",
                action=fy.P4TableAction("flood"),
                is_default_action=True,
            ),
        ]
    )

    async for packet in sw.read_packets():
        LOG.info("%r", packet)


async def main():
    "Main program."
    credentials = fy.GRPCCredentialsTLS(
        cacert=CACERT,
        cert=CERT,
        private_key=KEY,
    )

    options = fy.SwitchOptions(
        p4info=P4SRC / "hello.p4info.txt",
        p4blob=P4SRC / "hello.json",
        ready_handler=ready_handler,
        channel_credentials=credentials,
    )

    switches = [
        fy.Switch("sw1", "127.0.0.1:50001", options),
        fy.Switch("sw2", "127.0.0.1:50002", options),
    ]

    controller = fy.Controller(switches)
    await controller.run()


if __name__ == "__main__":
    fy.run(main())
