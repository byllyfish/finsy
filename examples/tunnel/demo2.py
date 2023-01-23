import asyncio

import finsy as fy


async def log_counters(sw: fy.Switch, counter_id: str, indexes: tuple[int, ...]):
    "Read counters for specific indexes and print them out."
    entries = [fy.P4CounterEntry(counter_id, index=indx) for indx in indexes]

    async for counter in sw.read(entries):
        indx = counter.index
        pkt_count = counter.packet_count
        byte_count = counter.byte_count
        print(f"{sw.name} {counter_id}[{indx}] pkts={pkt_count} bytes={byte_count}")


async def main():
    # We want a backup (not primary) client for read-only purposes.
    opts = fy.SwitchOptions(initial_election_id=0)

    sw1 = fy.Switch("sw1", "127.0.0.1:50001", opts)
    sw2 = fy.Switch("sw2", "127.0.0.1:50002", opts)

    async with sw1, sw2:

        while True:
            for sw in (sw1, sw2):
                await log_counters(sw, "ingressTunnelCounter", (100, 200))
                await log_counters(sw, "egressTunnelCounter", (100, 200))
                print()  # blank line between switches
            await asyncio.sleep(3.0)


if __name__ == "__main__":
    asyncio.run(main())
