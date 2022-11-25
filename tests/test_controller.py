# pyright: reportPrivateUsage=false

import asyncio

import pytest

from finsy import Controller, Switch


async def test_controller_run_empty():
    "Test the empty Finsy Controller class using the run() method."

    controller = Controller([])
    assert len(controller) == 0
    assert controller.get("sw1") is None

    # Helper to stop the Controller so it doesn't run forever.
    async def _stop_later():
        await asyncio.sleep(0.01)
        controller.stop()

    task = asyncio.create_task(_stop_later())
    with pytest.raises(asyncio.CancelledError):
        await controller.run()
    await task

    assert not controller.running


async def test_controller_ctxt_empty():
    "Test the empty Finsy Controller class using the context manager."

    controller = Controller([])
    assert len(controller) == 0
    assert not controller.running

    async with controller:
        assert controller.running
        await asyncio.sleep(0.01)

    assert not controller.running


async def test_controller_ctxt(p4rt_server_target: str):
    "Test Finsy Controller class."

    N = 2
    NAMES = {"sw0", "sw1"}

    controller = Controller([])

    async with controller:
        assert len(controller) == 0

        for i in range(N):
            sw = Switch(f"sw{i}", p4rt_server_target)
            controller.add(sw)
            assert controller.get(f"sw{i}") is sw
            await asyncio.sleep(0.01)

        assert len(controller) == N

        names = {sw.name for sw in controller}
        assert names == NAMES

        for name in names:
            sw = controller[name]
            controller.remove(sw)
            await asyncio.sleep(0.01)

        assert len(controller) == 0
        assert len(controller._removed) == 0
