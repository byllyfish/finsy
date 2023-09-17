from collections import OrderedDict
from pathlib import Path

import pytest

from finsy import pbuf
from finsy.p4entity import (
    P4ActionProfileGroup,
    P4ActionProfileMember,
    P4CloneSessionEntry,
    P4CounterData,
    P4CounterEntry,
    P4DigestEntry,
    P4DigestList,
    P4DigestListAck,
    P4DirectCounterEntry,
    P4DirectMeterEntry,
    P4ExternEntry,
    P4IdleTimeoutNotification,
    P4IndirectAction,
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
    P4ValueSetEntry,
    P4ValueSetMember,
    decode_entity,
    decode_replica,
    decode_stream,
    encode_entities,
    encode_replica,
    encode_updates,
    flatten,
    format_replica,
)
from finsy.p4schema import P4Schema
from finsy.proto import p4r

_P4INFO_TEST_DIR = Path(__file__).parent / "test_data/p4info"
_SCHEMA = P4Schema(_P4INFO_TEST_DIR / "basic.p4.p4info.txt")


def test_flatten():
    "Test the flatten method."
    assert list(flatten([])) == []
    assert list(flatten([None])) == [None]
    assert list(flatten([1, [2, [3]]])) == [1, 2, 3]

    with pytest.raises(TypeError, match="is not iterable"):
        list(flatten(None))


def test_replica1():
    "Test encode_replica and decode_replica functions."
    msg = encode_replica(1)
    assert pbuf.to_dict(msg) == {"egress_port": 1}
    assert decode_replica(msg) == (1, 0)


def test_replica2():
    "Test encode_replica and decode_replica functions"
    msg = encode_replica((1, 2))
    assert pbuf.to_dict(msg) == {"egress_port": 1, "instance": 2}
    assert decode_replica(msg) == (1, 2)


def test_format_replica():
    "Test the format_replica function."
    assert format_replica(1) == "1"
    assert format_replica((1, 0)) == "1"
    assert format_replica((1, 2)) == "1#2"


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
    assert match.format_str(table) == "dstAddr=0xa000000/24"


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


def test_table_match5():
    "Test TableMatch class with sdn_string new type field."
    schema = P4Schema(_P4INFO_TEST_DIR / "sai_unioned.p4info.txt")
    table = schema.tables["mirror_port_to_pre_session_table"]

    match = P4TableMatch(mirror_port="ethernet1/0")
    msgs = match.encode(table)

    assert [pbuf.to_dict(msg) for msg in msgs] == [
        {
            "field_id": 1,
            "exact": {"value": "ZXRoZXJuZXQxLzA="},
        }
    ]
    assert match == P4TableMatch.decode(msgs, table)


def test_table_match_dict():
    "Test TableMatch class with dict methods."
    match1 = P4TableMatch({"x.y": 1})
    match2 = P4TableMatch([("x.y", 1)])
    match3 = P4TableMatch(**{"x.y": 1})
    assert match1 == match2 == match3

    assert len(match1) == 1
    assert list(match1.items()) == [("x.y", 1)]
    assert match1["x.y"] == 1


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
    assert action.format_str(table) == "ipv4_forward(dstAddr=0xa000001, port=0x1)"


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


def test_table_action_call():
    "Test TableAction with __call__ syntax."
    action = P4TableAction("forward")

    action1 = action(dst=1)
    assert action == P4TableAction("forward")  # no change to original
    assert action1 == P4TableAction("forward", dst=1)

    action2 = action1(port=2)
    assert action1 == P4TableAction("forward", dst=1)  # no change to original
    assert action2 == P4TableAction("forward", port=2, dst=1)


