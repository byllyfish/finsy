import asyncio
import logging
from pathlib import Path

import finsy as fy

P4SRC = Path(__file__).parent / "p4src"
LOG = fy.LoggerAdapter(logging.getLogger("demo1"))


async def ready_handler(sw: fy.Switch):
    await sw.delete_all()
    await sw.write(
        [
            # Insert multicast group with ports 1, 2, 3 and CONTROLLER.
            +fy.P4MulticastGroupEntry(1, replicas=[1, 2, 3, 255]),
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


def main():
    options = fy.SwitchOptions(
        p4info=P4SRC / "hello.p4info.txt",
        p4blob=P4SRC / "hello.json",
        ready_handler=ready_handler,
    )

    controller = fy.Controller(
        [
            fy.Switch("sw1", "127.0.0.1:50001", options),
            fy.Switch("sw2", "127.0.0.1:50002", options),
            fy.Switch("sw3", "127.0.0.1:50003", options),
        ]
    )

    try:
        asyncio.run(controller.run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(created).03f %(levelname)s %(name)s %(message)s",
    )
    main()
