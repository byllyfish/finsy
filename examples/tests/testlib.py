import finsy as fy


async def read_p4_tables(target: str) -> set[str]:
    "Read all table entries from the P4Runtime switch."
    result: set[str] = set()

    async with fy.Switch("sw", target) as sw:
        with sw.p4info:
            # Wildcard-read does not read default entries.
            async for entry in sw.read(fy.P4TableEntry()):
                assert not entry.is_default_action
                result.add(
                    f"{entry.table_id} {entry.priority:#x} {entry.match_str(wildcard='*')} {entry.action_str()}"
                )
            # Read default entries for each table.
            for table in sw.p4info.tables:
                async for entry in sw.read(
                    fy.P4TableEntry(
                        table_id=table.alias,
                        is_default_action=True,
                    )
                ):
                    assert entry.is_default_action
                    assert entry.priority == 0
                    assert entry.match_str() == ""
                    result.add(f"{entry.table_id} {entry.action_str()}")

    return result
