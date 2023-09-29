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
    with pytest.raises(RuntimeError, match="controller does not exist"):
        Controller.current()

    async with controller:
        assert controller.running
        assert Controller.current() == controller

        await asyncio.sleep(0.01)

    assert not controller.running
    with pytest.raises(RuntimeError, match="controller does not exist"):
        Controller.current()


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
            event = controller.remove(sw)
            await event.wait()
            assert event.is_set()

        assert len(controller) == 0
        assert len(controller._pending_removal) == 0


def test_controller_sync():
    "Test that add/remove still work in synchronous land."
    N = 3
    NAMES = {"sw0", "sw1", "sw2"}

    controller = Controller([])
    assert len(controller) == 0
    assert not controller.running

    for i in range(N):
        sw = Switch(f"sw{i}", "127.0.0.1:50001")
        controller.add(sw)
        assert controller.get(f"sw{i}") is sw

    assert len(controller) == N

    names = {sw.name for sw in controller}
    assert names == NAMES

    for name in names:
        sw = controller[name]
        event = controller.remove(sw)
        assert event.is_set()

    assert len(controller) == 0
    assert len(controller._pending_removal) == 0
