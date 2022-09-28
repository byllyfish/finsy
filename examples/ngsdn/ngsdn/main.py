import logging
from pathlib import Path

import prometheus_client
from finsy import Controller

from .app import load_netcfg
from .console import run_console

NETCFG = Path("netcfg.json")


def setup():
    "Set up logging and our prometheus client."

    logging.basicConfig(
        level=logging.INFO,
        format="%(created).03f %(levelname)s %(name)s %(message)s",
    )
    prometheus_client.start_http_server(9091)


async def main():
    "Run the controller."
    setup()

    controller = Controller(load_netcfg(NETCFG))
    async with controller:
        await run_console(controller)