def test_indirect_action1():
    "Test P4IndirectAction class."
    action = P4IndirectAction(
        action_set=[
            (1, P4TableAction("ipv4_forward", dstAddr=0x0A000001, port=1)),
            (1, P4TableAction("ipv4_forward", dstAddr=0x0A000001, port=2)),
        ]
    )
    table = _SCHEMA.tables["ipv4_lpm"]

    msg = action.encode_table_action(table)
    assert pbuf.to_dict(msg) == {
        "action_profile_action_set": {
            "action_profile_actions": [
                {
                    "action": {
                        "action_id": 28792405,
                        "params": [
                            {"param_id": 1, "value": "CgAAAQ=="},
                            {"param_id": 2, "value": "AQ=="},
                        ],
                    },
                    "weight": 1,
                },
                {
                    "action": {
                        "action_id": 28792405,
                        "params": [
                            {"param_id": 1, "value": "CgAAAQ=="},
                            {"param_id": 2, "value": "Ag=="},
                        ],
                    },
                    "weight": 1,
                },
            ]
        }
    }

    assert action == P4TableAction.decode_table_action(msg, table)

    assert repr(action) == (
        "P4IndirectAction(action_set=[(1, P4TableAction(name='ipv4_forward', "
        "args={'dstAddr': 167772161, 'port': 1})), (1, "
        "P4TableAction(name='ipv4_forward', args={'dstAddr': 167772161, 'port': "
        "2}))])"
    )
    assert (
        action.format_str(table)
        == "1*ipv4_forward(dstAddr=0xa000001, port=0x1) 1*ipv4_forward(dstAddr=0xa000001, port=0x2)"
    )


def test_indirect_action2():
    "Test P4IndirectAction class."
    action = P4IndirectAction(group_id=123)
    table = _SCHEMA.tables["ipv4_lpm"]

    msg = action.encode_table_action(table)
    assert pbuf.to_dict(msg) == {"action_profile_group_id": 123}

    assert action == P4TableAction.decode_table_action(msg, table)

    assert repr(action) == "P4IndirectAction(group_id=123)"
    assert action.format_str(table) == "__indirect[0x7b]"


def test_indirect_action3():
    "Test P4IndirectAction class."
    action = P4IndirectAction(member_id=345)
    table = _SCHEMA.tables["ipv4_lpm"]

    msg = action.encode_table_action(table)
    assert pbuf.to_dict(msg) == {"action_profile_member_id": 345}

    assert action == P4TableAction.decode_table_action(msg, table)

    assert repr(action) == "P4IndirectAction(member_id=345)"
    assert action.format_str(table) == "__indirect[[0x159]]"


def test_indirect_action4():
    "Test P4IndirectAction class."
    action = P4IndirectAction(
        action_set=[
            ((1, 1), P4TableAction("ipv4_forward", dstAddr=0x0A000001, port=1)),
        ]
    )
    table = _SCHEMA.tables["ipv4_lpm"]

    msg = action.encode_table_action(table)
    assert pbuf.to_dict(msg) == {
        "action_profile_action_set": {
            "action_profile_actions": [
                {
                    "action": {
                        "action_id": 28792405,
                        "params": [
                            {"param_id": 1, "value": "CgAAAQ=="},
                            {"param_id": 2, "value": "AQ=="},
                        ],
                    },
                    "watch_port": "AQ==",
                    "weight": 1,
                },
            ]
        }
    }

    assert action == P4TableAction.decode_table_action(msg, table)

    assert (
        repr(action) == "P4IndirectAction(action_set=[((1, 1), P4TableAction("
        "name='ipv4_forward', args={'dstAddr': 167772161, 'port': 1}))])"
    )
    assert (
        action.format_str(table) == "(1, 1)*ipv4_forward(dstAddr=0xa000001, port=0x1)"
    )


