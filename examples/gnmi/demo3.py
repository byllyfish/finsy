import asyncio
import logging
import signal

from finsy import gNMIClient, gNMIPath
from finsy.proto import gnmi

_INTERFACE = gNMIPath("interfaces/interface[name=*]/state")
INTERFACE_ID = _INTERFACE / "id"
INTERFACE_STATUS = _INTERFACE / "oper-status"
INTERFACE_ENABLED = gNMIPath("interfaces/interface[name=*]/config/enabled")

ON = gnmi.TypedValue(bool_val=True)
OFF = gnmi.TypedValue(bool_val=False)


async def main():
    "Main program."

    # Boilerplate to shutdown cleanly upon SIGTERM signal.
    asyncio.get_running_loop().add_signal_handler(
        signal.SIGTERM,
        lambda task: task.cancel(),
        asyncio.current_task(),
    )

    async with gNMIClient("127.0.0.1:50001") as client:
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

        # Run a background task to toggle the interface status.
        asyncio.create_task(toggle_enabled(names))

        # Listen for status updates.
        async for update in sub.updates():
            print(f"update:  {update.path['name']} is {update.value}")


async def toggle_enabled(names: list[str]):
    "Repeatedly disable and enable interfaces using a separate GNMI client."

    async with gNMIClient("127.0.0.1:50001") as client:
        while True:
            await asyncio.sleep(1.0)
            updates = {INTERFACE_ENABLED.set(name=name): OFF for name in names}
            await client.set(update=updates)

            await asyncio.sleep(1.0)
            updates = {INTERFACE_ENABLED.set(name=name): ON for name in names}
            await client.set(update=updates)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
