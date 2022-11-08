import asyncio
import logging
import signal

from finsy import GNMIClient, GNMIPath

_INTERFACE = GNMIPath("interfaces/interface[name=*]/state")
INTERFACE_ID = _INTERFACE / "id"
INTERFACE_STATUS = _INTERFACE / "oper-status"


async def main():
    "Main program."

    # Boilerplate to shutdown cleanly upon SIGTERM signal.
    asyncio.get_running_loop().add_signal_handler(
        signal.SIGTERM,
        lambda task: task.cancel(),
        asyncio.current_task(),
    )

    async with GNMIClient("127.0.0.1:50001") as client:
        # Get list of interface names.
        ids = await client.get(INTERFACE_ID)
        names = [update.path["name"] for update in ids]

        # Subscribe to status (up/down) of each interface by name.
        paths = [INTERFACE_STATUS.set(name=name) for name in names]

        sub = client.subscribe()
        sub.on_change(*paths)

        # Fetch initial status of each interface.
        async for update in sub.synchronize():
            print(f"initial: {update.path['name']} is {update.value}")

        # Listen for status updates.
        async for update in sub.updates():
            print(f"update:  {update.path['name']} is {update.value}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
