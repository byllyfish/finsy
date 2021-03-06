from pathlib import Path

import pytest
from finsy import pbuf
from finsy.p4entity import (
    P4ActionProfileGroup,
    P4ActionProfileMember,
    P4CloneSessionEntry,
    P4CounterData,
    P4CounterEntry,
    P4DigestList,
    P4DirectCounterEntry,
    P4DirectMeterEntry,
    P4Member,
    P4MeterConfig,
    P4MeterCounterData,
    P4MeterEntry,
    P4MulticastGroupEntry,
    P4PacketIn,
    P4PacketOut,
    P4RegisterEntry,
    P4TableAction,
    P4TableEntry,
    P4TableMatch,
)
from finsy.p4schema import P4Schema
from finsy.proto import p4r

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


def test_table_match4():
    "Test TableMatch class with scalar LPM type."

    match = P4TableMatch(dstAddr=1)
    table = _SCHEMA.tables["ipv4_lpm"]
    msgs = match.encode(table)

    assert [pbuf.to_dict(msg) for msg in msgs] == [
        {
            "field_id": 1,
            "lpm": {"prefix_len": 32, "value": "AQ=="},
        }
    ]
    assert P4TableMatch(dstAddr=(1, 32)) == P4TableMatch.decode(msgs, table)


def test_table_action1():
    "Test TableAction class."

    action = P4TableAction("ipv4_forward", dstAddr=0x0A000001, port=1)
    table = _SCHEMA.tables["ipv4_lpm"]
    msg = action.encode_table_action(table)

    assert pbuf.to_dict(msg) == {
        "action": {
            "action_id": 28792405,
            "params": [
                {"param_id": 1, "value": "CgAAAQ=="},
                {"param_id": 2, "value": "AQ=="},
            ],
        }
    }
    assert action == P4TableAction.decode_table_action(msg, table)


def test_table_action2():
    "Test TableAction class with missing argument."

    action = P4TableAction("ipv4_forward", port=1)  # missing 'dstAddr'
    table = _SCHEMA.tables["ipv4_lpm"]

    with pytest.raises(ValueError, match="missing parameters {'dstAddr'}"):
        action.encode_table_action(table)


def test_table_action3():
    "Test TableAction class with incorrect argument name."

    action = P4TableAction("ipv4_forward", dstAddr=0x0A000001, prt=1)
    table = _SCHEMA.tables["ipv4_lpm"]

    with pytest.raises(ValueError, match="no action parameter named 'prt'"):
        action.encode_table_action(table)


def test_table_action4():
    "Test TableAction class with extra argument name."

    action = P4TableAction("ipv4_forward", dstAddr=0x0A000001, port=1, extra=0)
    table = _SCHEMA.tables["ipv4_lpm"]

    with pytest.raises(ValueError, match="no action parameter named 'extra'"):
        action.encode_table_action(table)


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


def test_action_profile_member1():
    "Test P4ActionProfileMember class."

    entry = P4ActionProfileMember()
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {"action_profile_member": {}}
    assert entry == P4ActionProfileMember.decode(msg, _SCHEMA)


def test_action_profile_member2():
    "Test P4ActionProfileMember class."

    entry = P4ActionProfileMember(
        action_profile_id=1,
        member_id=2,
        action=P4TableAction("ipv4_forward", port=1, dstAddr=2),
    )
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {
        "action_profile_member": {
            "action": {
                "action_id": 28792405,
                "params": [
                    {"param_id": 2, "value": "AQ=="},
                    {"param_id": 1, "value": "Ag=="},
                ],
            },
            "action_profile_id": 1,
            "member_id": 2,
        }
    }
    assert entry == P4ActionProfileMember.decode(msg, _SCHEMA)


def test_action_profile_group1():
    "Test P4ActionProfileGroup class."

    entry = P4ActionProfileGroup()
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {"action_profile_group": {}}
    assert entry == P4ActionProfileGroup.decode(msg, _SCHEMA)


