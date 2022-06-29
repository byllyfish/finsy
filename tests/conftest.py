import os

import pytest
from finsy.gnmiclient import gNMIClient

GNMI_TARGET = os.environ.get("FINSY_TEST_GNMI_TARGET", "127.0.0.1:50001")


@pytest.fixture
async def gnmi_client():
    "Fixture to test GNMI at a pre-specified target."

    if not GNMI_TARGET:
        pytest.skip("gNMI target is not available.")

    async with gNMIClient(GNMI_TARGET) as client:
        yield client
