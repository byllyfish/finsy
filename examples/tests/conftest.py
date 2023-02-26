import asyncio
import importlib
import sys
from pathlib import Path

import pytest
from shellous import sh
from shellous.harvest import harvest_results

from finsy.test import demonet as dn


@pytest.fixture(scope="module")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


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


@pytest.fixture(scope="module")
async def demonet(request):
    "Fixture to run demonet based on config in module."
    config = _get_config(request.module.DEMONET)

    async with dn.DemoNet(config) as net:
        yield net


@pytest.fixture
def python():
    return sh(sys.executable).stdin(sh.CAPTURE).stderr(sh.INHERIT).env(PYTHONPATH="..")