def test_indirect_action5():
    "Test P4IndirectAction class."
    schema = P4Schema(_P4INFO_TEST_DIR / "fabric.p4.p4info.txt")
    table = schema.tables["hashed"]

    action1 = P4IndirectAction(group_id=123)
    msg1 = action1.encode_table_action(table)
    assert pbuf.to_dict(msg1) == {"action_profile_group_id": 123}
    assert action1 == P4TableAction.decode_table_action(msg1, table)
    assert action1.format_str(table) == "@hashed_selector[0x7b]"

    action2 = P4IndirectAction(member_id=456)
    msg1 = action2.encode_table_action(table)
    assert pbuf.to_dict(msg1) == {"action_profile_member_id": 456}
    assert action2 == P4TableAction.decode_table_action(msg1, table)
    assert action2.format_str(table) == "@hashed_selector[[0x1c8]]"


def test_weighted_action():
    "Test P4WeightedAction constructed using * operator."
    action = P4TableAction("xyz", a=1)

    assert 2 * action == (2, action)
    assert 1 * action == (1, action)
    assert action * 2 == (2, action)
    assert action * 1 == (1, action)

    assert (2, 1) * action == ((2, 1), action)
    assert action * (2, 1) == ((2, 1), action)


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


def test_table_entry4():
    "Test TableEntry class."
    ctr_data = P4CounterData(byte_count=5, packet_count=6)
    entry = P4TableEntry(
        "ipv4_lpm",
        priority=10,
        controller_metadata=11,
        meter_config=P4MeterConfig(cir=1, cburst=2, pir=3, pburst=4),
        counter_data=ctr_data,
        meter_counter_data=P4MeterCounterData(
            green=ctr_data, yellow=ctr_data, red=ctr_data
        ),
        metadata=b"abc",
        is_default_action=True,
        idle_timeout_ns=10_000_000_000_000,
        time_since_last_hit=20_000_000_000_000,
        is_const=True,
    )

    msg = entry.encode(_SCHEMA)
    assert pbuf.to_dict(msg) == {
        "table_entry": {
            "controller_metadata": "11",
            "counter_data": {"byte_count": "5", "packet_count": "6"},
            "idle_timeout_ns": "10000000000000",
            "is_default_action": True,
            "metadata": "YWJj",
            "meter_config": {"cburst": "2", "cir": "1", "pburst": "4", "pir": "3"},
            "meter_counter_data": {
                "green": {"byte_count": "5", "packet_count": "6"},
                "red": {"byte_count": "5", "packet_count": "6"},
                "yellow": {"byte_count": "5", "packet_count": "6"},
            },
            "priority": 10,
            "table_id": 37375156,
            "time_since_last_hit": {"elapsed_ns": "20000000000000"},
            "is_const": True,
        }
    }

    assert entry == P4TableEntry.decode(msg, _SCHEMA)


def test_table_entry_indirect():
    "Test TableEntry class with table action auto-promoted to one-shot."
    schema = P4Schema(_P4INFO_TEST_DIR / "sai_unioned.p4info.txt")
    entry = P4TableEntry(
        "wcmp_group_table",
        match=P4TableMatch(wcmp_group_id="xyz"),
        action=P4TableAction("set_nexthop_id", nexthop_id="xyz"),
    )
    msg = entry.encode(schema)

    assert pbuf.to_dict(msg) == {
        "table_entry": {
            "action": {
                "action_profile_action_set": {
                    "action_profile_actions": [
                        {
                            "action": {
                                "action_id": 16777221,
                                "params": [{"param_id": 1, "value": "eHl6"}],
                            },
                            "weight": 1,
                        }
                    ]
                }
            },
            "match": [{"exact": {"value": "eHl6"}, "field_id": 1}],
            "table_id": 33554499,
        }
    }

    # Note that decode returns the table entry with a P4IndirectAction.
    decoded_entry = P4TableEntry(
        "wcmp_group_table",
        match=P4TableMatch(wcmp_group_id="xyz"),
        action=P4IndirectAction(
            action_set=[(1, P4TableAction("set_nexthop_id", nexthop_id="xyz"))]
        ),
    )
    assert decoded_entry == P4TableEntry.decode(msg, schema)