def test_action_profile_group2():
    "Test P4ActionProfileGroup class."

    entry = P4ActionProfileGroup(
        action_profile_id=1,
        group_id=2,
        max_size=3,
        members=[
            P4Member(member_id=1, weight=(3, b"abc")),
            P4Member(member_id=2, weight=(3, 9)),
        ],
    )
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {
        "action_profile_group": {
            "action_profile_id": 1,
            "group_id": 2,
            "max_size": 3,
            "members": [
                {"member_id": 1, "watch_port": "YWJj", "weight": 3},
                {"member_id": 2, "watch": 9, "weight": 3},
            ],
        }
    }
    assert entry == P4ActionProfileGroup.decode(msg, _SCHEMA)


def test_meter_entry1():
    "Test P4MeterEntry class."

    entry = P4MeterEntry()
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {"meter_entry": {}}
    assert entry == P4MeterEntry.decode(msg, _SCHEMA)


def test_meter_entry2():
    "Test P4MeterEntry class."

    entry = P4MeterEntry(
        meter_id=1,
        index=2,
        config=P4MeterConfig(cir=1, cburst=2, pir=3, pburst=4),
        counter_data=P4MeterCounterData(
            green=P4CounterData(byte_count=1, packet_count=2),
            yellow=P4CounterData(byte_count=1, packet_count=2),
            red=P4CounterData(byte_count=1, packet_count=2),
        ),
    )
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {
        "meter_entry": {
            "config": {"cburst": "2", "cir": "1", "pburst": "4", "pir": "3"},
            "counter_data": {
                "green": {"byte_count": "1", "packet_count": "2"},
                "red": {"byte_count": "1", "packet_count": "2"},
                "yellow": {"byte_count": "1", "packet_count": "2"},
            },
            "index": {"index": "2"},
            "meter_id": 1,
        }
    }
    assert entry == P4MeterEntry.decode(msg, _SCHEMA)


def test_direct_meter_entry1():
    "Test P4MeterEntry class."

    entry = P4DirectMeterEntry(P4TableEntry())
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {"direct_meter_entry": {"table_entry": {}}}
    assert entry == P4DirectMeterEntry.decode(msg, _SCHEMA)


def test_direct_meter_entry2():
    "Test P4MeterEntry class."

    entry = P4DirectMeterEntry(
        P4TableEntry(
            "ipv4_lpm",
            match=P4TableMatch(dstAddr=(167772160, 24)),
        ),
        config=P4MeterConfig(
            cir=1,
            cburst=2,
            pir=3,
            pburst=4,
        ),
        counter_data=P4MeterCounterData(
            green=P4CounterData(byte_count=1, packet_count=2),
            yellow=P4CounterData(byte_count=1, packet_count=2),
            red=P4CounterData(byte_count=1, packet_count=2),
        ),
    )
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {
        "direct_meter_entry": {
            "config": {
                "cburst": "2",
                "cir": "1",
                "pburst": "4",
                "pir": "3",
            },
            "counter_data": {
                "green": {"byte_count": "1", "packet_count": "2"},
                "red": {"byte_count": "1", "packet_count": "2"},
                "yellow": {"byte_count": "1", "packet_count": "2"},
            },
            "table_entry": {
                "match": [
                    {"field_id": 1, "lpm": {"prefix_len": 24, "value": "CgAAAA=="}}
                ],
                "table_id": 37375156,
            },
        }
    }
    assert entry == P4DirectMeterEntry.decode(msg, _SCHEMA)


def test_counter_entry1():
    "Test P4CounterEntry class."

    entry = P4CounterEntry()
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {"counter_entry": {}}
    assert entry == P4CounterEntry.decode(msg, _SCHEMA)


def test_counter_entry2():
    "Test P4CounterEntry class."

    entry = P4CounterEntry(
        1,
        index=2,
        data=P4CounterData(byte_count=1, packet_count=2),
    )
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {
        "counter_entry": {
            "counter_id": 1,
            "data": {"byte_count": "1", "packet_count": "2"},
            "index": {"index": "2"},
        }
    }
    assert entry == P4CounterEntry.decode(msg, _SCHEMA)


def test_direct_counter_entry1():
    "Test P4CounterEntry class."

    entry = P4DirectCounterEntry()
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {"direct_counter_entry": {}}
    assert entry == P4DirectCounterEntry.decode(msg, _SCHEMA)


