import asyncio

import pytest
from finsy.futures import CountdownFuture, wait_for_cancel


async def test_wait_for_cancel():
    "Test the wait_for_cancel() function."

    task = asyncio.create_task(wait_for_cancel())
    await asyncio.sleep(0.1)
    task.cancel()
    assert (await task) is None


async def test_countdown_future():
    "Test a CountdownFuture already counted down."

    called = False

    def _on_cancel():
        nonlocal called
        called = True

    future1 = CountdownFuture()
    await future1.wait(_on_cancel)
    assert not called

    future2 = CountdownFuture()
    future2.increment()
    future2.decrement()
    await future2.wait(_on_cancel)
    assert not called


async def test_countdown_future_wait():
    "Test a CountdownFuture that waits."

    called = False

    def _on_cancel():
        nonlocal called
        called = True

    future1 = CountdownFuture()
    future1.increment()
    task = asyncio.create_task(future1.wait(_on_cancel))
    await asyncio.sleep(0.05)
    future1.decrement()
    assert (await task) is None
    assert not called

    future2 = CountdownFuture()
    future2.increment()
    task = asyncio.create_task(future2.wait(_on_cancel))
    await asyncio.sleep(0.05)
    task.cancel()
    await asyncio.sleep(0.05)
    future2.decrement()  # cancelled task will wait for corresponding decrement

    with pytest.raises(asyncio.CancelledError):
        await task
    assert called  # wait was cancelled