def test_table_entry_match_dict():
    "Test TableEntry match_dict method."
    entry1 = P4TableEntry("ipv4_lpm")
    assert entry1.match_dict(_SCHEMA, wildcard="*") == {"dstAddr": "*"}

    entry2 = P4TableEntry("ipv4_lpm", match=P4TableMatch(dstAddr=1))
    assert entry2.match_dict(_SCHEMA, wildcard="*") == {"dstAddr": "0x1"}


def test_table_entry_accessor():
    "Test P4TableEntry accessor for match fields."
    entry1 = P4TableEntry("ipv4_lpm", match=P4TableMatch(dstAddr=1))
    assert entry1["dstAddr"] == 1

    with pytest.raises(KeyError):
        entry1["nope"]

    entry2 = P4TableEntry("ipv4_lpm")
    with pytest.raises(KeyError):
        entry2["dstAddr"]


def test_table_entry_str_display():
    "Test P4TableEntry match_str and action_str methods."
    entry = P4TableEntry(
        "ipv4_lpm",
        match=P4TableMatch(dstAddr=1),
        action=P4TableAction("ipv4_forward", dstAddr=1108152157446, port=1),
    )
    assert f"{entry}" == str(entry)

    with _SCHEMA:
        # Test schema-aware formatting.
        assert entry.match_str() == "dstAddr=0x1"
        assert entry.action_str() == "ipv4_forward(dstAddr=0x10203040506, port=0x1)"

    with pytest.raises(RuntimeError, match="not in P4Schema context"):
        assert entry.action_str()


def test_table_entry_action_id():
    "Test P4TableEntry entity with an action_id (no parameters)."
    entry = P4TableEntry(
        "ipv4_lpm",
        # 'ipv4_forward' normally requires two parameters: dstAddr and port.
        action=P4TableAction("ipv4_forward"),
    )
    msg = entry.encode(_SCHEMA)
    assert pbuf.to_dict(msg) == {
        "table_entry": {
            "action": {"action": {"action_id": 28792405}},
            "table_id": 37375156,
        },
    }


def test_table_update_action_id():
    "Test P4TableEntry update with an action_id (no parameters)."
    entry = +P4TableEntry(
        "ipv4_lpm",
        # 'ipv4_forward' normally requires two parameters: dstAddr and port.
        action=P4TableAction("ipv4_forward"),
    )
    msg = entry.encode_update(_SCHEMA)

    # Encode the message, but the P4Runtime server will not accept this.
    assert pbuf.to_dict(msg) == {
        "type": "INSERT",
        "entity": {
            "table_entry": {
                "table_id": 37375156,
                "action": {"action": {"action_id": 28792405}},
            }
        },
    }


def test_decode_entity1():
    "Test decode_entity function."
    entity = p4r.Entity()
    with pytest.raises(ValueError, match="missing entity"):
        decode_entity(entity, _SCHEMA)


def test_decode_entity2():
    "Test decode_entity function."
    entity = P4TableEntry().encode(_SCHEMA)
    entry = decode_entity(entity, _SCHEMA)
    assert entry == P4TableEntry()


def test_decode_entity3():
    "Test decode_entity function."
    entity = P4MulticastGroupEntry().encode(_SCHEMA)
    entry = decode_entity(entity, _SCHEMA)
    assert entry == P4MulticastGroupEntry()


def test_decode_entity4():
    "Test decode_entity function."
    entity = p4r.Entity(
        packet_replication_engine_entry=p4r.PacketReplicationEngineEntry()
    )
    with pytest.raises(ValueError, match="missing packet_replication_engine type"):
        decode_entity(entity, _SCHEMA)


def test_decode_stream1():
    "Test decode_stream function."
    msg = p4r.StreamMessageResponse()
    with pytest.raises(ValueError, match="missing update"):
        decode_stream(msg, _SCHEMA)


