import asyncio
import logging
from pathlib import Path

import finsy as fy

P4SRC = Path(__file__).parent / "p4src"
MGRP = 0xAB
PORTS = [0, 1, 2, 3, 4]

LOG = fy.LoggerAdapter(logging.getLogger("demo"))


async def _ready_handler(switch: fy.Switch):
    await switch.delete_all()

    switch.create_task(_handle_digests(switch))
    switch.create_task(_handle_timeouts(switch))

    await switch.write(
        [
            +fy.P4DigestEntry("digest_t", max_list_size=1, ack_timeout_ns=int(1e9)),
            +fy.P4MulticastGroupEntry(MGRP, replicas=PORTS),
            ~fy.P4TableEntry(
                "dmac",
                action=fy.P4TableAction("broadcast", mgrp=MGRP),
                is_default_action=True,
            ),
        ]
    )


async def _handle_digests(switch: fy.Switch):
    async for digest in switch.read_digests():
        await switch.write(
            (_learn(entry["srcAddr"], entry["ingressPort"]) for entry in digest),
            warn_only=True,
        )
        await switch.write([digest.ack()])


async def _handle_timeouts(switch: fy.Switch):
    async for timeout in switch.read_idle_timeouts():
        await switch.write(
            [
                _unlearn(entry.match["srcAddr"])
                for entry in timeout.table_entry
                if entry.match
            ]
        )


def _learn(src_addr: int, ingress_port: int):
    LOG.info(f"Learn {src_addr:#x} on port {ingress_port}")
    return [
        +fy.P4TableEntry(
            "smac",
            match=fy.P4TableMatch(srcAddr=src_addr),
            action=fy.P4TableAction("NoAction"),
            idle_timeout_ns=int(10e9),
        ),
        +fy.P4TableEntry(
            "dmac",
            match=fy.P4TableMatch(dstAddr=src_addr),
            action=fy.P4TableAction("fwd", eg_port=ingress_port),
        ),
    ]


def _unlearn(src_addr: int):
    LOG.info(f"Unlearn {src_addr:#x}")
    return [
        -fy.P4TableEntry(
            "smac",
            match=fy.P4TableMatch(srcAddr=src_addr),
        ),
        -fy.P4TableEntry(
            "dmac",
            match=fy.P4TableMatch(dstAddr=src_addr),
        ),
    ]


async def main():
    options = fy.SwitchOptions(
        p4info=P4SRC / "l2_switch.p4info.txt",
        p4blob=P4SRC / "l2_switch.json",
        # force_pipeline=True,
        ready_handler=_ready_handler,
    )

    controller = fy.Controller(
        [
            fy.Switch("sw1", "127.0.0.1:50001", options),
            fy.Switch("sw2", "127.0.0.1:50002", options),
            fy.Switch("sw3", "127.0.0.1:50003", options),
        ]
    )
    await controller.run()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(created).03f %(levelname)s %(name)s %(message)s",
    )
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
