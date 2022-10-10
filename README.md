# 🐟 Finsy P4Runtime Library

[![pypi](https://img.shields.io/pypi/v/finsy)](https://pypi.org/project/finsy/) [![ci](https://github.com/byllyfish/finsy/actions/workflows/ci.yml/badge.svg)](https://github.com/byllyfish/finsy/actions/workflows/ci.yml) [![codecov](https://codecov.io/gh/byllyfish/finsy/branch/main/graph/badge.svg?token=8RPYWRXNGS)](https://codecov.io/gh/byllyfish/finsy)

Finsy is a [P4Runtime](https://p4.org/p4-spec/p4runtime/main/P4Runtime-Spec.html) controller library written in Python using asyncio. Finsy includes support for [gNMI](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md).

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

When you write P4Runtime updates to the switch, you use a unary operator (+, -, \~) to specify the operation:
INSERT (+), DELETE (-) or MODIFY (\~).

```python
async def ready_handler(sw: fy.Switch):
    await sw.delete_all()
    await sw.write(
        [
            # Insert multicast group with ports 1, 2, 3 and CONTROLLER.
            +fy.P4MulticastGroupEntry(1, replicas=[1, 2, 3, 255]),
            # Modify default table entry to flood all unmatched packets.
            ~fy.P4TableEntry(
                "ipv4",
                action=fy.P4TableAction("flood"),
                is_default_action=True,
            ),
        ]
    )

    async for packet in sw.read_packets():
        print(f"{sw.name}: {packet}")
```

Use the `SwitchOptions` class to specify each switch's settings, including the p4info/p4blob and 
`ready_handler`. Use the `Controller` class to drive multiple switch connections. Each switch will call back
into your `ready_handler` function after the P4Runtime connection is established.

```python
from pathlib import Path

options = fy.SwitchOptions(
    p4info=Path("hello.p4info.txt"),
    p4blob=Path("hello.json"),
    ready_handler=ready_handler,
)

controller = fy.Controller([
    fy.Switch("sw1", "127.0.0.1:50001", options),
    fy.Switch("sw2", "127.0.0.1:50002", options),
    fy.Switch("sw3", "127.0.0.1:50003", options),
])

asyncio.run(controller.run())
```

If the switch disconnects or its role changes to backup, the task running your `ready_handler` 
(and any tasks it spawned) will be cancelled and the `ready_handler` will begin again.

For more examples, see the [examples](https://github.com/byllyfish/finsy/tree/main/examples) directory.