def test_decode_stream2():
    "Test decode_stream function."
    msg = pbuf.from_text(
        r"""
        packet {
            payload: "abc"
        }
        """,
        p4r.StreamMessageResponse,
    )
    packet = decode_stream(msg, _SCHEMA)
    assert packet == P4PacketIn(b"abc", metadata={})


def test_encode_entities1():
    "Test encode_entities function."
    entity = P4TableEntry().encode(_SCHEMA)
    msgs1 = encode_entities([entity], _SCHEMA)
    msgs2 = encode_entities([P4TableEntry()], _SCHEMA)
    assert msgs1 == msgs2 == [entity]


def test_encode_updates1():
    "Test encode_updates with P4TableEntry."
    entry1 = P4TableEntry("ipv4_lpm")
    entry2 = P4TableEntry("ipv4_lpm")
    entry3 = P4TableEntry("ipv4_lpm")

    with pytest.raises(ValueError, match="unspecified update type"):
        encode_updates([entry1], _SCHEMA)

    result = encode_updates([+entry1, -entry2, ~entry3], _SCHEMA)
    assert [pbuf.to_dict(msg) for msg in result] == [
        {"entity": {"table_entry": {"table_id": 37375156}}, "type": "INSERT"},
        {"entity": {"table_entry": {"table_id": 37375156}}, "type": "DELETE"},
        {"entity": {"table_entry": {"table_id": 37375156}}, "type": "MODIFY"},
    ]


def test_encode_updates2():
    "Test encode_updates with P4TableEntry."
    entry1 = P4RegisterEntry("counter_bloom_filter", index=1, data=1)
    entry2 = P4RegisterEntry("counter_bloom_filter", index=2, data=2)
    entry3 = P4RegisterEntry("counter_bloom_filter", index=3, data=3)

    result = encode_updates([entry1, ~entry2, ~entry3], _SCHEMA)
    assert [pbuf.to_dict(msg) for msg in result] == [
        {
            "entity": {
                "register_entry": {
                    "data": {"bitstring": "AQ=="},
                    "index": {"index": "1"},
                    "register_id": 369140025,
                }
            },
            "type": "MODIFY",
        },
        {
            "entity": {
                "register_entry": {
                    "data": {"bitstring": "Ag=="},
                    "index": {"index": "2"},
                    "register_id": 369140025,
                }
            },
            "type": "MODIFY",
        },
        {
            "entity": {
                "register_entry": {
                    "data": {"bitstring": "Aw=="},
                    "index": {"index": "3"},
                    "register_id": 369140025,
                }
            },
            "type": "MODIFY",
        },
    ]


def test_encode_updates3():
    "Test encode_updates with already encoded p4r updates."
    result = encode_updates([p4r.Update(), p4r.StreamMessageRequest()], _SCHEMA)
    assert result == [p4r.Update(), p4r.StreamMessageRequest()]


def test_encode_updates4():
    "Test encode_updates with a single non-iterable argument."
    entry = P4TableEntry("ipv4_lpm")
    result = encode_updates(+entry, _SCHEMA)
    assert [pbuf.to_dict(msg) for msg in result] == [
        {
            "entity": {"table_entry": {"table_id": 37375156}},
            "type": "INSERT",
        },
    ]


def test_action_profile_member1():
    "Test P4ActionProfileMember class."
    entry = P4ActionProfileMember()
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {"action_profile_member": {}}
    assert entry == P4ActionProfileMember.decode(msg, _SCHEMA)


def test_action_profile_member2():
    "Test P4ActionProfileMember class."
    schema = P4Schema(_P4INFO_TEST_DIR / "fabric.p4.p4info.txt")
    entry = P4ActionProfileMember(
        action_profile_id="hashed_selector",
        member_id=2,
        action=P4TableAction("pop_vlan"),
    )
    msg = entry.encode(schema)

    assert pbuf.to_dict(msg) == {
        "action_profile_member": {
            "action": {"action_id": 17183246},
            "action_profile_id": 291115404,
            "member_id": 2,
        }
    }
    assert entry == P4ActionProfileMember.decode(msg, schema)


