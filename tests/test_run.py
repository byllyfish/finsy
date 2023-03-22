import asyncio
import logging

import pytest

import finsy as fy
from finsy.test.p4runtime_server import P4RuntimeServer


def test_run():
    "Test the finsy.run() helper function."

    async def _main():
        pass

    fy.run(_main())


def test_run_failfast(unused_tcp_target, caplog):
    "Test the finsy.run() function with a fail_fast switch."
    caplog.set_level(logging.CRITICAL, logger="finsy")

    async def _ready(sw: fy.Switch):
        assert False

    async def _main():
        server = P4RuntimeServer(unused_tcp_target)
        async with server.run():
            opts = fy.SwitchOptions(ready_handler=_ready, fail_fast=True)
            switches = [fy.Switch("sw1", unused_tcp_target, opts)]
            await fy.Controller(switches).run()

    with pytest.raises(SystemExit) as exc:
        fy.run(_main())

    assert exc.value.args[0] == 99
    assert caplog.record_tuples == [
        (
            "finsy",
            50,
            "[] Switch task 'fy:sw1|test_run_failfast.<locals>._ready' failed",
        )
    ]


def test_run_nonfailfast(unused_tcp_target, caplog):
    "Test the finsy.run() function with a non-fail_fast switch."
    caplog.set_level(logging.CRITICAL, logger="finsy")

    async def _ready(sw: fy.Switch):
        assert False

    async def _main():
        server = P4RuntimeServer(unused_tcp_target)
        async with server.run():
            opts = fy.SwitchOptions(ready_handler=_ready, fail_fast=False)
            switches = [fy.Switch("sw1", unused_tcp_target, opts)]
            # Set a timeout of 2 seconds.
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(fy.Controller(switches).run(), 2.0)

    fy.run(_main())

    assert caplog.record_tuples == [
        (
            "finsy",
            50,
            "[] Switch task 'fy:sw1|test_run_nonfailfast.<locals>._ready' failed",
        )
    ]
