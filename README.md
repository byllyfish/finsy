# 🐟 Finsy P4Runtime Framework

[![pypi](https://img.shields.io/pypi/v/finsy)](https://pypi.org/project/finsy/) [![ci](https://github.com/byllyfish/finsy/actions/workflows/ci.yml/badge.svg)](https://github.com/byllyfish/finsy/actions/workflows/ci.yml) [![codecov](https://codecov.io/gh/byllyfish/finsy/branch/main/graph/badge.svg?token=8RPYWRXNGS)](https://codecov.io/gh/byllyfish/finsy)

Finsy is a P4Runtime controller framework written in Python using asyncio.

```python
import asyncio
import finsy as fy

async def main():
    async with fy.Switch("sw1", "127.0.0.1:50001") as sw1:
        print(sw1.p4info)

asyncio.run(main())
```

## Multiple Switches

With Finsy, you can write a P4Runtime controller that manages multiple switches.

Each switch is managed by an async `ready_handler` function. Your `ready_handler` function can read or 
update various P4Runtime entities in the switch. It can also create tasks to listen for 
packets or digests.

```python
async def ready_handler(sw: fy.Switch):
    await sw.delete_all()
    await sw.insert(fy.P4MulticastGroupEntry(1, replicas=[1, 2, 3, 255]))

    async for packet in sw.read_packets():
        print(packet)
```

Use the `SwitchOptions` class to specify each switch's settings, including the p4info/p4blob and ready_handler. Use the `Controller` class to drive multiple switch connections. Each switch will call back
into your ready_handler function after the P4Runtime connection is established.

```python
from pathlib import Path

options = fy.SwitchOptions(
    p4info=Path("example.p4info.txt"),
    p4blob=Path("example.json"),
    ready_handler=ready_handler,
)
controller = fy.Controller([
    fy.Switch("sw1", "127.0.0.1:50001", options),
    fy.Switch("sw2", "127.0.0.1:50002", options),
    fy.Switch("sw3", "127.0.0.1:50003", options),
])

asyncio.run(controller.run())
```

For more examples, see the examples directory.
