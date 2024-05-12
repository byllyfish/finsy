import json
from pathlib import Path
from typing import Iterator

from finsy import Switch, SwitchOptions

from . import netcfg
from .host import HostManager
from .link import LinkManager
from .route import RouteManager
from .stat import StatManager

P4SRC_DIR = Path(__file__).parent / "p4"
P4INFO = P4SRC_DIR / "main.p4info.txtpb"
P4BLOB = P4SRC_DIR / "main.json"


async def _ready_handler(sw: Switch):
    "The ready_handler is the entry point when finsy controls a switch."
    # Ignore switch if this is a backup.
    if not sw.is_primary:
        return

    # Delete all runtime state from the switch. A real program would read
    # the state of the switch and attempt to merge changes into it while
    # minimizing disruption to the data plane.
    await sw.delete_all()

    # Create a task for each configured sub-manager.
    for manager in sw.stash.values():
        sw.create_task(manager.run())


def load_netcfg(config: Path) -> Iterator[Switch]:
    "Return iterator of switches configured using `netcfg` object."
    cfg = json.loads(config.read_bytes())

    options = SwitchOptions(
        p4info=P4INFO,
        p4blob=P4BLOB,
        ready_handler=_ready_handler,
        configuration=cfg,
        fail_fast=True,
    )

    for name, address, device_id in netcfg.configured_devices(cfg):
        switch = Switch(name, address, options(device_id=device_id))

        # Configure and stash the switch sub-managers.
        switch.stash.update(
            host=HostManager(switch),
            route=RouteManager(switch),
            link=LinkManager(switch),
            stat=StatManager(switch),
        )

        yield switch
