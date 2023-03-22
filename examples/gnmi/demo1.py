import finsy as fy

_INTERFACE = fy.GNMIPath("interfaces/interface[name=*]/state")
INTERFACE_ID = _INTERFACE / "id"
INTERFACE_STATUS = _INTERFACE / "oper-status"


async def main():
    "Main program."

    async with fy.GNMIClient("127.0.0.1:50001") as client:
        # Get list of interface names.
        ids = await client.get(INTERFACE_ID)
        names = [update.path["name"] for update in ids]

        # Get status (up/down) of each interface by name.
        paths = [INTERFACE_STATUS.set(name=name) for name in names]
        stats = await client.get(*paths)

        for update in stats:
            name = update.path["name"]
            print(f"Interface {name!r} is {update.value}")


if __name__ == "__main__":
    fy.run(main())
