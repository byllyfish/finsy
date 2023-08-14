# Finsy P4Runtime Controller Library 

[![pypi](https://img.shields.io/pypi/v/finsy)](https://pypi.org/project/finsy/ "View Finsy on PyPI") [![documentation](https://img.shields.io/badge/-documentation-informational?logo=readme&logoColor=white)](https://byllyfish.github.io/finsy/finsy.html "View the latest API docs") [![ci](https://github.com/byllyfish/finsy/actions/workflows/ci.yml/badge.svg)](https://github.com/byllyfish/finsy/actions/workflows/ci.yml "View the latest CI builds") [![codecov](https://codecov.io/gh/byllyfish/finsy/branch/main/graph/badge.svg?token=8RPYWRXNGS)](https://codecov.io/gh/byllyfish/finsy "View the latest code coverage stats") [![codespace](https://img.shields.io/badge/codespace-blueviolet?logo=github)](https://codespaces.new/byllyfish/finsy "Open Finsy in a Github Codespace")

Finsy is a [P4Runtime](https://p4.org/p4-spec/p4runtime/main/P4Runtime-Spec.html) controller library written in Python using [asyncio](https://docs.python.org/3/library/asyncio.html). Finsy includes support for [gNMI](https://github.com/openconfig/reference/blob/master/rpc/gnmi/gnmi-specification.md).

Check out the [examples](https://github.com/byllyfish/finsy/tree/main/examples) directory
for some demonstration programs.

## Installation

Finsy requires Python 3.10 or later. To install the latest version, type `pip install finsy`.

## P4Runtime Scripts

With Finsy, you can write a Python script that reads/writes P4Runtime entities for a single switch.

Here is a complete example that retrieves the P4Info from a switch:

```python
import finsy as fy

async def main():
    async with fy.Switch("sw1", "127.0.0.1:50001") as sw1:
        # Print out a description of the switch's P4Info, if one is configured.
        print(sw1.p4info)

fy.run(main())
```

Here is another example that prints out all non-default table entries.

```python
import finsy as fy

async def main():
    async with fy.Switch("sw1", "127.0.0.1:50001") as sw1:
        # Do a wildcard read for table entries.
        async for entry in sw1.read(fy.P4TableEntry()):
            print(entry)

fy.run(main())
```

## P4Runtime Controller

You can also write a P4Runtime controller that manages multiple switches independently. Your controller
can react to events from the Switch by changing the contents of P4 tables.

Each switch is managed by an async `ready_handler` function. Your `ready_handler` function can read or 
update various P4Runtime entities in the switch. It can also create tasks to listen for 
packets or digests.

When you write P4Runtime updates to the switch, you use a unary operator (+, -, \~) to specify the operation:
INSERT (+), DELETE (-) or MODIFY (\~).

```python
import finsy as fy

async def ready_handler(sw: fy.Switch):
    await sw.delete_all()
    await sw.write(
        [
            # Insert (+) multicast group with ports 1, 2, 3 and CONTROLLER.
            +fy.P4MulticastGroupEntry(1, replicas=[1, 2, 3, 255]),
            # Modify (~) default table entry to flood all unmatched packets.
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

fy.run(controller.run())
```

Your `ready_handler` can spawn concurrent tasks with the `Switch.create_task` method. Tasks
created this way will have their lifetimes managed by the switch object.

If the switch disconnects or its role changes to backup, the task running your `ready_handler` 
(and any tasks it spawned) will be cancelled and the `ready_handler` will begin again.

For more examples, see the [examples](https://github.com/byllyfish/finsy/tree/main/examples) directory.

## Development and Testing

Perform these steps to set up your local environment for Finsy development, or try 
the [codespace](https://codespaces.new/byllyfish/finsy). Finsy requires Python 3.10 or 
later. If [poetry](https://python-poetry.org/) is not installed, follow 
[these directions](https://python-poetry.org/docs/#installation) to install it.

### Clone and Prepare a Virtual Environment

The `poetry install` command installs all development dependencies into the
virtual environment (venv).

```sh
$ git clone https://github.com/byllyfish/finsy.git
$ cd finsy
$ python3 -m venv .venv
$ poetry install
```

### Run Unit Tests

When you run pytest from the top level of the repository, you will run the unit tests.

```sh
$ poetry run pytest
```

### Run Integration Tests

When you run pytest from within the `examples` directory, you will run the integration
tests instead of the unit tests. The integration tests run the example programs against a
[Mininet](https://github.com/mininet/mininet) network. Docker or podman are required.

```bash
$ cd examples
$ poetry run pytest
```

---
