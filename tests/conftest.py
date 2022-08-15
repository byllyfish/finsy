import asyncio
import contextlib
import os

import pytest
from finsy.gnmiclient import gNMIClient
from finsy.test.gnmi_server import gNMIServer
from finsy.test.p4runtime_server import P4RuntimeServer

TEST_GNMI_TARGET = os.environ.get("FINSY_TEST_GNMI_TARGET", "")


@pytest.fixture
async def gnmi_server_target():
    if TEST_GNMI_TARGET:
        # If there is already a valid target, do nothing.
        yield TEST_GNMI_TARGET
    else:
        target = "127.0.0.1:51001"
        server = gNMIServer(target)
        async with server.run():
            yield target


@pytest.fixture
async def gnmi_client(gnmi_server_target):
    "Fixture to test GNMI at a pre-specified target."

    async with gNMIClient(gnmi_server_target) as client:
        yield client


@pytest.fixture
async def p4rt_server_target():
    target = "127.0.0.1:19559"
    server = P4RuntimeServer(target)
    async with server.run():
        yield target
