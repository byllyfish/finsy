import contextlib
import time
from pathlib import Path

import pytest
from finsy import P4TableAction, P4TableEntry, P4TableMatch, Switch, SwitchOptions
from finsy.log import LOGGER, get_setting
from finsy.proto import p4r

P4INFO_TEST_DIR = Path(__file__).parent / "test_data/p4info"

NO_BENCHMARK = get_setting("FINSY_TEST_NO_BENCHMARK")


@pytest.mark.skipif(NO_BENCHMARK, reason="FINSY_TEST_NO_BENCHMARK")
async def test_benchmark_table_entry1(p4rt_server_target):
    "Test writing table entries using P4TableEntry."

    opts = SwitchOptions(p4info=P4INFO_TEST_DIR / "basic.p4.p4info.txt")

    async with Switch("sw1", p4rt_server_target, opts) as sw:
        with _logger_disabled(LOGGER):
            with _timer("entries0"):
                entries1 = _make_entries1()

            with _timer("entries1"):
                await sw.write(entries1)

            entries2 = _make_entries2(sw)
            with _timer("entries2"):
                await sw.write(entries2)

            assert sw._p4client is not None
            req = p4r.WriteRequest(updates=_make_entries2(sw))
            with _timer("entries3"):
                await sw._p4client.request(req)


def _make_entries1():
    return [
        +P4TableEntry(
            "ipv4_lpm",
            match=P4TableMatch(dstAddr=(1024 * i, 32)),
            action=P4TableAction("ipv4_forward", dstAddr=i, port=1),
        )
        for i in range(1, 10001)
    ]


def _make_entries2(sw):
    return [entry.encode_update(sw.p4info) for entry in _make_entries1()]


@contextlib.contextmanager
def _timer(label):
    start = time.perf_counter()
    yield
    end = time.perf_counter()
    print(f"::notice::Benchmark {label!r} took {end - start:0.5f} seconds")


@contextlib.contextmanager
def _logger_disabled(logger):
    level = logger.getEffectiveLevel()
    logger.setLevel("ERROR")
    try:
        yield
    finally:
        logger.setLevel(level)
