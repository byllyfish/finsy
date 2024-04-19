import difflib
import importlib.util
from pathlib import Path

import finsy as fy


async def read_p4_tables(target: str, *, skip_const: bool = False) -> set[str]:
    "Read all table entries from the P4Runtime switch."
    result: set[str] = set()

    async with fy.Switch(f"sw@{target}", target) as sw:
        p4 = sw.p4info

        # Wildcard-read does not read default entries.
        async for entry in sw.read(fy.P4TableEntry()):
            assert not entry.is_default_action

            # Skip const table entries upon request.
            if skip_const and sw.p4info.tables[entry.table_id].is_const:
                continue

            if entry.priority != 0:
                info = f"{entry.table_id} {entry.priority:#x}"
            else:
                info = entry.table_id

            match_str = entry.match_str(p4, wildcard="*")
            if match_str:
                result.add(f"{info} {match_str} {entry.action_str(p4)}")
            else:
                # Table has no match fields.
                result.add(f"{info} {entry.action_str(p4)}")

        # Read default entries for each table.
        for table in sw.p4info.tables:
            # Skip const table entries upon request.
            if skip_const and table.is_const:
                continue

            async for entry in sw.read(
                fy.P4TableEntry(
                    table_id=table.alias,
                    is_default_action=True,
                )
            ):
                assert entry.is_default_action
                assert entry.priority == 0
                assert entry.match_str(p4) == ""
                result.add(f"{entry.table_id} {entry.action_str(p4)}")

        # Read action profiles. Ignore an INVALID_ARGUMENT error that is
        # raised when the selector programming mode is using one shots.
        try:
            async for entry in sw.read(fy.P4ActionProfileGroup()):
                # Group syntax uses [ ]
                result.add(
                    f"@{entry.action_profile_id}[{entry.group_id:#x}]"
                    f" max_size={entry.max_size:#x} {entry.action_str(p4)}"
                )

            async for entry in sw.read(fy.P4ActionProfileMember()):
                # Member syntax uses [[ ]]
                result.add(
                    f"@{entry.action_profile_id}[[{entry.member_id:#x}]] {entry.action_str(p4)}"
                )

        except fy.P4ClientError as ex:
            if ex.code != fy.GRPCStatusCode.INVALID_ARGUMENT:
                raise

        # Read CloneSessionEntry's.
        async for entry in sw.read(fy.P4CloneSessionEntry()):
            # Include packet_length only if it is non-zero.
            packet_length = entry.packet_length_bytes
            if packet_length != 0:
                pkt_len_str = f"packet_length={packet_length} "
            else:
                pkt_len_str = ""
            result.add(
                f"/clone/{entry.session_id:#x} class_of_service={entry.class_of_service} {pkt_len_str}{entry.replicas_str()}"
            )

        # Read MulticastGroupEntry's.
        async for entry in sw.read(fy.P4MulticastGroupEntry()):
            result.add(
                f"/multicast/{entry.multicast_group_id:#x} {entry.replicas_str()}"
            )

        # Read all DigestEntry's (wildcard reads are not supported).
        digest_entries = [
            fy.P4DigestEntry(digest.alias) for digest in sw.p4info.digests
        ]
        if digest_entries:
            async for entry in sw.read(digest_entries):
                result.add(
                    f"/digest/{entry.digest_id} max_list_size={entry.max_list_size} max_timeout_ns={entry.max_timeout_ns} ack_timeout_ns={entry.ack_timeout_ns}"
                )

    return result


def diff_text(orig: Path, new: Path) -> list[str]:
    "Compare two text files line by line."
    with orig.open() as a, new.open() as b:
        diff = difflib.unified_diff(
            a.readlines(),
            b.readlines(),
            fromfile=orig.name,
            tofile=new.name,
        )
        return list(diff)


def has_pygraphviz():
    "Return True if the `pygraphviz` module is available."
    return importlib.util.find_spec("pygraphviz") is not None
