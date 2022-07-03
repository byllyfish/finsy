from pathlib import Path

import pytest
from finsy import pbuf
from finsy.p4entity import (
    P4PacketOut,
    P4RegisterEntry,
    P4TableAction,
    P4TableEntry,
    P4TableMatch,
)
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


def test_table_match3():
    "Test TableMatch class with missing field."

    match = P4TableMatch()
    table = _SCHEMA.tables["ipv4_lpm"]
    msgs = match.encode(table)

    assert [pbuf.to_dict(msg) for msg in msgs] == []
    assert match == P4TableMatch.decode(msgs, table)


def test_table_action1():
    "Test TableAction class."

    action = P4TableAction("ipv4_forward", dstAddr=0x0A000001, port=1)
    table = _SCHEMA.tables["ipv4_lpm"]
    msg = action.encode(table)

    assert pbuf.to_dict(msg) == {
        "action": {
            "action_id": 28792405,
            "params": [
                {"param_id": 1, "value": "CgAAAQ=="},
                {"param_id": 2, "value": "AQ=="},
            ],
        }
    }
    assert action == P4TableAction.decode(msg, table)


def test_table_action2():
    "Test TableAction class with missing argument."

    action = P4TableAction("ipv4_forward", port=1)  # missing 'dstAddr'
    table = _SCHEMA.tables["ipv4_lpm"]

    with pytest.raises(ValueError, match="missing parameters {'dstAddr'}"):
        action.encode(table)


def test_table_action3():
    "Test TableAction class with incorrect argument name."

    action = P4TableAction("ipv4_forward", dstAddr=0x0A000001, prt=1)
    table = _SCHEMA.tables["ipv4_lpm"]

    with pytest.raises(ValueError, match="no action parameter named 'prt'"):
        action.encode(table)


def test_table_action4():
    "Test TableAction class with extra argument name."

    action = P4TableAction("ipv4_forward", dstAddr=0x0A000001, port=1, extra=0)
    table = _SCHEMA.tables["ipv4_lpm"]

    with pytest.raises(ValueError, match="no action parameter named 'extra'"):
        action.encode(table)


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


def test_packet_out1():
    "Test PacketOut class."

    entry = P4PacketOut(b"abc", egress_port=1, _pad=0)
    msg = entry.encode_update(_SCHEMA)

    assert pbuf.to_dict(msg) == {
        "packet": {
            "metadata": [
                {"metadata_id": 1, "value": "AQ=="},
                {"metadata_id": 2, "value": "AA=="},
            ],
            "payload": "YWJj",
        }
    }


def test_packet_out2():
    "Test PacketOut class with missing argument name."

    entry = P4PacketOut(b"abc", egress_port=1)

    with pytest.raises(ValueError, match="missing parameter '_pad'"):
        entry.encode_update(_SCHEMA)


def test_packet_out3():
    "Test PacketOut class with wrong argument name."

    entry = P4PacketOut(b"abc", ingress_port=1, _pad=0)

    with pytest.raises(ValueError, match="missing parameter 'egress_port'"):
        entry.encode_update(_SCHEMA)


def test_packet_out4():
    "Test PacketOut class with extra argument name."

    entry = P4PacketOut(b"abc", egress_port=1, _pad=0, extra=1)

    with pytest.raises(ValueError, match="extra parameters {'extra'}"):
        entry.encode_update(_SCHEMA)