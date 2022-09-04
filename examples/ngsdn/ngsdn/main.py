import asyncio
import logging
from pathlib import Path

import prometheus_client
from finsy import Controller

from .app import load_netcfg

NETCFG = Path("demonet/netcfg.json")


def setup():
    "Set up logging and our prometheus client."

    logging.basicConfig(
        level=logging.INFO,
        format="%(created).03f %(levelname)s %(name)s %(message)s",
    )
    prometheus_client.start_http_server(9091)


def main():
    "Run the controller."
    setup()

    switches = load_netcfg(NETCFG)
    controller = Controller(switches)
    asyncio.run(controller.run())
