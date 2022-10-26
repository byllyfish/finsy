import os

import pytest
from finsy.gnmiclient import gNMIClient
from finsy.test.gnmi_server import gNMIServer
from finsy.test.p4runtime_server import P4RuntimeServer

# Set environment variable to "skip" to skip tests that rely on GRPC servers.

TEST_GNMI_TARGET = os.environ.get("FINSY_TEST_GNMI_TARGET", "")
TEST_P4RUNTIME_TARGET = os.environ.get("FINSY_TEST_P4RUNTIME_TARGET", "")


@pytest.fixture
async def gnmi_server_target():
    "Fixture to provide a gNMI server for testing."

    if TEST_GNMI_TARGET.lower() == "skip":
        pytest.skip("FINSY_TEST_GNMI_TARGET=skip")

    if TEST_GNMI_TARGET:
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
    "Fixture to provide a P4Runtime server for testing."

    if TEST_P4RUNTIME_TARGET.lower() == "skip":
        pytest.skip("FINSY_TEST_P4RUNTIME_TARGET=skip")

    if TEST_P4RUNTIME_TARGET:
        yield TEST_P4RUNTIME_TARGET
    else:
        target = "127.0.0.1:19559"
        server = P4RuntimeServer(target)
        async with server.run():
            yield target
