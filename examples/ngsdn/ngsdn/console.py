"Implements a simple async command REPL."

import asyncio
import shlex
import sys
from typing import AsyncIterator

import finsy as fy


async def run_console(controller: fy.Controller):
    "Run the REPL for the console."

    print("Welcome to the ngsdn demo console.")

    async for cmd in _read_prompt("ngsdn>"):
        await _run_command(controller, cmd)


async def _run_command(controller: fy.Controller, cmd: list[str]):
    "Run a single command."

    if cmd[0] in _COMMANDS:
        try:
            func = _COMMANDS[cmd[0]]
            await func(controller, cmd[1:])
        except Exception as ex:
            print(f"{cmd[0]}: {ex}")

    else:
        print(f"unknown command: {cmd[0]!r}")


async def _help(_controller: fy.Controller, args: list[str]):
    "Display list of commands."

    for cmd, func in _COMMANDS.items():
        doc = func.__doc__ or ""
        print(f"{cmd:<14} - {doc.strip()}")


async def _devices(controller: fy.Controller, args: list[str]):
    "Display list of devices."

    for switch in controller:
        status = "UP" if switch.is_up else "DOWN"
        primary = "PRIMARY" if switch.is_primary else "BACKUP"
        print(f"{switch.name:<16} {status:>4} {primary:<7}  {switch.address}")


async def _srv6_insert(controller: fy.Controller, args: list[str]):
    "Insert source route entry into srv6_transit table."

    match args:
        case [device_name, s1, s2, s3]:
            entry = fy.P4TableEntry(
                "srv6_transit",
                match=fy.P4TableMatch(dst_addr=s3),
                action=fy.P4TableAction("srv6_t_insert_3", s1=s1, s2=s2, s3=s3),
            )
        case [device_name, s1, s2]:
            entry = fy.P4TableEntry(
                "srv6_transit",
                match=fy.P4TableMatch(dst_addr=s2),
                action=fy.P4TableAction("srv6_t_insert_2", s1=s1, s2=s2),
            )
        case _:
            raise ValueError("srv6-insert <device> <seg1> <seg2> <seg3>?")

    switch = controller.get(device_name)
    if switch is None:
        raise ValueError(f"no such device: {device_name}")

    if switch.is_primary:
        # Insert or replace the entity if it already exists.
        await switch.delete([entry], strict=False)
        await switch.insert([entry])
    else:
        raise ValueError(f"Switch {switch.name!r} is not primary.")


async def _srv6_clear(controller: fy.Controller, args: list[str]):
    "Clear all entries in srv6_transit table."

    match args:
        case [device]:
            switch = controller[device]
            entry = fy.P4TableEntry("srv6_transit")
            await switch.delete_all([entry])
        case _:
            print("srv6-clear <device>")


_COMMANDS = {
    "help": _help,
    "devices": _devices,
    "srv6-insert": _srv6_insert,
    "srv6-clear": _srv6_clear,
}


async def _read_prompt(prompt: str) -> AsyncIterator[list[str]]:
    """Display a prompt and asynchronously read commands from stdin.

    FIXME: For output, we use `print` which may block the event loop.
    """

    reader = asyncio.StreamReader()
    await asyncio.get_running_loop().connect_read_pipe(
        lambda: asyncio.StreamReaderProtocol(reader),
        sys.stdin,
    )

    print(prompt, end=" ", flush=True)

    async for line in reader:
        try:
            result = shlex.split(line.decode())
            if result:
                yield result
        except ValueError as ex:
            print(f"error: {ex}")

        print(prompt, end=" ", flush=True)
