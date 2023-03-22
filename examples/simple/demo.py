from pathlib import Path
from typing import Any

import finsy as fy

P4SRC = Path(__file__).parent / "p4"


def table_set_default(
    table_id: str,
    action: str,
    params: dict[str, Any],
):
    return ~fy.P4TableEntry(
        table_id,
        action=fy.P4TableAction(action, **params),
        is_default_action=True,
    )


def table_add(
    table_id: str,
    match: dict[str, Any],
    action: str,
    params: dict[str, Any],
):
    return +fy.P4TableEntry(
        table_id,
        match=fy.P4TableMatch(match),
        action=fy.P4TableAction(action, **params),
    )


ENTRIES = [
    table_set_default("send_frame", "_drop", {}),
    table_set_default("forward", "_drop", {}),
    table_set_default("ipv4_lpm", "_drop", {}),
    table_add(
        "send_frame", {"egress_port": 1}, "rewrite_mac", {"smac": "00:00:00:aa:bb:cc"}
    ),
    table_add(
        "send_frame", {"egress_port": 2}, "rewrite_mac", {"smac": "00:00:00:aa:bb:cc"}
    ),
    table_add(
        "forward", {"nhop_ipv4": "10.0.1.10"}, "set_dmac", {"dmac": "00:00:00:00:00:01"}
    ),
    table_add(
        "forward", {"nhop_ipv4": "10.0.2.10"}, "set_dmac", {"dmac": "00:00:00:00:00:02"}
    ),
    table_add(
        "ipv4_lpm",
        {"dstAddr": "10.0.1.10/32"},
        "set_nhop",
        {"nhop_ipv4": "10.0.1.10", "port": 1},
    ),
    table_add(
        "ipv4_lpm",
        {"dstAddr": "10.0.2.10/32"},
        "set_nhop",
        {"nhop_ipv4": "10.0.2.10", "port": 2},
    ),
]


async def main():
    "Main program."
    opts = fy.SwitchOptions(
        p4info=P4SRC / "simple_router.p4info.txt",
        p4blob=P4SRC / "simple_router.json",
    )

    async with fy.Switch("sw", "127.0.0.1:50001", opts) as sw:
        await sw.delete_all()
        await sw.write(ENTRIES)


if __name__ == "__main__":
    fy.run(main())
