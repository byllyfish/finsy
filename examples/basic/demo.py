from pathlib import Path

import finsy as fy

_P4SRC = Path(__file__).parent / "p4"


def ipv4_lpm_forward(dstAddr: str, mac: str, port: int):
    "Insert entry into the ipv4_lpm table."
    return +fy.P4TableEntry(
        "ipv4_lpm",
        match=fy.Match(dstAddr=dstAddr),
        action=fy.Action("ipv4_forward", dstAddr=mac, port=port),
    )


def ipv4_lpm_drop_default():
    "Set the default action for the ipv4_lpm table to drop."
    return ~fy.P4TableEntry(
        "ipv4_lpm",
        action=fy.Action("drop"),
        is_default_action=True,
    )


S1_ENTS = [
    ipv4_lpm_drop_default(),
    ipv4_lpm_forward("10.0.1.1", "08:00:00:00:01:11", 1),
    ipv4_lpm_forward("10.0.2.2", "08:00:00:00:02:22", 2),
    ipv4_lpm_forward("10.0.3.3", "08:00:00:00:03:00", 3),
    ipv4_lpm_forward("10.0.4.4", "08:00:00:00:04:00", 4),
]

S2_ENTS = [
    ipv4_lpm_drop_default(),
    ipv4_lpm_forward("10.0.1.1", "08:00:00:00:03:00", 4),
    ipv4_lpm_forward("10.0.2.2", "08:00:00:00:04:00", 3),
    ipv4_lpm_forward("10.0.3.3", "08:00:00:00:03:33", 1),
    ipv4_lpm_forward("10.0.4.4", "08:00:00:00:04:44", 2),
]

S3_ENTS = [
    ipv4_lpm_drop_default(),
    ipv4_lpm_forward("10.0.1.1", "08:00:00:00:01:00", 1),
    ipv4_lpm_forward("10.0.2.2", "08:00:00:00:01:00", 1),
    ipv4_lpm_forward("10.0.3.3", "08:00:00:00:02:00", 2),
    ipv4_lpm_forward("10.0.4.4", "08:00:00:00:02:00", 2),
]

S4_ENTS = [
    ipv4_lpm_drop_default(),
    ipv4_lpm_forward("10.0.1.1", "08:00:00:00:01:00", 1),
    ipv4_lpm_forward("10.0.2.2", "08:00:00:00:01:00", 1),
    ipv4_lpm_forward("10.0.3.3", "08:00:00:00:02:00", 2),
    ipv4_lpm_forward("10.0.4.4", "08:00:00:00:02:00", 2),
]


async def main():
    "Main program."
    opts = fy.SwitchOptions(
        p4info=_P4SRC / "basic.p4info.txtpb",
        p4blob=_P4SRC / "basic.json",
        p4force=True,  # Always reload P4 program upon connection.
    )

    async with (
        fy.Switch("s1", "127.0.0.1:50001", opts) as s1,
        fy.Switch("s2", "127.0.0.1:50002", opts) as s2,
        fy.Switch("s3", "127.0.0.1:50003", opts) as s3,
        fy.Switch("s4", "127.0.0.1:50004", opts) as s4,
    ):
        await s1.write(S1_ENTS)
        await s2.write(S2_ENTS)
        await s3.write(S3_ENTS)
        await s4.write(S4_ENTS)


if __name__ == "__main__":
    fy.run(main())
