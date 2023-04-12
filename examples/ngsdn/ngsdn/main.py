from pathlib import Path

import prometheus_client

from finsy import Controller

from .app import load_netcfg
from .console import run_console

NETCFG = Path(__file__).parent.parent / "netcfg.json"


async def main():
    "Run the controller."
    prometheus_client.start_http_server(9091)

    controller = Controller(load_netcfg(NETCFG))
    async with controller:
        await run_console(controller)
