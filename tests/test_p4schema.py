import difflib
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
from finsy.p4schema import P4EntityMap, P4MatchField, P4MatchType, P4Schema

P4INFO_TEST_DIR = Path(__file__).parent / "test_data/p4info"


@dataclass
class _Example:
    "Dummy entity used to testing P4EntityMap."
    id: int
    name: str
    alias: str


def test_entity_map():
    "Test P4EntityMap helper class."

    example = _Example(1, "example.one", "one")

    entities = P4EntityMap("entry_type")
    assert len(entities) == 0

    entities._add(example)
    assert len(entities) == 1
    assert list(entities) == [example]

    assert entities[1] == example
    assert entities["example.one"] == example
    assert entities["one"] == example

    with pytest.raises(ValueError, match="no entry_type named 'example.zero'"):
        entities["example.zero"]

    assert entities.get(1) == example
    assert entities.get("example.one") == example
    assert entities.get("one") == example
    assert entities.get("zero") is None

    assert repr(entities) == "[_Example(id=1, name='example.one', alias='one')]"


def test_entity_map_split():
    "Test P4EntityMap helper class with split_suffix."
    example = _Example(1, "example.one", "example.one")

    entities = P4EntityMap("entry_type")
    entities._add(example, split_suffix=True)

    assert entities[1] == example
    assert entities["example.one"] == example
    assert entities["one"] == example


def test_entity_map_duplicate():
    "Test P4EntityMap helper class with duplicate entry."
    example1 = _Example(1, "example.one", "example.one")
    example2 = _Example(1, "example.one", "example.one")
    example3 = _Example(2, "example.one", "example.one")

    entities = P4EntityMap("entry_type")
    entities._add(example1)

    with pytest.raises(ValueError, match="id already exists"):
        entities._add(example2)

    with pytest.raises(ValueError, match="name already exists"):
        entities._add(example3)


def test_p4schema():
    "Test P4Schema."

    schema = P4Schema(P4INFO_TEST_DIR / "basic.p4.p4info.txt", b"abc")

    assert schema.p4info is not None
    assert schema.p4blob == b"abc"
    assert repr(schema)


def test_p4info_tables():
    p4 = P4Schema(P4INFO_TEST_DIR / "basic.p4.p4info.txt")

    # Access a table by name.
    ipv4_lpm = p4.tables["MyIngress.ipv4_lpm"]
    assert ipv4_lpm.id == 37375156
    assert ipv4_lpm.name == "MyIngress.ipv4_lpm"
    assert ipv4_lpm.alias == "ipv4_lpm"
    assert ipv4_lpm.brief == ""
    assert ipv4_lpm.description == ""
    assert ipv4_lpm.size == 1024
    assert [field.alias for field in ipv4_lpm._match_fields] == ["dstAddr"]
    assert [action.alias for action in ipv4_lpm._actions] == [
        "ipv4_forward",
        "drop",
        "NoAction",
    ]

    # Test access by alias and ID.
    assert p4.tables["ipv4_lpm"] is ipv4_lpm
    assert p4.tables[37375156] is ipv4_lpm

    # Test table match_fields.
    dstAddr = ipv4_lpm._match_fields["dstAddr"]
    assert dstAddr.match_type == P4MatchType.LPM
    assert dstAddr.bitwidth == 32


def test_p4info_actions():
    p4 = P4Schema(Path(P4INFO_TEST_DIR, "basic.p4.p4info.txt"))

    # Access an action by name.
    noaction = p4.actions["NoAction"]
    assert noaction.id == 21257015
    assert noaction.name == "NoAction"
    assert noaction.alias == "NoAction"
    assert noaction.brief == ""
    assert noaction.description == ""
    assert [anno.name for anno in noaction.annotations] == ["noWarn"]
    assert [anno.body for anno in noaction.annotations] == ['"unused"']

    # Test access by ID.
    assert p4.actions[21257015] is noaction


@pytest.mark.skip()
def test_table_syntax():
    p4 = P4Schema(Path(P4INFO_TEST_DIR, "basic.p4.p4info.txt"))
    ipv4 = p4.tables["ipv4_lpm"].set(idle_timeout=1e9)

    x = ipv4(dstaddr="A").ipv4_forward(dstaddr="B", port=1)
    assert ~x == {
        "table": "MyIngress.ipv4_lpm",
        "match": {"dstaddr": "A"},
        "actions": [
            {"$action": "ipv4_forward", "$weight": None, "dstaddr": "B", "port": 1}
        ],
        "idle_timeout": 1000000000.0,
        "group_id": None,
        "member_id": None,
        "priority": None,
    }

    oneshot = (
        ipv4(dstaddr="B")
        .ipv4_forward((1, b"1"), dstaddr="B", port=1)
        .ipv4_forward((2, b"2"), dstaddr="B", port=1)
        .ipv4_forward((3, b"3"), dstaddr="B", port=1)
    )
    assert ~oneshot == {
        "table": "MyIngress.ipv4_lpm",
        "match": {"dstaddr": "B"},
        "actions": [
            {
                "$action": "ipv4_forward",
                "$weight": (1, b"1"),
                "dstaddr": "B",
                "port": 1,
            },
            {
                "$action": "ipv4_forward",
                "$weight": (2, b"2"),
                "dstaddr": "B",
                "port": 1,
            },
            {
                "$action": "ipv4_forward",
                "$weight": (3, b"3"),
                "dstaddr": "B",
                "port": 1,
            },
        ],
        "idle_timeout": 1000000000.0,
        "group_id": None,
        "member_id": None,
        "priority": None,
    }


@pytest.mark.parametrize("p4info_file", P4INFO_TEST_DIR.glob("*.p4info.txt"))
def test_p4info(p4info_file):
    p4 = P4Schema(p4info_file)

    p4_orig = Path(p4info_file).with_suffix(".repr.txt")
    if p4_orig.exists():
        p4_orig_lines = p4_orig.read_text().splitlines()
    else:
        p4_orig_lines = []

    p4_repr = _format_source_code(repr(p4))
    result = difflib.unified_diff(
        p4_orig_lines,
        p4_repr.splitlines(),
        p4_orig.name,
        "new",
    )

    result_lines = list(result)
    # if result_lines:
    #    p4_orig.write_text(p4_repr)
    assert not result_lines


def _format_source_code(source):
    "Format the given source code using `black` formatter."
    return subprocess.check_output(
        ["black", "-"],
        input=source,
        stderr=subprocess.DEVNULL,
        encoding="utf-8",
    )


def test_p4info_lookup():
    schema = P4Schema(P4INFO_TEST_DIR / "basic.p4.p4info.txt")

    with pytest.raises(
        ValueError,
        match="no P4Register named 'bloom'. Did you mean 'counter_bloom_filter'?",
    ):
        schema.registers["bloom"]
