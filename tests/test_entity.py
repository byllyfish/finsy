from pathlib import Path

import pytest
from finsy import pbuf
from finsy.p4entity import *
from finsy.p4schema import P4Schema

_P4INFO_TEST_DIR = Path(__file__).parent / "test_data/p4info"
_SCHEMA = P4Schema(_P4INFO_TEST_DIR / "basic.p4.p4info.txt")


def test_table_match1():
    "Test TableMatch class."

    match = P4TableMatch(dstAddr=(167772160, 24))
    table = _SCHEMA.tables["ipv4_lpm"]
    msgs = match.encode(table)

    assert [pbuf.to_dict(msg) for msg in msgs] == [
        {
            "field_id": 1,
            "lpm": {"prefix_len": 24, "value": "CgAAAA=="},
        }
    ]
    assert match == P4TableMatch.decode(msgs, table)


def test_table_match2():
    "Test TableMatch class."

    match = P4TableMatch(x=1)
    table = _SCHEMA.tables["ipv4_lpm"]
    with pytest.raises(ValueError, match="no match field named 'x'"):
        match.encode(table)


def test_table_action1():
    "Test TableAction class."

    action = P4TableAction("ipv4_forward", port=1)  # FIXME: missing parameter
    table = _SCHEMA.tables["ipv4_lpm"]
    msg = action.encode(table)

    assert pbuf.to_dict(msg) == {
        "action": {
            "action_id": 28792405,
            "params": [
                {"param_id": 2, "value": "AQ=="},
            ],
        }
    }
    assert action == P4TableAction.decode(msg, table)


def test_table_entry1():
    "Test TableEntry class."

    entry = P4TableEntry()
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {"table_entry": {}}
    assert entry == P4TableEntry.decode(msg, _SCHEMA)


def test_table_entry2():
    "Test TableEntry class."

    entry = P4TableEntry("ipv4_lpm")
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {"table_entry": {"table_id": 37375156}}
    assert entry == P4TableEntry.decode(msg, _SCHEMA)


def test_table_entry3():
    "Test TableEntry class."

    entry = P4TableEntry(
        "ipv4_lpm",
        match=P4TableMatch(dstAddr=(167772160, 24)),
        action=P4TableAction("ipv4_forward", dstAddr=1108152157446, port=1),
    )
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {
        "table_entry": {
            "action": {
                "action": {
                    "action_id": 28792405,
                    "params": [
                        {"param_id": 1, "value": "AQIDBAUG"},
                        {"param_id": 2, "value": "AQ=="},
                    ],
                }
            },
            "match": [
                {
                    "field_id": 1,
                    "lpm": {"prefix_len": 24, "value": "CgAAAA=="},
                }
            ],
            "table_id": 37375156,
        }
    }
    assert entry == P4TableEntry.decode(msg, _SCHEMA)


def test_register_entry1():
    "Test RegisterEntry class."

    entry = P4RegisterEntry("counter_bloom_filter", index=1, data=1)
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {
        "register_entry": {
            "data": {"bitstring": "AQ=="},
            "index": {"index": "1"},
            "register_id": 369140025,
        }
    }
    assert entry == P4RegisterEntry.decode(msg, _SCHEMA)


def test_register_entry2():
    "Test RegisterEntry class with no Index."

    entry = P4RegisterEntry("counter_bloom_filter", data=1)
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {
        "register_entry": {
            "data": {"bitstring": "AQ=="},
            "register_id": 369140025,
        }
    }
    assert entry == P4RegisterEntry.decode(msg, _SCHEMA)
