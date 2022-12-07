import finsy as fy


async def read_p4_tables(target: str) -> set[str]:
    "Read all table entries from the P4Runtime switch."
    result: set[str] = set()

    async with fy.Switch("sw", target) as sw:
        with sw.p4info:
            async for entry in sw.read(fy.P4TableEntry()):
                result.add(
                    f"{entry.table_id} {entry.match_str(wildcard='*')} {entry.action_str()}"
                )

    return result
