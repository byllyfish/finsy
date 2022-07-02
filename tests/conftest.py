import os

import pytest
from finsy.gnmiclient import gNMIClient
from finsy.test.gnmi_server import gNMIServer

TEST_GNMI_TARGET = os.environ.get("FINSY_TEST_GNMI_TARGET", "")


@pytest.fixture
async def gnmi_server():
    if TEST_GNMI_TARGET:
        # If there is already a valid target, do nothing.
        yield TEST_GNMI_TARGET
    else:
        default_target = "127.0.0.1:51001"
        server = gNMIServer(default_target)
        async with server.run():
            yield default_target


@pytest.fixture
async def gnmi_client(gnmi_server):
    "Fixture to test GNMI at a pre-specified target."

    async with gNMIClient(gnmi_server) as client:
        yield client
