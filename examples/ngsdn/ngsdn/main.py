import asyncio
import logging
import signal
from pathlib import Path

import prometheus_client
from finsy import Controller

from .app import load_netcfg
from .console import run_console

NETCFG = Path(__file__).parent.parent / "netcfg.json"


def setup():
    "Set up logging and our prometheus client."

    logging.basicConfig(
        level=logging.INFO,
        format="%(created).03f %(levelname)s %(name)s %(message)s",
    )
    prometheus_client.start_http_server(9091)

    # Boilerplate to shutdown cleanly upon SIGTERM signal.
    asyncio.get_running_loop().add_signal_handler(
        signal.SIGTERM,
        lambda task: task.cancel(),
        asyncio.current_task(),
    )


async def main():
    "Run the controller."
    setup()

    controller = Controller(load_netcfg(NETCFG))
    async with controller:
        await run_console(controller)
