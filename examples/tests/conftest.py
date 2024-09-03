import asyncio
import importlib
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from shellous import sh

from finsy.test import demonet as dn


def _import_module(path: Path):
    "Import module given path to Python source file."
    # Reference: https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
    assert path.suffix == ".py"
    module_name = path.stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    # sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _get_config(value):
    "Retrieve config list for demonet."
    if isinstance(value, Path):
        # Load module at path and obtain its DEMONET value.
        module = _import_module(value)
        return module.DEMONET
    return value


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def demonet(request):
    """Fixture to run demonet based on config in module.

    This async fixture runs once per module in the module-scoped event loop.
    """
    config = _get_config(request.module.DEMONET)

    try:
        async with dn.DemoNet(config) as net:
            # FIXME: wait for switches to be ready
            await asyncio.sleep(0.25)
            yield net

    except RuntimeError as ex:
        pytest.exit(f"DemoNet failure: {ex}")


@pytest.fixture
def python():
    return sh(sys.executable).stdin(sh.CAPTURE).stderr(sh.INHERIT).env(PYTHONPATH="..")
