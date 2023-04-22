import asyncio

import finsy as fy

_INTERFACE = fy.GNMIPath("interfaces/interface[name=*]/state")
INTERFACE_ID = _INTERFACE / "id"
INTERFACE_STATUS = _INTERFACE / "oper-status"
INTERFACE_ENABLED = fy.GNMIPath("interfaces/interface[name=*]/config/enabled")


async def main():
    "Main program."
    async with fy.GNMIClient("127.0.0.1:50001") as client:
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
        _task = asyncio.create_task(toggle_enabled(names))

        # Listen for status updates.
        async for update in sub.updates():
            print(f"update:  {update.path['name']} is {update.value}")


async def toggle_enabled(names: list[str]):
    "Repeatedly disable and enable interfaces using a separate GNMI client."
    async with fy.GNMIClient("127.0.0.1:50001") as client:
        while True:
            await asyncio.sleep(1.0)
            updates = [(INTERFACE_ENABLED.set(name=name), False) for name in names]
            await client.set(update=updates)

            await asyncio.sleep(1.0)
            updates = [(INTERFACE_ENABLED.set(name=name), True) for name in names]
            await client.set(update=updates)


if __name__ == "__main__":
    fy.run(main())