def test_action_profile_member_actionstr():
    "Test the P4ActionProfileMember action_str method."
    schema = P4Schema(_P4INFO_TEST_DIR / "fabric.p4.p4info.txt")
    entry = P4ActionProfileMember(
        action_profile_id="hashed_selector",
        member_id=2,
        action=P4TableAction("pop_vlan"),
    )
    with schema:
        assert entry.action_profile_id == "hashed_selector"
        assert entry.member_id == 2
        assert entry.action_str() == "pop_vlan()"


def test_action_profile_group1():
    "Test P4ActionProfileGroup class."
    entry = P4ActionProfileGroup()
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {"action_profile_group": {}}
    assert entry == P4ActionProfileGroup.decode(msg, _SCHEMA)


def test_action_profile_group2():
    "Test P4ActionProfileGroup class."
    schema = P4Schema(_P4INFO_TEST_DIR / "fabric.p4.p4info.txt")
    entry = P4ActionProfileGroup(
        action_profile_id="hashed_selector",
        group_id=2,
        max_size=3,
        members=[
            P4Member(member_id=1, weight=(3, 0xABC)),
            P4Member(member_id=2, weight=4),
        ],
    )
    msg = entry.encode(schema)

    assert pbuf.to_dict(msg) == {
        "action_profile_group": {
            "action_profile_id": 291115404,
            "group_id": 2,
            "max_size": 3,
            "members": [
                {"member_id": 1, "watch_port": "Crw=", "weight": 3},
                {"member_id": 2, "weight": 4},
            ],
        }
    }
    assert entry == P4ActionProfileGroup.decode(msg, schema)


def test_action_profile_group_actionstr():
    "Test the P4ActionProfileGroup action_str method."
    schema = P4Schema(_P4INFO_TEST_DIR / "fabric.p4.p4info.txt")
    entry = P4ActionProfileGroup(
        action_profile_id="hashed_selector",
        group_id=2,
        max_size=3,
        members=[
            P4Member(member_id=1, weight=(3, 0xABC)),
            P4Member(member_id=2, weight=4),
        ],
    )

    with schema:
        assert entry.action_profile_id == "hashed_selector"
        assert entry.group_id == 2
        assert entry.max_size == 3
        assert entry.action_str() == "(3, 2748)*0x1 4*0x2"


def test_member():
    "Test P4Member class."
    member1 = P4Member(1, weight=2)
    msg = member1.encode()

    assert pbuf.to_dict(msg) == {"member_id": 1, "weight": 2}
    assert member1 == P4Member.decode(msg)

    member2 = P4Member(member_id=2, weight=(4, 3))
    msg = member2.encode()

    assert pbuf.to_dict(msg) == {"member_id": 2, "watch_port": "Aw==", "weight": 4}
    assert member2 == P4Member.decode(msg)


def test_meter_entry1():
    "Test P4MeterEntry class."
    entry = P4MeterEntry()
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {"meter_entry": {}}
    assert entry == P4MeterEntry.decode(msg, _SCHEMA)


def test_meter_entry2():
    "Test P4MeterEntry class."
    entry = P4MeterEntry(
        meter_id="other_meter",
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
            "meter_id": 341473317,
        }
    }
    assert entry == P4MeterEntry.decode(msg, _SCHEMA)


def test_direct_meter_entry1():
    "Test P4MeterEntry class."
    entry = P4DirectMeterEntry()
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {"direct_meter_entry": {}}
    assert entry == P4DirectMeterEntry.decode(msg, _SCHEMA)