def test_direct_counter_entry2():
    "Test P4CounterEntry class."

    entry = P4DirectCounterEntry(
        table_entry=P4TableEntry(
            "ipv4_lpm",
            match=P4TableMatch(dstAddr=(167772160, 24)),
        ),
        data=P4CounterData(byte_count=1, packet_count=2),
    )
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {
        "direct_counter_entry": {
            "data": {"byte_count": "1", "packet_count": "2"},
            "table_entry": {
                "match": [
                    {
                        "field_id": 1,
                        "lpm": {"prefix_len": 24, "value": "CgAAAA=="},
                    }
                ],
                "table_id": 37375156,
            },
        }
    }
    assert entry == P4DirectCounterEntry.decode(msg, _SCHEMA)


def test_register_entry0():
    "Test P4RegisterEntry class."

    entry = P4RegisterEntry()
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {"register_entry": {}}
    assert entry == P4RegisterEntry.decode(msg, _SCHEMA)


def test_register_entry1():
    "Test P4RegisterEntry class."

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


def test_multicast_group_entry1():
    "Test P4MulticastEntry."

    entry = P4MulticastGroupEntry()
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {
        "packet_replication_engine_entry": {
            "multicast_group_entry": {},
        }
    }
    assert entry == P4MulticastGroupEntry.decode(msg, _SCHEMA)


def test_clone_session_entry1():
    "Test P4CloneSessionEntry."

    entry = P4CloneSessionEntry()
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {
        "packet_replication_engine_entry": {
            "clone_session_entry": {},
        }
    }
    assert entry == P4CloneSessionEntry.decode(msg, _SCHEMA)


def test_packet_out1():
    "Test P4PacketOut class."

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

    assert entry["egress_port"] == 1
    assert (
        repr(entry)
        == "PacketOut(metadata={'egress_port': 1, '_pad': 0}, payload=h'616263')"
    )


def test_packet_out2():
    "Test P4PacketOut class with missing argument name."

    entry = P4PacketOut(b"abc", egress_port=1)

    with pytest.raises(ValueError, match="missing parameter '_pad'"):
        entry.encode_update(_SCHEMA)


def test_packet_out3():
    "Test P4PacketOut class with wrong argument name."

    entry = P4PacketOut(b"abc", ingress_port=1, _pad=0)

    with pytest.raises(ValueError, match="missing parameter 'egress_port'"):
        entry.encode_update(_SCHEMA)


def test_packet_out4():
    "Test P4PacketOut class with extra argument name."

    entry = P4PacketOut(b"abc", egress_port=1, _pad=0, extra=1)

    with pytest.raises(ValueError, match="extra parameters {'extra'}"):
        entry.encode_update(_SCHEMA)


def test_packet_in1():
    "Test P4PacketIn class with no metadata."

    data = pbuf.from_text(
        r"""
        packet {
            payload: "abc"
        }
        """,
        p4r.StreamMessageResponse,
    )

    packet = P4PacketIn.decode(data, _SCHEMA)

    assert packet.payload == b"abc"
    assert packet.metadata == {}
    assert repr(packet) == "PacketIn(payload=h'616263')"


def test_packet_in2():
    "Test P4PacketIn class with metadata."

    data = pbuf.from_text(
        r"""
        packet {
            payload: "abc"
            metadata { metadata_id: 1 value: "a" }
            metadata { metadata_id: 2 value: "b" }
        }
        """,
        p4r.StreamMessageResponse,
    )

    packet = P4PacketIn.decode(data, _SCHEMA)

    assert packet.payload == b"abc"
    assert packet.metadata == {"_pad": 98, "ingress_port": 97}
    assert packet["ingress_port"] == 97
    assert (
        repr(packet)
        == "PacketIn(metadata={'ingress_port': 97, '_pad': 98}, payload=h'616263')"
    )


def test_digest_list1():
    "Test P4DigestList."

    digest_list = P4DigestList(
        "digest_name",
        list_id=1,
        timestamp=2,
        data=[
            {"a": 1},
            {"a": 2},
            {"a": 3},
        ],
    )

    assert len(digest_list) == 3
    assert list(digest_list) == digest_list.data
    assert digest_list[0] == {"a": 1}