def test_direct_meter_entry2():
    "Test P4MeterEntry class."
    entry = P4DirectMeterEntry(
        table_entry=P4TableEntry(
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
        "other_counter",
        index=2,
        data=P4CounterData(byte_count=1, packet_count=2),
    )
    assert entry.counter_id == "other_counter"
    assert entry.byte_count == 1
    assert entry.packet_count == 2

    msg = entry.encode(_SCHEMA)
    assert pbuf.to_dict(msg) == {
        "counter_entry": {
            "counter_id": 307710742,
            "data": {"byte_count": "1", "packet_count": "2"},
            "index": {"index": "2"},
        }
    }
    assert entry == P4CounterEntry.decode(msg, _SCHEMA)


def test_direct_counter_entry1():
    "Test P4CounterEntry class."
    entry = P4DirectCounterEntry()
    assert entry.table_id == ""

    msg = entry.encode(_SCHEMA)
    assert pbuf.to_dict(msg) == {"direct_counter_entry": {"table_entry": {}}}

    entry_decode = P4DirectCounterEntry(table_entry=P4TableEntry())
    assert entry_decode == P4DirectCounterEntry.decode(msg, _SCHEMA)


def test_direct_counter_entry2():
    "Test P4CounterEntry class."
    table_entry = P4TableEntry(
        "ipv4_lpm",
        match=P4TableMatch(dstAddr=(167772160, 24)),
    )

    entry = P4DirectCounterEntry(
        table_entry=table_entry,
        data=P4CounterData(byte_count=1, packet_count=2),
    )
    assert entry.counter_id == ""
    assert entry.table_id == "ipv4_lpm"
    assert entry.byte_count == 1
    assert entry.packet_count == 2

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

    # When decoded, the entry will have a counter_id.
    entry_decode = P4DirectCounterEntry(
        "ipv4_counter",
        table_entry=table_entry,
        data=P4CounterData(byte_count=1, packet_count=2),
    )
    assert entry_decode == P4DirectCounterEntry.decode(msg, _SCHEMA)


def test_direct_counter_entry3():
    "Test P4CounterEntry class."
    entry = P4DirectCounterEntry("ipv4_counter")
    assert entry.counter_id == "ipv4_counter"
    assert entry.table_entry is None
    assert entry.data is None

    msg = entry.encode(_SCHEMA)
    assert pbuf.to_dict(msg) == {
        "direct_counter_entry": {
            "table_entry": {"table_id": 37375156},
        }
    }

    # When decoded, the entry will have a table_entry.
    entry_decode = P4DirectCounterEntry(
        "ipv4_counter",
        table_entry=P4TableEntry("ipv4_lpm"),
    )
    assert entry_decode == P4DirectCounterEntry.decode(msg, _SCHEMA)


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


def test_digest_entry1():
    "Test P4DigestEntry class."
    entry = P4DigestEntry()
    msg = entry.encode(_SCHEMA)

    assert pbuf.to_dict(msg) == {"digest_entry": {}}
    assert entry == P4DigestEntry.decode(msg, _SCHEMA)


def test_digest_entry2():
    "Test P4DigestEntry class."
    schema = P4Schema(_P4INFO_TEST_DIR / "layer2.p4.p4info.txt")
    entry = P4DigestEntry(
        "Digest_t",
        max_list_size=1,
        max_timeout_ns=2,
        ack_timeout_ns=3,
    )
    msg = entry.encode(schema)

    assert pbuf.to_dict(msg) == {
        "digest_entry": {
            "config": {
                "ack_timeout_ns": "3",
                "max_list_size": 1,
                "max_timeout_ns": "2",
            },
            "digest_id": 401827287,
        }
    }
    assert entry == P4DigestEntry.decode(msg, schema)


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
        == "P4PacketOut(metadata={'egress_port': 1, '_pad': 0}, payload=h'616263')"
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
    assert repr(packet) == "P4PacketIn(payload=h'616263')"


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
        == "P4PacketIn(metadata={'ingress_port': 97, '_pad': 98}, payload=h'616263')"
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


def test_digest_list2():
    "Test P4DigestList."
    schema = P4Schema(_P4INFO_TEST_DIR / "layer2.p4.p4info.txt")
    msg = pbuf.from_text(
        r"""
        digest {
            digest_id: 401827287
            list_id: 2
            timestamp: 3
        }
        """,
        p4r.StreamMessageResponse,
    )

    digest = P4DigestList.decode(msg, schema)
    assert digest == P4DigestList("Digest_t", list_id=2, timestamp=3, data=[])


def test_idle_timeout_notification1():
    "Test P4IdleTimeoutNotification."
    data = pbuf.from_dict(
        {
            "idle_timeout_notification": {
                "table_entry": [
                    {
                        "match": [
                            {
                                "field_id": 1,
                                "lpm": {"prefix_len": 24, "value": "CgAAAA=="},
                            }
                        ],
                        "table_id": 37375156,
                    },
                ],
                "timestamp": 1000,
            }
        },
        p4r.StreamMessageResponse,
    )

    notification = P4IdleTimeoutNotification.decode(data, _SCHEMA)

    expected = P4TableEntry("ipv4_lpm", match=P4TableMatch(dstAddr=(167772160, 24)))
    assert notification.timestamp == 1000
    assert notification.table_entry == [expected]

    assert len(notification) == 1
    assert notification[0] == expected

    for entry in notification:
        assert entry.table_id == "ipv4_lpm"


def test_digest_list_ack1():
    "Test P4DigestListAck."
    schema = P4Schema(_P4INFO_TEST_DIR / "layer2.p4.p4info.txt")
    ack = P4DigestListAck("Digest_t", 1)
    msg = ack.encode_update(schema)

    assert pbuf.to_dict(msg) == {
        "digest_ack": {
            "digest_id": 401827287,
            "list_id": "1",
        }
    }

    digest = P4DigestList("Digest_t", list_id=1, timestamp=0, data=[])
    assert digest.ack() == ack


def test_value_set_entry1():
    "Test P4ValueSetEntry."
    entry = P4ValueSetEntry(
        "pvs",
        members=[
            P4ValueSetMember(1),
            P4ValueSetMember(2),
        ],
    )

    msg = entry.encode(_SCHEMA)
    assert pbuf.to_dict(msg) == {
        "value_set_entry": {
            "members": [
                {"match": [{"exact": {"value": "AQ=="}, "field_id": 1}]},
                {"match": [{"exact": {"value": "Ag=="}, "field_id": 1}]},
            ],
            "value_set_id": 56033750,
        }
    }
    assert entry == P4ValueSetEntry.decode(msg, _SCHEMA)

    assert entry.members[0].value == 1
    assert entry.members[1].value == 2


def test_extern_entry0():
    "Test that P4ExternEntry class requires keyword arguments."
    with pytest.raises(TypeError, match="keyword-only"):
        P4ExternEntry()  # pyright: ignore[reportGeneralTypeIssues]


def test_extern_entry1():
    "Test P4ExternEntry."
    schema = P4Schema(_P4INFO_TEST_DIR / "externs.p4info.txt")
    any_data = pbuf.to_any(p4r.CounterData(byte_count=1, packet_count=2))

    entry = P4ExternEntry(
        extern_type_id="x",
        extern_id="instance2",
        entry=any_data,
    )

    assert entry.extern_type_id == "x"
    assert entry.extern_id == "instance2"
    assert entry.entry == any_data

    msg = entry.encode(schema)
    assert pbuf.to_dict(msg) == {
        "extern_entry": {
            "entry": OrderedDict(
                [
                    ("@type", "type.googleapis.com/p4.v1.CounterData"),
                    ("byte_count", "1"),
                    ("packet_count", "2"),
                ]
            ),
            "extern_id": 2,
            "extern_type_id": 1,
        }
    }
    assert entry == P4ExternEntry.decode(msg, schema)
